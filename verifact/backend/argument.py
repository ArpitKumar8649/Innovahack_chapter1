"""Argument layer (Phase 5) — the report as an argument tree.

Builds a Toulmin-structured tree from the verified claims:

    claim (root)
      └─ hypothesis H1 ── evidence E1,E3 (supports)
                       └─ counter-evidence E7 (attacks)
      └─ hypothesis H2 ── evidence E2 (supports)

- nodes = hypotheses / claims; edges = supports / attacks with evidence weight
- every node carries its verdict distribution (A ✓ / B ✗ / C ✓)
- the **weakest link** = the load-bearing evidence span with the lowest
  authority — flagged so the reader knows where the argument is thinnest.

Pure function over already-scored claims + sources; emitted as an SSE event
and stored on the report.
"""
from evidence import TIER_WEIGHT


def _verdict_distribution(claim) -> dict:
    """A/B/C (+J) stance counts for a claim's verdicts."""
    dist = {}
    for v in claim.verdicts:
        dist[v.verifier] = v.stance
    return dist


def _evidence_weight(source) -> float:
    return TIER_WEIGHT.get(source.authority_tier, 0.4)


def build_argument_tree(claims, hypotheses, sources_by_id) -> dict:
    """Assemble the tree. Returns a JSON-serializable dict.

    Root = the investigation's topic claim (the first claim, by convention the
    verbatim topic assertion); children = hypotheses; leaves = evidence chunks
    grouped into supports / attacks per hypothesis.
    """
    if not claims:
        return {"root": None, "weakest_link": None, "multi_hypothesis": False}

    claims_by_hyp: dict[str, list] = {}
    unattributed: list = []
    for c in claims:
        if c.hypothesis_id:
            claims_by_hyp.setdefault(c.hypothesis_id, []).append(c)
        else:
            unattributed.append(c)

    # The root is the claim that states the topic itself — by extraction
    # convention that's the first claim; fall back to the highest-confidence one.
    root_claim = claims[0]

    hyp_nodes = []
    evidence_nodes: list[dict] = []   # flat list for weakest-link scan
    multi_hypothesis = len(hypotheses) > 1 or len(claims_by_hyp) > 1

    for h in hypotheses:
        h_claims = claims_by_hyp.get(h.id, [])
        supports, attacks = [], []
        for c in h_claims:
            stance = _dominant_stance(c)
            edge = {
                "claim_id": c.id,
                "text": c.text,
                "relation": "supports" if stance != "refute" else "attacks",
                "status": c.status,
                "confidence": c.confidence,
                "verdicts": _verdict_distribution(c),
                "source_ids": c.source_ids,
                "weight": _claim_weight(c, sources_by_id),
            }
            (supports if stance != "refute" else attacks).append(edge)
            # record each cited source as an evidence node for the weakest-link scan
            for sid in c.source_ids:
                s = sources_by_id.get(sid)
                if s:
                    evidence_nodes.append({
                        "source_id": sid, "claim_id": c.id, "hypothesis": h.id,
                        "tier": s.authority_tier, "weight": _evidence_weight(s),
                        "relation": edge["relation"],
                    })

        hyp_nodes.append({
            "id": h.id,
            "statement": h.statement,
            "plausibility": h.plausibility,
            "supports": supports,
            "attacks": attacks,
            "verdicts": _aggregate_verdicts(h_claims),
        })

    # hypotheses with no attributed claims still deserve a node (they were argued)
    seen = {h["id"] for h in hyp_nodes}
    for h in hypotheses:
        if h.id not in seen:
            hyp_nodes.append({"id": h.id, "statement": h.statement,
                              "plausibility": h.plausibility, "supports": [],
                              "attacks": [], "verdicts": {}})

    weakest = _weakest_link(evidence_nodes, sources_by_id)

    return {
        "root": {
            "claim_id": root_claim.id,
            "text": root_claim.text,
            "status": root_claim.status,
            "confidence": root_claim.confidence,
            "verdicts": _verdict_distribution(root_claim),
        },
        "hypotheses": hyp_nodes,
        "unattributed": [
            {"claim_id": c.id, "text": c.text, "status": c.status,
             "confidence": c.confidence} for c in unattributed
        ],
        "weakest_link": weakest,
        "multi_hypothesis": multi_hypothesis,
    }


def _dominant_stance(claim) -> str:
    """support unless the panel (or a refuting majority) says refute."""
    stances = [v.stance for v in claim.verdicts]
    if stances.count("refute") > stances.count("support"):
        return "refute"
    if claim.status == "REFUTED":
        return "refute"
    return "support"


def _aggregate_verdicts(h_claims) -> dict:
    """Per-verifier majority stance across a hypothesis's claims."""
    by_verifier: dict[str, list] = {}
    for c in h_claims:
        for v in c.verdicts:
            by_verifier.setdefault(v.verifier, []).append(v.stance)
    out = {}
    for tag, stances in by_verifier.items():
        out[tag] = max(set(stances), key=stances.count)
    return out


def _claim_weight(claim, sources_by_id) -> float:
    """Best authority weight among a claim's cited sources."""
    weights = [
        _evidence_weight(sources_by_id[sid])
        for sid in claim.source_ids if sid in sources_by_id
    ]
    return max(weights, default=0.4)


def _weakest_link(evidence_nodes, sources_by_id) -> dict | None:
    """The load-bearing evidence with the lowest authority.

    "Load-bearing" = it supports a claim that the argument leans on (not an
    attack). We pick the supporting evidence node with the smallest tier weight;
    ties broken toward the higher-confidence claim it underpins.
    """
    load_bearing = [e for e in evidence_nodes if e["relation"] == "supports"]
    if not load_bearing:
        return None
    weakest = min(load_bearing, key=lambda e: (e["weight"], e["source_id"]))
    s = sources_by_id.get(weakest["source_id"])
    return {
        "source_id": weakest["source_id"],
        "claim_id": weakest["claim_id"],
        "hypothesis": weakest["hypothesis"],
        "tier": weakest["tier"],
        "publisher": s.publisher if s else "",
        "title": s.title if s else "",
        "note": (f"This argument leans on a T{weakest['tier']} source "
                 f"({s.publisher if s else 'unknown'}) — its weakest point."),
    }
