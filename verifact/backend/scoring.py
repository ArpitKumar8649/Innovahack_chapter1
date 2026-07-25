"""Trust Engine v2 — deterministic, calibrated, auditable.

Confidence is COMPUTED from verification signals (LLM self-reported
confidence is miscalibrated — Amazon/MIT calibration research 2024-25):

    30 × verifier_agreement   (unanimous 1.0 · majority 0.66 · split 0.33)
  + 20 × evidence_coverage    (min(distinct evidence chunks / 3, 1.0))
  + 20 × source_authority     (best authority-tier weight among cited sources)
  + 10 × source_diversity     (distinct publishers / 2, capped 1.0)
  + 10 × specificity          (1.0, or 0.5 for hedged claims)
  + 10 × recency              (freshness vs. topic velocity; 1.0 default)
  − 35 × contradiction_penalty
  − 20 × hallucination_flag
  clamped to [5, 98] — never 0 (unverifiable ≠ false), never 100 (epistemic honesty)

Epistemic status taxonomy: ESTABLISHED · SUPPORTED · CONTESTED · REFUTED ·
UNVERIFIABLE · OUTDATED.
"""
from evidence import TIER_WEIGHT

HEDGE_WORDS = (
    "may", "might", "possibly", "approximately", "about", "roughly",
    "some", "often", "usually", "believed", "reportedly", "allegedly",
    "around", "nearly", "perhaps", "likely",
)


def _agreement(stances: list[str]) -> float:
    n = len(stances) or 1
    sup, ref = stances.count("support"), stances.count("refute")
    if sup == n or ref == n:
        return 1.0
    if max(sup, ref) / n >= 2 / 3:
        return 0.66
    return 0.33


def score_claim(
    claim_text: str,
    verdicts: list,
    chunk_ids: list[str],
    source_ids: list[int],
    sources_by_id: dict,
    contradiction_flagged: bool,
    hallucination_flags: list,
) -> tuple[int, str]:
    """Returns (confidence 0-100, epistemic status)."""
    stances = [v.stance for v in verdicts]
    sup, ref = stances.count("support"), stances.count("refute")

    agreement = _agreement(stances)
    coverage = min(len(set(chunk_ids)) / 3, 1.0)

    tiers = [
        sources_by_id[sid].authority_tier
        for sid in source_ids if sid in sources_by_id
    ]
    authority = max((TIER_WEIGHT[t] for t in tiers), default=0.4)

    publishers = {
        sources_by_id[sid].publisher
        for sid in source_ids
        if sid in sources_by_id and sources_by_id[sid].publisher
    }
    diversity = min(len(publishers) / 2, 1.0)

    specificity = (
        0.5 if any(w in claim_text.lower().split() for w in HEDGE_WORDS) else 1.0
    )
    recency = 1.0  # Phase 2: source-date vs. topic-velocity analysis

    high_flag = any(f.get("severity") == "high" for f in hallucination_flags)
    hallu = 1.0 if high_flag else (0.5 if hallucination_flags else 0.0)
    contra = 1.0 if contradiction_flagged else 0.0

    conf = (
        30 * agreement
        + 20 * coverage
        + 20 * authority
        + 10 * diversity
        + 10 * specificity
        + 10 * recency
        - 35 * contra
        - 20 * hallu
    )
    conf = int(max(5, min(98, round(conf))))

    # --- epistemic status ---------------------------------------------------
    if ref >= 2 or (contra and ref >= 1):
        status = "REFUTED"
    elif any(f.get("type") == "staleness" for f in hallucination_flags):
        status = "OUTDATED"
    elif not stances or (sup == 0 and ref == 0):
        status = "UNVERIFIABLE"
    elif high_flag and conf < 60:
        # auditor flagged a serious problem the panel missed → contested, not supported
        status = "CONTESTED"
    elif sup >= 2 and ref == 0:
        best_tier = min(tiers, default=4)
        status = "ESTABLISHED" if (conf >= 80 and best_tier <= 2) else "SUPPORTED"
    elif sup >= 1 and ref >= 1:
        status = "CONTESTED"
    elif sup >= 1:
        status = "SUPPORTED"
    else:
        status = "UNVERIFIABLE"
    return conf, status


def trust_score(claims) -> int:
    """Report-level trust: mean of claim confidences."""
    if not claims:
        return 0
    return int(round(sum(c.confidence for c in claims) / len(claims)))
