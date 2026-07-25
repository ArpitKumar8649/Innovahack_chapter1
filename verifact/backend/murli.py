"""The Murli Agent — Multi-modal Unified Reasoning Loop Integrator.

The core research agent. Unlike a standard scraper-agent, Murli:
1. generates 3 competing HYPOTHESES ("theories of truth") for the topic,
2. runs a SELF-QUERY LOOP on each: "if this is wrong, why? what would
   disprove it?" — and issues those as REAL searches,
3. requisitions evidence via Serper (web + scholar + news),
4. plays DEVIL'S ADVOCATE: dedicated counter-evidence searches,
5. hands the court a corpus of full-text sources (Tavily extract),
   chunked and content-hashed (FEC foundation).

Standard agents "yes-sir" the prompt. Murli attacks its own findings
before the verifier panel even convenes — pre-filtering hallucination
at the source.
"""
import asyncio
import datetime

import llm
import serper_client
import tavily_client
from evidence import (TIER_LABEL, authority_tier, chunk_text, publisher_of,
                      sha256_hex)
from models import ChunkRef, Hypothesis, Source

HYPOTHESIS_SYSTEM = """You are Murli, a cognitive scientist opening an investigation.
For the given topic, generate 2-3 COMPETING hypotheses ("theories of truth") —
not one answer. If the topic is itself a factual assertion, one hypothesis MUST
be that assertion verbatim, and another must be its strongest negation or
alternative explanation. Assign each a prior plausibility (0-1).
Also generate 5-7 diverse search queries covering: official/primary sources,
statistics, academic research, recent developments, and critical perspectives.

Return JSON:
{"hypotheses": [{"id": "H1", "statement": "...", "plausibility": 0.6}],
 "search_queries": ["...", "..."]}"""

SELF_QUERY_SYSTEM = """You are Murli running a self-adversarial check. For each
hypothesis, ask: "If this is WRONG, why would it be wrong? What evidence would
DISPROVE it? Who disagrees, and on what grounds?" Turn those questions into 1-2
concrete search queries per hypothesis — queries that would find
COUNTER-evidence, not confirmation.
Also state 1-2 honest WEAKNESSES per hypothesis: what it rests on that could
break (single-source dependence, definitional ambiguity, confounders,
unverifiable premises).

Return JSON:
{"counter_queries": {"H1": ["..."], "H2": ["..."]},
 "weaknesses": {"H1": ["..."], "H2": ["..."]}}"""


async def hypothesize(topic: str, log=None) -> tuple[list[Hypothesis], list[str]]:
    data = await llm.chat_json(
        HYPOTHESIS_SYSTEM, f"Topic under investigation: {topic}",
        temperature=0.3, max_tokens=2000, log=log,
    )
    hypotheses = [
        Hypothesis(
            id=h.get("id", f"H{i+1}"),
            statement=h.get("statement", "").strip(),
            plausibility=float(h.get("plausibility", 0.5)),
        )
        for i, h in enumerate((data.get("hypotheses") or [])[:3])
        if h.get("statement")
    ]
    queries = [q for q in (data.get("search_queries") or []) if q][:7]
    if not hypotheses:
        hypotheses = [Hypothesis(id="H1", statement=topic, plausibility=0.5)]
    if not queries:
        queries = [topic]
    return hypotheses, queries


async def self_challenge(hypotheses: list[Hypothesis], log=None) -> None:
    """Self-query loop: generate real counter-evidence queries per hypothesis."""
    h_block = "\n".join(f"{h.id}: {h.statement}" for h in hypotheses)
    try:
        data = await llm.chat_json(
            SELF_QUERY_SYSTEM, f"Hypotheses:\n{h_block}",
            temperature=0.3, max_tokens=1500, log=log,
        )
        for h in hypotheses:
            qs = (data.get("counter_queries") or {}).get(h.id, [])
            h.counter_queries = [q for q in qs if q][:2]
            ws = (data.get("weaknesses") or {}).get(h.id, [])
            h.weaknesses = [w for w in ws if w][:2]
    except Exception as e:
        if log:
            log(f"self-challenge degraded: {e}")


async def requisition_evidence(
    hypotheses: list[Hypothesis], queries: list[str], log=None
) -> list[Source]:
    """Serper (web+scholar+news) → dedup → Tavily full-text extract → chunks+hashes."""

    # --- 1. gather candidate URLs from all angles (bounded concurrency) -----
    scholar_q = queries[0]
    news_q = queries[1] if len(queries) > 1 else queries[0]
    counter_queries = [q for h in hypotheses for q in h.counter_queries][:4]

    sem = asyncio.Semaphore(4)

    async def web(q):
        async with sem:
            return await serper_client.web_search(q, num=10)

    async def scholar(q):
        async with sem:
            return await serper_client.scholar_search(q)

    async def news(q):
        async with sem:
            return await serper_client.news_search(q)

    web_results, scholar_hits, news_hits = await asyncio.gather(
        asyncio.gather(*(web(q) for q in queries[:6])),
        scholar(scholar_q),
        news(news_q),
        return_exceptions=False,
    )
    counter_results = await asyncio.gather(*(web(q) for q in counter_queries))

    # --- 2. merge + dedup, keeping origin + best snippet --------------------
    candidates: dict[str, dict] = {}   # url -> candidate
    paa: list[str] = []

    def add(url, title, snippet, origin, scholar_flag=False):
        if not url or url in candidates:
            return
        candidates[url] = {"title": title, "url": url, "snippet": snippet,
                           "origin": origin, "scholar": scholar_flag}

    for wr in list(web_results) + list(counter_results):
        for r in wr.get("organic", []):
            add(r["url"], r["title"], r.get("snippet", ""), "web")
        paa += wr.get("people_also_ask", [])
    for r in scholar_hits:
        add(r["url"], r["title"], r.get("snippet", ""), "scholar", scholar_flag=True)
    for r in news_hits:
        add(r["url"], r["title"], r.get("snippet", ""), "news")

    if log:
        log(f"{len(candidates)} candidate URLs "
            f"({len(scholar_hits)} scholar, {len(news_hits)} news, "
            f"{len(counter_queries)} counter-queries issued)")

    # --- 3. rank: scholar first, then SERP order; cap ------------------------
    ranked = sorted(candidates.values(),
                    key=lambda c: (0 if c["scholar"] else 1))[:16]

    # ---4. Tavily full-text extraction (basic, then advanced retry) ---------
    extracted = await tavily_client.extract([c["url"] for c in ranked])
    missing = [c["url"] for c in ranked if c["url"] not in extracted]
    if missing:
        retry = await tavily_client.extract(missing, depth="advanced")
        extracted.update(retry)
    if log:
        log(f"full text extracted for {len(extracted)}/{len(ranked)} sources")

    # --- 5. build Sources with chunks + hashes (FEC foundation) --------------
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    sources: list[Source] = []
    for i, c in enumerate(ranked, start=1):
        content = extracted.get(c["url"], "")
        chunks = chunk_text(content, i) if content else []
        tier = 1 if c["scholar"] else authority_tier(c["url"])
        sources.append(Source(
            id=i,
            title=(c["title"] or c["url"])[:200],
            url=c["url"],
            publisher=publisher_of(c["url"]),
            authority_tier=tier,
            authority_label=TIER_LABEL[tier],
            retrieved_at=now,
            origin=c["origin"],
            snippet=c["snippet"][:800],
            content_hash=sha256_hex(content) if content else "",
            chunks=[ChunkRef(chunk_id=ch.id, text=ch.text, hash=ch.hash)
                    for ch in chunks],
        ))
        # stash chunk texts on the object for downstream agents (not serialized)
        sources[-1].__dict__["_chunks"] = chunks

    # keep only sources with extractable content (fallback: keep top snippet-only)
    with_content = [s for s in sources if s.content_hash]
    if with_content:
        return with_content
    return sources  # degraded mode: snippet-only (v1 behavior)
