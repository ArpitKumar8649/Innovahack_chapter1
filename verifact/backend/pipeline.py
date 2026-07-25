"""Research Court orchestrator — the 10-stage execution flow.

Intake (memory priors) → Hypotheses (Murli) → Self-challenge → Evidence
requisition (Serper→Tavily, full-text, hashed) → Claim extraction (anchored)
→ Cache check (freshly-verified claims reused from memory) → Adversarial
verification (span-gated, signed) → Multi-turn debate (deliberation + Judge)
→ Hallucination sweep → Contradiction sweep → Trust scoring → Synthesis +
Merkle anchoring → Learning (claims, domains, content hashes recorded).

Every stage emits SSE events; the finished run is journaled to SQLite
with its Merkle root and signed verdicts (FEC layers 2-3).
"""
import os
import secrets
import time

import authority
import court
import llm
import memory
import murli
import scoring
from evidence import Chunk, merkle_proof, merkle_root, publisher_of
from models import ChunkRef, Report, Source, Verdict

STAGES = ["intake", "hypothesize", "research", "extract", "verify",
          "deliberate", "hallucinations", "contradictions", "report"]


class Run:
    def __init__(self, run_id: str, topic: str):
        self.id = run_id
        self.topic = topic
        self.run_key = secrets.token_hex(16)   # per-run HMAC key (published w/ report)
        self.history: list[tuple[str, dict]] = []
        self.report: Report | None = None
        self.error: str | None = None
        self.done = False
        self.started = time.time()
        self.priors: list[dict] = []

    def emit(self, event: str, data: dict):
        self.history.append((event, data))

    def log(self, stage: str, msg: str):
        self.emit("log", {"stage": stage, "message": msg})


def _cached_verdict(prior: dict, run_key: str, claim_id: int) -> Verdict:
    """A memory-sourced verdict — signed, marked round-0/cache."""
    stance = prior["last_verdict"] or "insufficient"
    quote = ""
    return Verdict(
        verifier="M", stance=stance,
        reasoning=(f"Reused from memory: verified {prior['age_days']}d ago "
                   f"({prior['status']}, confidence {prior['confidence']}, "
                   f"seen {prior['times_seen']}×). Re-verified only if this "
                   "run's panel disagrees."),
        quote=quote, chunk_id="", span_valid=False,
        signature=court.sign_verdict(run_key, "M", claim_id, stance, quote),
        round=0, action="cache",
    )


async def run_pipeline(run: Run):
    try:
        topic = run.topic
        cache_enabled = os.environ.get("VERITAS_NO_CACHE") != "1"
        cached_sources = memory.get_evidence(topic) if cache_enabled else None

        # --- 0. INTAKE — memory priors ---------------------------------------
        run.emit("stage", {"stage": "intake", "status": "started"})
        run.priors = memory.topic_priors(topic)
        if run.priors:
            run.emit("priors", {"priors": run.priors})
            run.log("intake", f"memory recall: {len(run.priors)} prior finding(s) "
                    f"related to this topic")
        run.emit("stage", {"stage": "intake", "status": "done"})

        # --- 1. HYPOTHESES (Murli) -------------------------------------------
        run.emit("stage", {"stage": "hypothesize", "status": "started"})
        hypotheses, queries = await murli.hypothesize(
            topic, log=lambda m: run.log("hypothesize", m))
        if not cached_sources:
            # self-challenge issues counter-evidence SEARCHES — only useful
            # when we're actually searching (skipped on evidence cache hits)
            await murli.self_challenge(hypotheses, log=lambda m: run.log("hypothesize", m))
        run.emit("hypotheses", {"hypotheses": [h.model_dump() for h in hypotheses],
                                "queries": queries})
        run.emit("stage", {"stage": "hypothesize", "status": "done"})

        # --- 2. EVIDENCE REQUISITION (Serper → Tavily extract) ---------------
        run.emit("stage", {"stage": "research", "status": "started"})
        if cached_sources:
            sources = _rehydrate_sources(cached_sources)
            run.log("research", f"evidence cache hit — reusing {len(sources)} "
                    f"extracted sources (skipping Serper/Tavily)")
            run.emit("sources", {"sources": [s.model_dump() for s in sources],
                                 "cached": True})
        else:
            sources = await murli.requisition_evidence(
                hypotheses, queries, log=lambda m: run.log("research", m))
            if not sources:
                raise RuntimeError("No evidence gathered — search APIs unreachable.")
            run.emit("sources", {"sources": [s.model_dump() for s in sources]})
        run.emit("stage", {"stage": "research", "status": "done"})

        # --- 3. CLAIM EXTRACTION (anchored to chunks) -------------------------
        run.emit("stage", {"stage": "extract", "status": "started"})
        claims = await court.extract_claims(
            sources, hypotheses, topic, log=lambda m: run.log("extract", m))
        run.emit("claims", {"claims": [c.model_dump() for c in claims]})
        run.emit("stage", {"stage": "extract", "status": "done"})

        # --- 3b. CACHE CHECK — freshly-verified claims skip the panel ---------
        new_claims, cached_claims = [], []
        for c in claims:
            prior = memory.lookup_claim(c.text) if cache_enabled else None
            if prior and prior["exact"] and prior["fresh"]:
                c.verdicts = [_cached_verdict(prior, run.run_key, c.id)]
                c.confidence = prior["confidence"]
                c.status = prior["status"]
                cached_claims.append(c)
            else:
                new_claims.append(c)
        if cached_claims:
            run.emit("cache", {"cached": [
                {"claim_id": c.id, "text": c.text, "confidence": c.confidence,
                 "status": c.status} for c in cached_claims]})
            run.log("verify", f"{len(cached_claims)} claim(s) reused from memory "
                    f"(verified <24h ago) — {len(new_claims)} sent to the panel")

        # --- 4. ADVERSARIAL VERIFICATION (span-gated, signed) -----------------
        run.emit("stage", {"stage": "verify", "status": "started"})
        by_claim = {c.id: list(c.verdicts) for c in cached_claims}
        failures = 0
        fast_path = len(cached_claims) >= 0.5 * len(claims) and new_claims
        if new_claims:
            if fast_path:
                # memory already settled most of this topic — one quick pass
                # on the new claims instead of the full panel + debate
                by_claim_new, failures = await court.quick_verify(
                    new_claims, sources, run.run_key,
                    log=lambda m: run.log("verify", m))
                run.log("verify", f"fast path: {len(cached_claims)}/{len(claims)} "
                        f"claims from memory → quick verification of {len(new_claims)} new")
            else:
                by_claim_new, failures = await court.verifier_panel(
                    new_claims, sources, run.run_key,
                    log=lambda m: run.log("verify", m))
            by_claim.update(by_claim_new)
        for c in new_claims:
            c.verdicts = by_claim.get(c.id, [])
            for v in c.verdicts:
                run.emit("verdict", {
                    "claim_id": c.id, "verifier": v.verifier, "stance": v.stance,
                    "reasoning": v.reasoning, "quote": v.quote,
                    "chunk_id": v.chunk_id, "span_valid": v.span_valid,
                })
        run.emit("stage", {"stage": "verify", "status": "done",
                           "verifier_failures": failures})

        # --- 4b. MULTI-TURN DEBATE (deliberation + Judge) ----------------------
        run.emit("stage", {"stage": "deliberate", "status": "started"})
        rounds_used = 1
        if new_claims and not fast_path:
            by_claim_new = {cid: vs for cid, vs in by_claim.items()
                            if cid not in {c.id for c in cached_claims}}
            by_claim_new, transcript, rounds_used = await court.debate(
                by_claim_new, new_claims, sources, run.run_key,
                log=lambda m: run.log("deliberate", m))
            by_claim.update(by_claim_new)
            for c in new_claims:
                c.verdicts = by_claim.get(c.id, [])
            run.emit("debate", {"transcript": transcript, "rounds": rounds_used})
        run.emit("stage", {"stage": "deliberate", "status": "done",
                           "rounds": rounds_used})

        # --- 5. HALLUCINATION SWEEP (typed; fresh claims only) ------------------
        run.emit("stage", {"stage": "hallucinations", "status": "started"})
        hallu = {}
        if new_claims and not fast_path:
            hallu = await court.detect_hallucinations(
                new_claims, sources, log=lambda m: run.log("hallucinations", m))
        for c in claims:
            c.hallucinations = hallu.get(c.id, [])
            for f in c.hallucinations:
                run.emit("hallucination", {"claim_id": c.id, **f})
        run.emit("stage", {"stage": "hallucinations", "status": "done"})

        # --- 6. CONTRADICTION SWEEP --------------------------------------------
        run.emit("stage", {"stage": "contradictions", "status": "started"})
        contradictions = []
        if not fast_path:
            contradictions = await _contradictions(claims, by_claim, sources, run)
        for cd in contradictions:
            run.emit("contradiction", cd.model_dump())
        run.emit("stage", {"stage": "contradictions", "status": "done"})

        # --- 7. TRUST SCORING + MERKLE ANCHORING (deterministic) ---------------
        sources_by_id = {s.id: s for s in sources}
        flagged = {cd.claim_id for cd in contradictions}
        leaves, leaf_index = _merkle_leaves(sources)
        root = merkle_root(leaves)
        for c in claims:
            cited_chunks = set(c.chunk_ids)
            for v in c.verdicts:
                if v.span_valid and v.chunk_id:
                    cited_chunks.add(v.chunk_id)
            c.chunk_ids = sorted(cited_chunks)
            src_ids = {
                sid for ch in c.chunk_ids
                if (sid := sources_by_id_chunk(sources, ch))
            }
            c.source_ids = sorted(src_ids) or c.source_ids
            c.merkle_proofs = {
                ch: merkle_proof(leaves, leaf_index[ch])
                for ch in c.chunk_ids if ch in leaf_index
            }
            if c in cached_claims:
                continue   # confidence/status already set from memory
            dates = [
                sources_by_id[sid].published_at
                for sid in c.source_ids
                if sid in sources_by_id and sources_by_id[sid].published_at
            ]
            c.confidence, c.status = scoring.score_claim(
                c.text, c.verdicts, c.chunk_ids, c.source_ids, sources_by_id,
                c.id in flagged, c.hallucinations,
                recency=authority.recency_score(dates),
            )
            run.emit("score", {"claim_id": c.id, "confidence": c.confidence,
                               "status": c.status})

        # --- 8. SYNTHESIS -------------------------------------------------------
        run.emit("stage", {"stage": "report", "status": "started"})
        summary = await _synthesize(topic, claims, contradictions, sources, run)
        report = Report(
            topic=topic, summary=summary,
            trust_score=scoring.trust_score(claims),
            hypotheses=hypotheses, claims=claims, sources=sources,
            contradictions=contradictions,
            transcript=court.build_transcript(by_claim, {c.id: c for c in claims}),
            priors=run.priors,
            memory_stats={"cached": len(cached_claims), "new": len(new_claims),
                          "rounds": rounds_used, "priors": len(run.priors)},
            merkle_root=root, run_key=run.run_key, verified=False,
        )
        run.report = report
        run.emit("report", report.model_dump())
        run.emit("stage", {"stage": "report", "status": "done"})
        run.emit("done", {
            "run_id": run.id,
            "elapsed_s": round(time.time() - run.started, 1),
            "claims": len(claims), "sources": len(sources),
            "contradictions": len(contradictions),
            "cached": len(cached_claims), "debate_rounds": rounds_used,
            "merkle_root": root[:16] + "…",
        })

        # --- 9. LEARNING — record claims, domains, content hashes ---------------
        _learn(claims, cached_claims, sources, topic, run)
    except Exception as e:
        run.error = str(e)
        run.emit("error", {"message": str(e)})
    finally:
        run.done = True


# ---------------------------------------------------------------------------
# learning (Phase 3 memory writes)
# ---------------------------------------------------------------------------

def _rehydrate_sources(dicts: list) -> list:
    """Rebuild Source objects (with _chunks) from cached dicts."""
    out = []
    for d in dicts:
        chunks = [Chunk(id=ch["chunk_id"], source_id=d["id"], text=ch.get("text", ""),
                        hash=ch.get("hash", ""))
                  for ch in d.get("chunks", []) if ch.get("text")]
        s = Source(**{k: v for k, v in d.items() if k != "chunks"})
        s.chunks = [ChunkRef(**ch) for ch in d.get("chunks", [])]
        s.__dict__["_chunks"] = chunks
        out.append(s)
    return out


def _learn(claims, cached_claims, sources, topic, run):
    try:
        cached_ids = {c.id for c in cached_claims}
        for c in claims:
            if c.id in cached_ids:
                continue   # already in memory; don't double-count this run
            last = c.verdicts[-1].stance if c.verdicts else "insufficient"
            memory.record_claim(c.text, last, c.status, c.confidence, topic)
        memory.record_evidence(topic, sources)
        for s in sources:
            domain = publisher_of(s.url)
            if memory.get_domain_tier(domain) is None:
                memory.record_domain(domain, s.authority_tier, "static")
            else:
                memory.bump_domain(domain)
            for ch in s.__dict__.get("_chunks", []):
                if ch.hash:
                    memory.record_hash(ch.hash, ch.id, s.url)
        run.log("report", f"memory updated: {memory.stats()}")
    except Exception as e:
        run.log("report", f"memory write degraded: {e}")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _merkle_leaves(sources):
    """Ordered leaf list (chunk hashes in source/chunk order) + id→index map."""
    leaves, index = [], {}
    i = 0
    for s in sources:
        for ch in s.__dict__.get("_chunks", []):
            leaves.append(ch.hash)
            index[ch.id] = i
            i += 1
    return leaves, index


def sources_by_id_chunk(sources, chunk_id: str) -> int | None:
    for s in sources:
        for ch in s.__dict__.get("_chunks", []):
            if ch.id == chunk_id:
                return s.id
    return None


async def _contradictions(claims, by_claim, sources, run):
    """Contradiction detector — verifier disagreements + source refutations."""
    from agents import contradiction_detector # reused from v1 (still valid)
    return await contradiction_detector(
        claims, by_claim, sources, log=lambda m: run.log("contradictions", m))


async def _synthesize(topic, claims, contradictions, sources, run):
    from agents import writer
    by_claim = {c.id: c.verdicts for c in claims}
    written = await writer(topic, claims, by_claim, contradictions, sources,
                           log=lambda m: run.log("report", m))
    notes = {
        n.get("claim_id"): n.get("verification_note", "")
        for n in written.get("claim_report", []) if isinstance(n, dict)
    }
    for c in claims:
        c.verification_note = notes.get(c.id, "")
    return written.get("summary", "")
