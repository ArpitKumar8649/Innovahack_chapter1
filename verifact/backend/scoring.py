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


def _agreement(stances: list[str], judge_ruled: bool = False) -> float:
    n = len(stances) or 1
    sup, ref = stances.count("support"), stances.count("refute")
    if sup == n or ref == n:
        return 1.0
    if max(sup, ref) / n >= 2 / 3:
        return 0.66
    if judge_ruled and max(sup, ref) > min(sup, ref):
        return 0.55   # judge-broken tie — a decided but weak majority
    return 0.33


def _components(claim_text, verdicts, chunk_ids, source_ids, sources_by_id, recency):
    """The six confidence axes (each 0-1) — shared by score_claim and radar."""
    stances = [v.stance for v in verdicts]
    judge_ruled = any(getattr(v, "verifier", "") == "J" for v in verdicts)
    agreement = _agreement(stances, judge_ruled)
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
    return {"agreement": agreement, "coverage": coverage, "authority": authority,
            "diversity": diversity, "specificity": specificity,
            "recency": recency, "tiers": tiers}


def score_claim(
    claim_text: str,
    verdicts: list,
    chunk_ids: list[str],
    source_ids: list[int],
    sources_by_id: dict,
    contradiction_flagged: bool,
    hallucination_flags: list,
    recency: float = 0.8,
) -> tuple[int, str]:
    """Returns (confidence 0-100, epistemic status)."""
    stances = [v.stance for v in verdicts]
    sup, ref = stances.count("support"), stances.count("refute")

    comp = _components(claim_text, verdicts, chunk_ids, source_ids,
                       sources_by_id, recency)
    tiers = comp["tiers"]

    high_flag = any(f.get("severity") == "high" for f in hallucination_flags)
    hallu = 1.0 if high_flag else (0.5 if hallucination_flags else 0.0)
    contra = 1.0 if contradiction_flagged else 0.0

    conf = (
        30 * comp["agreement"]
        + 20 * comp["coverage"]
        + 20 * comp["authority"]
        + 10 * comp["diversity"]
        + 10 * comp["specificity"]
        + 10 * comp["recency"]
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


def radar(claims, sources_by_id) -> dict:
    """Report-level Trust Radar: mean of each confidence axis across claims.

    Five axes (agreement / authority / coverage / diversity / recency), each
    0-1 — the brief's "consensus score" visual, computed not vibes.
    """
    from authority import recency_score   # local import: avoid a cycle
    axes = {"agreement": [], "authority": [], "coverage": [],
            "diversity": [], "recency": []}
    for c in claims:
        dates = [
            sources_by_id[sid].published_at
            for sid in c.source_ids
            if sid in sources_by_id
            and getattr(sources_by_id[sid], "published_at", None)
        ]
        comp = _components(c.text, c.verdicts, c.chunk_ids, c.source_ids,
                           sources_by_id, recency_score(dates))
        for k in axes:
            axes[k].append(comp[k])
    return {k: round(sum(v) / len(v), 3) if v else 0.0 for k, v in axes.items()}


def trust_score(claims) -> int:
    """Report-level trust: mean of claim confidences."""
    if not claims:
        return 0
    return int(round(sum(c.confidence for c in claims) / len(claims)))
