"""The Research Court — Phase 1 agents.

- claim extraction anchored to evidence chunks (hypothesis-attributed)
- adversarial verifier panel v2: exact-quote SPAN GATE — a verdict whose
  quote doesn't exist verbatim in the corpus is voided (catches
  hallucinated citations), and only span-valid verdicts count toward the
  majority. Verdicts are HMAC-signed (non-repudiation).
- typed hallucination detector (7 types)
"""
import asyncio
import hashlib
import hmac
import os
import re

import llm
from evidence import validate_span
from models import Claim, Verdict

# ---------------------------------------------------------------------------
# corpus rendering
# ---------------------------------------------------------------------------

def _chunks_of(source) -> list:
    return source.__dict__.get("_chunks", [])


def corpus_block(sources, max_chars: int = 30000) -> str:
    """Render the evidence corpus for agent prompts: [C{id}] chunks w/ source meta."""
    parts, used = [], 0
    for s in sources:
        header = (f"=== SOURCE S{s.id} [{s.authority_label}] {s.publisher} "
                  f"({s.origin}) ===\n{s.title}\nURL: {s.url}")
        chunks = _chunks_of(s)
        if not chunks:
            block = f"{header}\n[snippet only] {s.snippet[:400]}"
        else:
            chunk_txt = "\n".join(
                f"[{ch.id}] {ch.text[:1200]}" for ch in chunks[:4]
            )
            block = f"{header}\n{chunk_txt}"
        if used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block)
    return "\n\n".join(parts)


def chunk_index(sources) -> dict[str, str]:
    """chunk_id -> chunk text (for span validation)."""
    idx = {}
    for s in sources:
        for ch in _chunks_of(s):
            idx[ch.id] = ch.text
    return idx


def chunk_source_map(sources) -> dict[str, int]:
    return {ch.id: s.id for s in sources for ch in _chunks_of(s)}


# ---------------------------------------------------------------------------
# claim extraction (anchored, hypothesis-attributed)
# ---------------------------------------------------------------------------

EXTRACT_SYSTEM = """You are the court's claim analyst. Decompose the evidence corpus
into 6-10 ATOMIC claims: one verifiable fact per claim, no compound sentences,
no opinions. Prefer concrete facts: dates, numbers, entities, causal links.

For each claim:
- anchor it to the evidence chunk(s) it comes from (chunk IDs like "C3.1")
- attribute it to the hypothesis it bears on (H1/H2/H3), if applicable
- CONSISTENCY RULE: a claim must state what its anchored chunk(s) actually
  assert. If a chunk REFUTES an idea, do not extract that idea as a claim —
  extract the chunk's actual assertion instead.
- if the TOPIC itself makes a factual assertion, include that assertion VERBATIM
  as the FIRST claim (claim_type "fact") so the panel can confirm or refute
  the premise directly.

Return JSON:
{"claims": [{"text": "...", "claim_type": "fact|statistic|date|entity|causal",
             "hypothesis_id": "H1", "chunk_ids": ["C1.0", "C2.1"]}]}"""


async def extract_claims(sources, hypotheses, topic, log=None) -> list[Claim]:
    h_block = "\n".join(f"{h.id}: {h.statement}" for h in hypotheses)
    data = await llm.chat_json(
        EXTRACT_SYSTEM,
        f"Topic: {topic}\n\nHypotheses:\n{h_block}\n\nEvidence corpus:\n{corpus_block(sources)}",
        temperature=0.1, max_tokens=3500, log=log,
    )
    valid_chunks = chunk_source_map(sources)
    claims, cid = [], 1
    for c in (data.get("claims") or [])[:10]:
        text = (c.get("text") or "").strip()
        if not text:
            continue
        chunk_ids = [x for x in (c.get("chunk_ids") or []) if x in valid_chunks][:4]
        claims.append(Claim(
            id=cid, text=text,
            claim_type=c.get("claim_type", "fact"),
            hypothesis_id=c.get("hypothesis_id") or "",
            chunk_ids=chunk_ids,
            source_ids=sorted({valid_chunks[x] for x in chunk_ids}),
        ))
        cid += 1
    if not claims:
        raise ValueError("Claim extraction produced no claims")
    return claims


# ---------------------------------------------------------------------------
# verifier panel v2 — span gate + signatures
# ---------------------------------------------------------------------------

def sign_verdict(run_key: str, verifier: str, claim_id: int, stance: str,
                 quote: str) -> str:
    msg = f"{verifier}|{claim_id}|{stance}|{quote}".encode("utf-8")
    return hmac.new(run_key.encode("utf-8"), msg, hashlib.sha256).hexdigest()[:32]


def _verifier_system(persona: str, bias: str) -> str:
    return f"""You are Verifier {persona}, an independent fact-checker on the court.
{bias}

THE SPAN GATE (strict):
- For each claim return: stance ("support"|"refute"|"insufficient"), 1-2
  sentences of reasoning, and a QUOTE — the exact sentence(s) from the
  evidence corpus your verdict rests on, copied verbatim from a chunk.
- Cite the chunk_id the quote comes from (e.g. "C3.1").
- A verdict WITHOUT a verbatim quote from the corpus is VOID. If the corpus
  is silent on a claim, your stance is "insufficient" — never guess.

Return JSON:
{{"verdicts": [{{"claim_id": 1, "stance": "support", "reasoning": "...",
               "quote": "exact sentence from a chunk", "chunk_id": "C1.0"}}]}}"""

VERIFIERS = [
    ("A — Evidentialist",
     "Your lens: LITERAL EVIDENCE. Support a claim ONLY if a source explicitly "
     "states it. You never infer, extrapolate, or use outside knowledge."),
    ("B — Skeptic",
     "Your lens: ADVERSARIAL SCRUTINY. Actively try to REFUTE each claim. Hunt "
     "for outdated information, confused entities, unsourced assertions, "
     "numbers without provenance. Default to 'insufficient' unless evidence "
     "is strong and specific. You are the panel's immune system against "
     "hallucination."),
    ("C — Contextualist",
     "Your lens: PRECISION & CURRENCY. Check dates, numbers, scope. Refute "
     "claims that were once true but are outdated, true only with omitted "
     "caveats, or stated more absolutely than the sources justify."),
]


async def _one_verifier(persona, bias, claims, corpus, chunks, run_key, log=None,
                        model=None):
    claims_block = "\n".join(f"[C{c.id}] {c.text}" for c in claims)
    data = await llm.chat_json(
        _verifier_system(persona, bias),
        f"CLAIMS:\n{claims_block}\n\nEVIDENCE CORPUS:\n{corpus}",
        temperature=0.1, max_tokens=4500, log=log, model=model,
    )
    tag = persona.split(" ")[0]
    valid_ids = {c.id for c in claims}
    out = []
    for i, v in enumerate(data.get("verdicts") or []):
        stance = v.get("stance", "insufficient")
        if stance not in ("support", "refute", "insufficient"):
            stance = "insufficient"
        cid = v.get("claim_id")
        if cid not in valid_ids:
            cid = claims[i].id if i < len(claims) else None
        if cid is None:
            continue
        quote = (v.get("quote") or "").strip().strip('"').strip("'")
        quote = re.sub(r"\s+", " ", quote).replace("…", "...")
        chunk_id = v.get("chunk_id") or ""
        chunk_text = chunks.get(chunk_id, "")
        span_valid = bool(quote) and bool(chunk_text) and validate_span(quote, chunk_text)
        # SPAN GATE: unverifiable quotes void the verdict's vote
        if stance in ("support", "refute") and not span_valid:
            stance = "insufficient"
        out.append((cid, Verdict(
            verifier=tag, stance=stance,
            reasoning=(v.get("reasoning") or "")[:400],
            quote=quote[:600], chunk_id=chunk_id, span_valid=span_valid,
            signature=sign_verdict(run_key, tag, cid, stance, quote[:600]),
        )))
    return out


async def verifier_panel(claims, sources, run_key, log=None):
    """3 adversarial verifiers in parallel. Returns ({claim_id: [Verdict]}, failures).

    Multi-model A/B scaffolding (Phase 2): set VERIFIER_MODELS to a
    comma-separated list (e.g. "modelA,modelB,modelC") and each verifier
    runs on its own model — model diversity. Unset = persona diversity
    on one model. The harness records which config ran so results compare.
    """
    corpus = corpus_block(sources)
    chunks = chunk_index(sources)
    models = [m.strip() or None
              for m in os.environ.get("VERIFIER_MODELS", "").split(",")]
    results = await asyncio.gather(
        *(_one_verifier(p, b, claims, corpus, chunks, run_key, log,
                        model=models[i] if i < len(models) else None)
          for i, (p, b) in enumerate(VERIFIERS)),
        return_exceptions=True,
    )
    by_claim = {c.id: [] for c in claims}
    failures = 0
    for r in results:
        if isinstance(r, Exception):
            failures += 1
            if log:
                log(f"verifier failed: {r}")
            continue
        for cid, verdict in r:
            by_claim[cid].append(verdict)
    voided = sum(
        1 for vs in by_claim.values() for v in vs
        if v.quote and not v.span_valid
    )
    if voided and log:
        log(f"span gate voided {voided} unverifiable quote(s)")
    return by_claim, failures


async def quick_verify(claims, sources, run_key, log=None):
    """Fast-path verification (Phase 3 memory replay): a single Evidentialist
    pass on the few claims memory couldn't settle. Skips the full 3-verifier
    panel + debate — used when ≥80% of claims are already cached, so the court
    only needs to rule on the genuinely new ones. Returns ({claim_id:[Verdict]}, failures).
    """
    corpus = corpus_block(sources)
    chunks = chunk_index(sources)
    persona, bias = VERIFIERS[0]
    try:
        out = await _one_verifier(persona, bias, claims, corpus, chunks, run_key, log)
    except Exception as e:
        if log:
            log(f"quick verify degraded: {e}")
        return {c.id: [] for c in claims}, 1
    by_claim = {c.id: [] for c in claims}
    for cid, verdict in out:
        by_claim[cid].append(verdict)
    return by_claim, 0


# ---------------------------------------------------------------------------
# multi-turn debate (Phase 3) — deliberation + Judge
# ---------------------------------------------------------------------------

def _needs_debate(stances: list[str]) -> bool:
    """No 2/3 consensus AND at least one substantive (non-insufficient) vote."""
    n = len(stances) or 1
    sup, ref = stances.count("support"), stances.count("refute")
    if max(sup, ref) / n >= 2 / 3:
        return False
    return (sup + ref) >= 1


def _latest_stances(verdicts: list) -> list[str]:
    """Each verifier's most recent stance (later rounds override earlier)."""
    latest: dict[str, str] = {}
    for v in verdicts:
        latest[v.verifier] = v.stance
    return list(latest.values())


def _deliberate_system(persona: str) -> str:
    tag = persona.split(" ")[0]
    return f"""You are Verifier {tag} in Round 2 of the court's deliberation.
The panel split on the claims below. You have seen the other verifiers'
Round-1 positions. For EACH contested claim, respond with exactly one action:

- "concede" — their evidence changed your mind. Adopt the stronger stance
  and say what convinced you.
- "rebut" — you hold AND attack their position. A rebuttal MUST cite an
  evidence span the others missed or misread (verbatim quote + chunk_id).
  A rebuttal whose quote is not in the corpus is VOID.
- "hold" — you maintain your verdict; the others raised nothing new
  (say why, briefly).

Return JSON:
{{"responses": [{{"claim_id": 1, "action": "concede|rebut|hold",
                "stance": "support|refute|insufficient", "reasoning": "...",
                "quote": "exact sentence from a chunk", "chunk_id": "C1.0"}}]}}"""


JUDGE_SYSTEM = """You are the JUDGE of the court. After two rounds of debate the
verifier panel still has no 2/3 consensus on the claims below. Read every
verifier's positions and their cited evidence across both rounds, weigh
evidence quality (authority tier, specificity, recency, span validity),
and RULE on each claim.

Your ruling must:
- pick a stance ("support"|"refute"|"insufficient")
- quote the decisive evidence span verbatim (chunk_id)
- explain in 2-3 sentences why the prevailing evidence wins
- record the DISSENT: what the losing side argued, and why it fails

Return JSON:
{"rulings": [{"claim_id": 1, "stance": "...", "reasoning": "...",
              "quote": "...", "chunk_id": "...", "dissent": "..."}]}"""


async def _deliberate(persona, bias, contested_ids, by_claim, claims_by_id,
                      corpus, chunks, run_key, log=None):
    """Round 2: one verifier reconsiders the contested claims."""
    tag = persona.split(" ")[0]
    r1_stance = {}   # claim_id -> this verifier's round-1 stance (for voided rebuts)
    blocks = []
    for cid in contested_ids:
        claim = claims_by_id[cid]
        mine = [v for v in by_claim[cid] if v.verifier == tag and v.round == 1]
        others = [v for v in by_claim[cid] if v.verifier != tag]
        if mine:
            r1_stance[cid] = mine[-1].stance
        mine_txt = "; ".join(
            f"{v.stance}: {v.reasoning[:150]} (quote: {v.quote[:120]!r})"
            for v in mine) or "no round-1 verdict"
        others_txt = "; ".join(
            f"{v.verifier}={v.stance}: {v.reasoning[:150]} (quote: {v.quote[:120]!r})"
            for v in others) or "none"
        blocks.append(f"[C{cid}] {claim.text}\n  YOUR round-1 verdict: {mine_txt}"
                      f"\n  OTHERS: {others_txt}")
    try:
        data = await llm.chat_json(
            _deliberate_system(persona),
            "CONTESTED CLAIMS:\n" + "\n\n".join(blocks) +
            f"\n\nEVIDENCE CORPUS:\n{corpus}",
            temperature=0.1, max_tokens=3000, log=log,
        )
    except Exception as e:
        if log:
            log(f"deliberation ({tag}) degraded: {e}")
        return []
    out = []
    for r in data.get("responses") or []:
        cid = r.get("claim_id")
        if cid not in contested_ids:
            continue
        action = r.get("action", "hold")
        if action not in ("concede", "rebut", "hold"):
            action = "hold"
        stance = r.get("stance", "insufficient")
        if stance not in ("support", "refute", "insufficient"):
            stance = "insufficient"
        quote = re.sub(r"\s+", " ", (r.get("quote") or "").strip().strip('"').strip("'"))
        quote = quote.replace("…", "...")
        chunk_id = r.get("chunk_id") or ""
        chunk_text = chunks.get(chunk_id, "")
        span_valid = bool(quote) and bool(chunk_text) and validate_span(quote, chunk_text)
        # span gate: a rebuttal with a fabricated quote falls back to "hold"
        if action == "rebut" and stance in ("support", "refute") and not span_valid:
            action = "hold"
            stance = r1_stance.get(cid, "insufficient")
        out.append((cid, Verdict(
            verifier=tag, stance=stance,
            reasoning=(r.get("reasoning") or "")[:400],
            quote=quote[:600], chunk_id=chunk_id, span_valid=span_valid,
            signature=sign_verdict(run_key, tag, cid, stance, quote[:600]),
            round=2, action=action,
        )))
    return out


async def _judge(contested_ids, by_claim, claims_by_id, corpus, chunks,
                 run_key, log=None):
    """Round 3: the Judge rules on claims the panel could not settle."""
    blocks = []
    for cid in contested_ids:
        claim = claims_by_id[cid]
        v_txt = "\n".join(
            f"  R{v.round} {v.verifier} ({v.action or 'verdict'}) = {v.stance}: "
            f"{v.reasoning[:200]}" + (f" [quote: {v.quote[:150]!r}]" if v.quote else "")
            for v in by_claim[cid])
        blocks.append(f"[C{cid}] {claim.text}\n{v_txt}")
    try:
        data = await llm.chat_json(
            JUDGE_SYSTEM,
            "CLAIMS UNDER JUDGMENT:\n" + "\n\n".join(blocks) +
            f"\n\nEVIDENCE CORPUS:\n{corpus}",
            temperature=0.1, max_tokens=2500, log=log,
        )
    except Exception as e:
        if log:
            log(f"judge degraded: {e}")
        return []
    out = []
    for r in data.get("rulings") or []:
        cid = r.get("claim_id")
        if cid not in contested_ids:
            continue
        stance = r.get("stance", "insufficient")
        if stance not in ("support", "refute", "insufficient"):
            stance = "insufficient"
        quote = re.sub(r"\s+", " ", (r.get("quote") or "").strip().strip('"').strip("'"))
        quote = quote.replace("…", "...")
        chunk_id = r.get("chunk_id") or ""
        chunk_text = chunks.get(chunk_id, "")
        span_valid = bool(quote) and bool(chunk_text) and validate_span(quote, chunk_text)
        out.append((cid, Verdict(
            verifier="J", stance=stance,
            reasoning=(r.get("reasoning") or "")[:500],
            quote=quote[:600], chunk_id=chunk_id, span_valid=span_valid,
            signature=sign_verdict(run_key, "J", cid, stance, quote[:600]),
            round=3, action="judge", dissent=(r.get("dissent") or "")[:400],
        )))
    return out


def build_transcript(by_claim, claims_by_id) -> list[dict]:
    """Chronological debate record for the UI and the stored report."""
    entries = []
    for cid, verdicts in by_claim.items():
        for v in verdicts:
            entries.append({
                "claim_id": cid, "claim": claims_by_id[cid].text,
                "round": v.round, "verifier": v.verifier,
                "action": v.action or "verdict", "stance": v.stance,
                "reasoning": v.reasoning, "quote": v.quote,
                "chunk_id": v.chunk_id, "span_valid": v.span_valid,
                "dissent": v.dissent,
            })
    entries.sort(key=lambda e: (e["round"], e["claim_id"], e["verifier"]))
    return entries


async def debate(by_claim, claims, sources, run_key, log=None):
    """Multi-turn deliberation on contested claims.

    Round 2 — each verifier reads the others' verdicts and concedes, rebuts
    (must cite missed evidence), or holds. Round 3 — if still no 2/3
    consensus, the Judge rules and records the dissent. Consensus after any
    round short-circuits the next (latency budget: at most +2 rounds).

    Returns (by_claim, transcript, rounds_used).
    """
    claims_by_id = {c.id: c for c in claims}
    contested = [cid for cid, vs in by_claim.items()
                 if _needs_debate([v.stance for v in vs])]
    if not contested:
        return by_claim, build_transcript(by_claim, claims_by_id), 1
    if log:
        log(f"panel split on {len(contested)} claim(s) → deliberation round 2")

    corpus = corpus_block(sources)
    chunks = chunk_index(sources)

    # --- round 2: deliberation (one call per verifier, parallel) ------------
    results = await asyncio.gather(
        *(_deliberate(p, b, contested, by_claim, claims_by_id, corpus, chunks,
                      run_key, log)
          for p, b in VERIFIERS),
        return_exceptions=True,
    )
    for r in results:
        if isinstance(r, Exception):
            if log:
                log(f"deliberation failed: {r}")
            continue
        for cid, verdict in r:
            by_claim[cid].append(verdict)

    rounds = 2
    # --- round 3: Judge on claims STILL without consensus -------------------
    still = [cid for cid in contested
             if _needs_debate(_latest_stances(by_claim[cid]))]
    if still:
        if log:
            log(f"no consensus after deliberation on {len(still)} claim(s) → Judge")
        rulings = await _judge(still, by_claim, claims_by_id, corpus, chunks,
                               run_key, log)
        for cid, verdict in rulings:
            by_claim[cid].append(verdict)
        rounds = 3

    return by_claim, build_transcript(by_claim, claims_by_id), rounds


# ---------------------------------------------------------------------------
# hallucination detector — typed taxonomy
# ---------------------------------------------------------------------------

HALLUCINATION_SYSTEM = """You are the court's hallucination auditor. For each claim,
check the evidence corpus for these failure types:
- entity:      wrong/confused person, org, or place
- relation:    wrong relationship ("founded" vs "worked at")
- number:      wrong figure vs. sources
- date:        wrong year/period
- extrapolation: claim says more than the evidence ("all" from one case)
- unsupported: no corpus evidence at all
- staleness:   was true, superseded by newer evidence

Report ONLY genuine findings with the exact evidence. No speculation.

Return JSON:
{"findings": [{"claim_id": 1, "type": "number", "severity": "high|medium|low",
               "evidence": "what the corpus actually says",
               "correction": "corrected version of the claim, if known"}]}"""


async def detect_hallucinations(claims, sources, log=None) -> dict[int, list[dict]]:
    claims_block = "\n".join(f"[C{c.id}] {c.text}" for c in claims)
    try:
        data = await llm.chat_json(
            HALLUCINATION_SYSTEM,
            f"CLAIMS:\n{claims_block}\n\nEVIDENCE CORPUS:\n{corpus_block(sources, 20000)}",
            temperature=0.1, max_tokens=3000, log=log,
        )
    except Exception as e:
        if log:
            log(f"hallucination detector degraded: {e}")
        return {}
    types = {"entity", "relation", "number", "date", "extrapolation",
             "unsupported", "staleness"}
    valid = {c.id for c in claims}
    out: dict[int, list[dict]] = {}
    for f in data.get("findings") or []:
        cid = f.get("claim_id")
        if cid in valid and f.get("type") in types:
            out.setdefault(cid, []).append({
                "type": f["type"],
                "severity": f.get("severity", "medium"),
                "evidence": (f.get("evidence") or "")[:300],
                "correction": (f.get("correction") or "")[:300],
            })
    return out
