"""Deterministic confidence scoring — never trust LLM self-reported confidence.

Calibration research (Amazon/MIT 2024-25) shows LLMs report ~100% confidence
even when wrong, so confidence here is computed from verification signals:

    40 × verifier_agreement   (unanimous 1.0 · majority 0.66 · split 0.33)
  + 25 × source_coverage      (min(cited_sources / 2, 1.0))
  + 20 × source_quality       (avg Tavily relevance of cited sources)
  + 15 × specificity          (1.0, or 0.5 for hedged/vague claims)
  - 30 × contradiction_penalty (flagged by the contradiction detector)
  clamped to [5, 98]  — never 0 (unverifiable ≠ false), never 100 (epistemic honesty)
"""

HEDGE_WORDS = (
    "may", "might", "possibly", "approximately", "about", "roughly",
    "some", "often", "usually", "believed", "reportedly", "allegedly",
    "around", "nearly", "估计", "大约",
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
    source_ids: list[int],
    sources_by_id: dict,
    contradiction_flagged: bool,
) -> tuple[int, str]:
    """Returns (confidence 0-100, status)."""
    stances = [v.stance for v in verdicts]
    ref = stances.count("support") and stances.count("refute")

    agreement = _agreement(stances)
    coverage = min(len(source_ids) / 2, 1.0)

    scores = [
        sources_by_id[sid].score
        for sid in source_ids
        if sid in sources_by_id and sources_by_id[sid].score
    ]
    quality = sum(scores) / len(scores) if scores else 0.5

    text_lower = claim_text.lower()
    specificity = 0.5 if any(w in text_lower.split() for w in HEDGE_WORDS) else 1.0

    penalty = 1.0 if contradiction_flagged else 0.0

    conf = (
        40 * agreement
        + 25 * coverage
        + 20 * quality
        + 15 * specificity
        - 30 * penalty
    )
    conf = int(max(5, min(98, round(conf))))

    if stances.count("refute") >= 2 or contradiction_flagged:
        status = "contradicted"
    elif conf >= 75:
        status = "verified"
    elif conf >= 50:
        status = "disputed"
    else:
        status = "unverified"
    return conf, status


def trust_score(claims) -> int:
    """Report-level trust: mean of claim confidences."""
    if not claims:
        return 0
    return int(round(sum(c.confidence for c in claims) / len(claims)))
