"""The 7 VeriFact agents — each an async function with a focused prompt.

1. Planner              — decompose topic into subtopics + diverse search queries
2. Researcher           — Tavily multi-query search, dedup, rank (no LLM)
3. Extractor            — atomic claim decomposition (FActScore-style)
4. Verifier panel (×3)  — adversarial lenses: evidentialist / skeptic / contextualist
5. ContradictionDetector— cross-claim, source-vs-claim, verifier-disagreement
6. Writer               — citation-backed report compilation
"""
import asyncio
import json

import llm
import tavily_client
from models import Claim, Contradiction, Report, Source, Verdict

# ---------------------------------------------------------------------------
# 1. PLANNER
# ---------------------------------------------------------------------------

PLANNER_SYSTEM = """You are a research director planning a fact-verification investigation.
Decompose the topic into 3-5 subtopics and generate 6-8 DIVERSE search queries
covering different angles: official/primary sources, statistics, recent
developments, and critical perspectives. Avoid duplicate angles.

Return JSON:
{"subtopics": ["..."], "search_queries": ["...", "..."]}"""


async def planner(topic: str, log=None) -> dict:
    data = await llm.chat_json(
        PLANNER_SYSTEM,
        f"Topic to investigate: {topic}",
        temperature=0.3,
        max_tokens=1500,
        log=log,
    )
    queries = data.get("search_queries") or [topic]
    return {"subtopics": data.get("subtopics", [topic]), "search_queries": queries[:8]}


# ---------------------------------------------------------------------------
# 2. RESEARCHER (tool orchestration — no LLM)
# ---------------------------------------------------------------------------

async def researcher(queries: list[str], log=None) -> list[Source]:
    """Parallel Tavily searches, dedup by URL, cap at 12 sources."""
    seen, sources, sid = set(), [], 1
    # 2 queries at a time to stay polite to the API
    for i in range(0, len(queries), 2):
        batch = queries[i : i + 2]
        results = await asyncio.gather(
            *(tavily_client.search(q, max_results=4) for q in batch)
        )
        for hits in results:
            for hit in hits:
                url = hit.get("url", "")
                if not url or url in seen:
                    continue
                seen.add(url)
                sources.append(
                    Source(
                        id=sid,
                        title=hit.get("title", url)[:200],
                        url=url,
                        snippet=hit.get("content", "")[:1200],
                        score=float(hit.get("score") or 0.5),
                    )
                )
                sid += 1
        if log:
            log(f"{len(sources)} unique sources so far")
    return sources[:12]


def _sources_block(sources: list[Source]) -> str:
    return "\n\n".join(
        f"[S{s.id}] {s.title}\nURL: {s.url}\n{s.snippet}" for s in sources
    )


# ---------------------------------------------------------------------------
# 3. EXTRACTOR (atomic claim decomposition)
# ---------------------------------------------------------------------------

EXTRACTOR_SYSTEM = """You are a fact-checking analyst. Decompose the research material
into 6-10 ATOMIC claims: one verifiable fact per claim, no compound sentences,
no opinions, no vague statements. Prefer concrete facts: dates, numbers,
entities, causal relationships. Tag each claim with the source IDs ([S1], [S2]…)
it is drawn from.

IMPORTANT: If the TOPIC itself makes a factual assertion (e.g. "X did Y",
"X is the largest Y"), include that assertion VERBATIM as the FIRST claim
(claim_type "fact", source_ids from any source that confirms or denies it),
so the verification panel can confirm or refute the premise directly.

Return JSON:
{"claims": [{"text": "...", "claim_type": "fact|statistic|date|entity", "source_ids": [1, 2]}]}"""


async def extractor(sources: list[Source], topic: str, log=None) -> list[Claim]:
    data = await llm.chat_json(
        EXTRACTOR_SYSTEM,
        f"Topic: {topic}\n\nResearch material:\n{_sources_block(sources)}",
        temperature=0.1,
        max_tokens=3000,
        log=log,
    )
    claims, cid = [], 1
    for c in (data.get("claims") or [])[:10]:
        text = (c.get("text") or "").strip()
        if not text:
            continue
        claims.append(
            Claim(
                id=cid,
                text=text,
                claim_type=c.get("claim_type", "fact"),
                source_ids=[int(s) for s in c.get("source_ids", []) if str(s).isdigit()][:4],
            )
        )
        cid += 1
    if not claims:
        raise ValueError("Extractor produced no claims")
    return claims


# ---------------------------------------------------------------------------
# 4. VERIFIER PANEL — three adversarial lenses, run in parallel
# ---------------------------------------------------------------------------

def _verifier_system(persona: str, bias: str) -> str:
    return f"""You are Verifier {persona}, an independent fact-checker.
{bias}

RULES:
- For EACH claim return a verdict: "support", "refute", or "insufficient".
- You MUST cite the source IDs ([S1], [S2]…) your verdict rests on. A verdict
  without cited evidence is invalid — use "insufficient" instead.
- Reasoning: 1-2 sentences, concrete, quoting the relevant snippet.

Return JSON:
{{"verdicts": [{{"claim_id": 1, "stance": "support|refute|insufficient", "reasoning": "...", "source_ids": [1]}}]}}"""

VERIFIERS = [
    (
        "A — Evidentialist",
        "Your lens: LITERAL EVIDENCE. Support a claim ONLY if a source explicitly "
        "states it. You never infer, extrapolate, or use outside knowledge. "
        "If the sources are silent on a claim, your verdict is 'insufficient'.",
    ),
    (
        "B — Skeptic",
        "Your lens: ADVERSARIAL SCRUTINY. Actively try to REFUTE each claim. Hunt "
        "for outdated information, confusion between similar entities, unsourced "
        "assertions, and numbers without provenance. Default to 'insufficient' "
        "unless the evidence is strong and specific. You are the panel's immune "
        "system against hallucination.",
    ),
    (
        "C — Contextualist",
        "Your lens: PRECISION & CURRENCY. Check dates, numbers, and scope. Refute "
        "claims that were once true but are outdated, true only with omitted "
        "caveats, or stated more absolutely than the sources justify.",
    ),
]


async def _one_verifier(persona: str, bias: str, claims: list[Claim],
                        sources: list[Source], log=None) -> list[tuple[int, Verdict]]:
    claims_block = "\n".join(f"[C{c.id}] {c.text}" for c in claims)
    data = await llm.chat_json(
        _verifier_system(persona, bias),
        f"CLAIMS:\n{claims_block}\n\nSOURCES:\n{_sources_block(sources)}",
        temperature=0.1,
        max_tokens=4000,
        log=log,
    )
    tag = persona.split(" ")[0]  # "A" | "B" | "C"
    valid_ids = {c.id for c in claims}
    out = []
    raw = data.get("verdicts") or []
    for i, v in enumerate(raw):
        stance = v.get("stance", "insufficient")
        if stance not in ("support", "refute", "insufficient"):
            stance = "insufficient"
        cid = v.get("claim_id")
        if cid not in valid_ids:
            cid = claims[i].id if i < len(claims) else None  # positional fallback
        if cid is None:
            continue
        out.append((
            cid,
            Verdict(
                verifier=tag,
                stance=stance,
                reasoning=(v.get("reasoning") or "")[:400],
                source_ids=[int(s) for s in v.get("source_ids", []) if str(s).isdigit()][:4],
            ),
        ))
    return out


async def verifier_panel(claims: list[Claim], sources: list[Source], log=None):
    """Run all three verifiers concurrently (they land on different rotated keys).

    Returns (by_claim: {claim_id: [Verdict]}, failed_count).
    Tolerates a failed verifier — 2 of 3 still yields a majority.
    """
    results = await asyncio.gather(
        *(_one_verifier(p, b, claims, sources, log) for p, b in VERIFIERS),
        return_exceptions=True,
    )
    by_claim: dict[int, list[Verdict]] = {c.id: [] for c in claims}
    failed = 0
    for r in results:
        if isinstance(r, Exception):
            failed += 1
            if log:
                log(f"verifier failed: {r}")
            continue
        for cid, verdict in r:
            by_claim[cid].append(verdict)
    return by_claim, failed


# ---------------------------------------------------------------------------
# 5. CONTRADICTION DETECTOR
# ---------------------------------------------------------------------------

CONTRADICTION_SYSTEM = """You are a hostile fact-checking editor. Given claims, the
verifier panel's verdicts, and the sources, find EVERY genuine problem:
1. verifier_disagreement — verifiers split (one supports, another refutes)
2. source_refuted — a retrieved source directly contradicts a claim
3. internal_conflict — two claims in the set contradict each other

Report NONE if there genuinely are none — false alarms destroy trust.
For each finding, explain the conflict concretely in 1-2 sentences.

Return JSON:
{"contradictions": [{"claim_id": 1, "kind": "verifier_disagreement|source_refuted|internal_conflict", "description": "..."}]}"""


async def contradiction_detector(claims: list[Claim], by_claim: dict,
                                 sources: list[Source], log=None) -> list[Contradiction]:
    evidence = []
    for c in claims:
        verdicts = by_claim.get(c.id, [])
        v_block = "; ".join(
            f"{v.verifier}={v.stance} ({v.reasoning[:120]})" for v in verdicts
        ) or "no verdicts"
        evidence.append(f"[C{c.id}] {c.text}\n  verdicts: {v_block}")

    data = await llm.chat_json(
        CONTRADICTION_SYSTEM,
        f"CLAIMS + VERDICTS:\n" + "\n".join(evidence) +
        f"\n\nSOURCES:\n{_sources_block(sources)}",
        temperature=0.1,
        max_tokens=2500,
        log=log,
    )
    valid = {c.id for c in claims}
    kinds = {"verifier_disagreement", "source_refuted", "internal_conflict"}
    out = []
    for cd in data.get("contradictions") or []:
        cid = cd.get("claim_id")
        kind = cd.get("kind", "verifier_disagreement")
        if cid in valid and kind in kinds and cd.get("description"):
            out.append(Contradiction(
                claim_id=cid, kind=kind, description=cd["description"][:500]
            ))
    return out


# ---------------------------------------------------------------------------
# 6. WRITER (report compiler)
# ---------------------------------------------------------------------------

WRITER_SYSTEM = """You are the report compiler for a fact-verification system.
Write a concise research briefing from VERIFIED material only.

Rules:
- "summary": 3-5 sentences synthesizing the verified findings. Every factual
  sentence ends with citation markers like [1][3] referencing source IDs.
- "claim_report": one entry per claim with a short "verification_note"
  (what the verifiers concluded, in plain language).
- CONTRADICTED claims must NOT appear in the summary as facts — mention them
  only as corrections ("contrary to the common claim that X, sources show Y [n]").
- Never invent facts or citations not present in the input.

Return JSON:
{"summary": "...", "claim_report": [{"claim_id": 1, "verification_note": "..."}]}"""


async def writer(topic: str, claims: list[Claim], by_claim: dict,
                 contradictions: list[Contradiction], sources: list[Source],
                 log=None) -> dict:
    claim_block = []
    for c in claims:
        verdicts = by_claim.get(c.id, [])
        v_block = "; ".join(f"{v.verifier}={v.stance}" for v in verdicts) or "n/a"
        claim_block.append(
            f"[C{c.id}] {c.text}\n  status={c.status} confidence={c.confidence} "
            f"verdicts: {v_block} sources: {c.source_ids}"
        )
    contra_block = "\n".join(
        f"[C{cd.claim_id}] {cd.kind}: {cd.description}" for cd in contradictions
    ) or "none"

    data = await llm.chat_json(
        WRITER_SYSTEM,
        f"Topic: {topic}\n\nCLAIMS (verified):\n" + "\n".join(claim_block) +
        f"\n\nCONTRADICTIONS:\n{contra_block}\n\nSOURCES:\n{_sources_block(sources)}",
        temperature=0.3,
        max_tokens=4000,
        log=log,
    )
    return {
        "summary": data.get("summary", ""),
        "claim_report": data.get("claim_report", []),
    }
