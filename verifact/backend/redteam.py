"""Red-Team Agent (Phase 9) — adversarial probing of completed reports.

After the court delivers its verdict, the Red-Team agent attacks the report
from multiple adversarial angles, searching for residual bias, hallucination,
and reasoning gaps that the panel missed.

Attack vectors:
1. Source quality — are the cited sources actually authoritative?
2. Staleness — could newer evidence change the verdict?
3. Scope creep — does the claim overstate what the evidence supports?
4. Entity confusion — could similar entities be conflated?
5. Missing evidence — what evidence is conspicuously absent?

Findings with severity "high" are seeded into the trap suite as new test
cases — the system literally learns from its own adversarial probing.
"""
import json
import time

import llm


RETEAM_SYSTEM = """You are the Red-Team Agent — an adversarial auditor whose job
is to BREAK the court's verdict. You are NOT part of the panel; you attack
from the outside, looking for what the panel missed.

For each claim in the report, probe these attack vectors:
1. SOURCE QUALITY: Are the cited sources actually authoritative for THIS claim?
   Could a higher-tier source contradict them?
2. STALENESS: Is the evidence current? Could newer evidence (published after
   the sources) change the verdict?
3. SCOPE CREEP: Does the claim overstate what the evidence supports? (e.g.,
   "all studies show" when only one study is cited)
4. ENTITY CONFUSION: Could similar entities be conflated? (e.g., two people
   with the same name, two companies with similar names)
5. MISSING EVIDENCE: What evidence is conspicuously absent? What would a
   thorough investigation have found that this one didn't?

For each finding, report:
- attack_vector: which of the 5 vectors
- severity: "high" | "medium" | "low"
- finding: what you found (1-2 sentences)
- recommendation: what the court should do about it

Be ruthless but fair. Only report genuine findings — false alarms erode trust.

Return JSON:
{"findings": [{"claim_id": 1, "attack_vector": "source_quality", "severity": "high",
               "finding": "...", "recommendation": "..."}]}"""


async def probe_report(report: dict, log=None) -> list[dict]:
    """Attack a completed report from multiple adversarial angles.

    Returns a list of findings, each with claim_id, attack_vector, severity,
    finding, and recommendation.
    """
    if log:
        log("red-team agent probing the report for residual bias and gaps…")

    # Build a compact representation of the report for the red-team prompt
    claims_block = []
    for c in report.get("claims", []):
        verdicts = "; ".join(
            f"{v['verifier']}={v['stance']}" for v in c.get("verdicts", [])
        )
        sources = ", ".join(f"[{sid}]" for sid in c.get("source_ids", []))
        claims_block.append(
            f"C{c['id']} ({c['status']}, conf={c['confidence']}): {c['text']}\n"
            f"  verdicts: {verdicts} | sources: {sources}"
        )

    sources_block = []
    for s in report.get("sources", []):
        sources_block.append(
            f"[{s['id']}] T{s['authority_tier']} {s['publisher']} — {s['title']}"
        )

    prompt = (
        f"REPORT TOPIC: {report.get('topic', '')}\n\n"
        f"CLAIMS:\n" + "\n".join(claims_block) + "\n\n"
        f"SOURCES:\n" + "\n".join(sources_block) + "\n\n"
        f"TRUST SCORE: {report.get('trust_score', 0)}\n"
        f"CONTRADICTIONS: {len(report.get('contradictions', []))}\n\n"
        "Attack this report. Find what the panel missed."
    )

    try:
        data = await llm.chat_json(
            RETEAM_SYSTEM, prompt,
            temperature=0.3, max_tokens=4000, log=log,
        )
    except Exception as e:
        if log:
            log(f"red-team probe failed: {e}")
        return []

    valid_vectors = {"source_quality", "staleness", "scope_creep",
                     "entity_confusion", "missing_evidence"}
    valid_severities = {"high", "medium", "low"}
    valid_claim_ids = {c["id"] for c in report.get("claims", [])}

    findings = []
    for f in data.get("findings", []):
        if (f.get("claim_id") in valid_claim_ids
                and f.get("attack_vector") in valid_vectors
                and f.get("severity") in valid_severities
                and f.get("finding")):
            findings.append({
                "claim_id": f["claim_id"],
                "attack_vector": f["attack_vector"],
                "severity": f["severity"],
                "finding": f["finding"][:500],
                "recommendation": (f.get("recommendation") or "")[:300],
                "probed_at": time.time(),
            })

    if log:
        high = sum(1 for f in findings if f["severity"] == "high")
        log(f"red-team found {len(findings)} issue(s) ({high} high-severity)")

    return findings


def findings_to_trap_cases(findings: list[dict], report: dict) -> list[dict]:
    """Convert high-severity red-team findings into trap-suite test cases.

    This is the self-improvement loop: the system's own adversarial probing
    generates new regression tests.
    """
    cases = []
    claims_by_id = {c["id"]: c for c in report.get("claims", [])}
    for f in findings:
        if f["severity"] != "high":
            continue
        claim = claims_by_id.get(f["claim_id"])
        if not claim:
            continue
        cases.append({
            "claim": claim["text"],
            "expected_label": "REFUTES" if claim["status"] in ("REFUTED", "CONTESTED") else "SUPPORTS",
            "red_team_finding": {
                "attack_vector": f["attack_vector"],
                "finding": f["finding"],
                "recommendation": f["recommendation"],
            },
            "source": "red_team_agent",
            "created_at": time.time(),
        })
    return cases
