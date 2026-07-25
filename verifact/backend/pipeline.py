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
import argument
import compliance
import court
import graph
import llm
import memory
import metrics
import murli
import scoring
import semantic
import sentry_integration
import workflow
from evidence import Chunk, merkle_proof, merkle_root, publisher_of
from models import ChunkRef, Report, Source, Verdict

STAGES = ["intake", "hypothesize", "research", "extract", "verify",
          "deliberate", "hallucinations", "contradictions", "report"]


class Run:
    def __init__(self, run_id: str, topic: str, explain: str | None = None):
        self.id = run_id
        self.topic = topic
        self.run_key = secrets.token_hex(16)   # per-run HMAC key (published w/ report)
        self.history: list[tuple[str, dict]] = []
        self.report: Report | None = None
        self.error: str | None = None
        self.done = False
        self.started = time.time()
        self.priors: list[dict] = []
        self.compliance_trace = compliance.create_compliance_trace(run_id, explain)

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
        semantic_enabled = os.environ.get("VERITAS_SEMANTIC", "0") == "1"
        cached_sources = memory.get_evidence(topic) if cache_enabled else None

        # Phase 8: workflow journaling + metrics + Sentry context
        workflow.start_run(run.id, topic)
        metrics.increment_active_runs()
        sentry_integration.set_run_context(run.id, topic)

        # --- 0. INTAKE — memory priors ---------------------------------------
        run.emit("stage", {"stage": "intake", "status": "started"})
        run.priors = memory.topic_priors(topic)
        if run.priors:
            run.emit("priors", {"priors": run.priors})
            run.log("intake", f"memory recall: {len(run.priors)} prior finding(s) "
                    f"related to this topic")
        run.emit("stage", {"stage": "intake", "status": "done"})
        workflow.checkpoint(run.id, "intake", {"priors": len(run.priors)})

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
        workflow.checkpoint(run.id, "hypothesize", {"hypotheses": len(hypotheses)})

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
        workflow.checkpoint(run.id, "research", {"sources": len(sources)})

        # --- 3. CLAIM EXTRACTION (anchored to chunks) -------------------------
        run.emit("stage", {"stage": "extract", "status": "started"})
        claims = await court.extract_claims(
            sources, hypotheses, topic, log=lambda m: run.log("extract", m))
        # Phase 6 — semantic dedup: link each claim to its nearest past-run twin
        if semantic_enabled and semantic.available():
            dedup_hits = 0
            for c in claims:
                similar = semantic.find_similar_claims(c.text, n=1)
                if similar:
                    c.semantic_prior = similar[0]
                    dedup_hits += 1
            if dedup_hits:
                run.log("extract", f"semantic dedup: {dedup_hits}/{len(claims)} "
                        f"claim(s) match a claim verified in a past run")
        run.emit("claims", {"claims": [c.model_dump() for c in claims]})
        run.emit("stage", {"stage": "extract", "status": "done"})
        workflow.checkpoint(run.id, "extract", {"claims": len(claims)})

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
                # Phase 8: compliance trace
                run.compliance_trace.record_verdict(v.verifier, {
                    "claim_id": c.id, "stance": v.stance, "reasoning": v.reasoning,
                    "quote": v.quote, "chunk_id": v.chunk_id, "span_valid": v.span_valid
                })
        run.emit("stage", {"stage": "verify", "status": "done",
                           "verifier_failures": failures})
        workflow.checkpoint(run.id, "verify", {"verified": len(new_claims), "failures": failures})

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
            # Phase 8: compliance trace for deliberation
            for round_num in range(2, rounds_used + 1):
                round_transcript = [t for t in transcript if t.get("round") == round_num]
                run.compliance_trace.record_deliberation(round_num, round_transcript)
        run.emit("stage", {"stage": "deliberate", "status": "done",
                           "rounds": rounds_used})
        workflow.checkpoint(run.id, "deliberate", {"rounds": rounds_used})

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
                # Phase 8: metrics + compliance trace
                metrics.record_hallucination_flag(f.get("type", "unknown"), f.get("severity", "unknown"))
                run.compliance_trace.record_hallucination_check("hallucination_detector", [{
                    "claim_id": c.id, **f
                }])
        run.emit("stage", {"stage": "hallucinations", "status": "done"})
        workflow.checkpoint(run.id, "hallucinations", {"flags": sum(len(v) for v in hallu.values())})

        # --- 6. CONTRADICTION SWEEP --------------------------------------------
        run.emit("stage", {"stage": "contradictions", "status": "started"})
        contradictions = []
        if not fast_path:
            contradictions = await _contradictions(claims, by_claim, sources, run)
        for cd in contradictions:
            run.emit("contradiction", cd.model_dump())
        run.emit("stage", {"stage": "contradictions", "status": "done"})
        workflow.checkpoint(run.id, "contradictions", {"contradictions": len(contradictions)})

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
        workflow.checkpoint(run.id, "scoring", {"scored": len(claims)})

        # --- 7b. ARGUMENT TREE + TRUST RADAR (Phase 5) --------------------------
        argument_tree = argument.build_argument_tree(claims, hypotheses, sources_by_id)
        trust_radar = scoring.radar(claims, sources_by_id)
        run.emit("argument", {"tree": argument_tree, "radar": trust_radar})
        if argument_tree.get("weakest_link"):
            wl = argument_tree["weakest_link"]
            run.log("report", f"weakest link: {wl['note']}")

        # --- 7c. SEMANTIC LAYER (Phase 6) — counter-evidence the search missed --
        # Optional: the embedding model needs ~300MB; on constrained boxes the
        # live API may not have room mid-run. Enable with VERITAS_SEMANTIC=1.
        semantic_stats = {"counter_hits": 0, "claims_checked": 0}
        if semantic_enabled and semantic.available():
            run.emit("stage", {"stage": "semantic", "status": "started"})
            hits = 0
            for c in claims:
                counter = semantic.counter_evidence(c.text)
                if counter:
                    c.counter_evidence = counter
                    hits += 1
                    run.emit("counter_evidence", {"claim_id": c.id, "counter": counter})
            semantic_stats = {"counter_hits": hits, "claims_checked": len(claims)}
            if hits:
                run.log("report", f"semantic layer surfaced opposing evidence for "
                        f"{hits}/{len(claims)} claim(s) that keyword search missed")
            run.emit("stage", {"stage": "semantic", "status": "done"})

        # --- 7d. PROVENANCE GRAPH (Phase 7) — circular-citation detection ------
        G = graph.build_provenance_graph(claims, sources_by_id)
        graph_stats = graph.graph_stats(G)
        run.emit("graph", {"stats": graph_stats})
        if graph_stats["circular_citations"] > 0:
            run.log("report", f"⚠ circular citation detected: "
                    f"{graph_stats['circular_citations']} cycle(s) in the provenance graph")

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
            argument_tree=argument_tree, trust_radar=trust_radar,
            semantic_stats=semantic_stats, graph_stats=graph_stats,
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
        workflow.checkpoint(run.id, "synthesis", {"trust_score": report.trust_score})

        # --- 9. LEARNING — record claims, domains, content hashes ---------------
        _learn(claims, cached_claims, sources, topic, run, semantic_enabled)
        workflow.checkpoint(run.id, "learning", {})

        # Phase 8: workflow completion + metrics
        duration = time.time() - run.started
        workflow.finish_run(run.id, status="completed")
        metrics.record_run_completed("completed", duration)
        metrics.decrement_active_runs()

    except Exception as e:
        run.error = str(e)
        run.emit("error", {"message": str(e)})
        # Phase 8: workflow failure + metrics + Sentry
        duration = time.time() - run.started
        workflow.finish_run(run.id, status="failed", error=str(e))
        metrics.record_run_completed("failed", duration)
        metrics.decrement_active_runs()
        sentry_integration.capture_error(e, {
            "run_id": run.id,
            "topic": run.topic,
            "duration": duration
        })
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


def _learn(claims, cached_claims, sources, topic, run, semantic_enabled=False):
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

        # semantic index (Phase 6) — grow the evidence + claim corpora
        if semantic_enabled and semantic.available():
            chunks = []
            for s in sources:
                for ch in s.__dict__.get("_chunks", []):
                    if ch.text:
                        chunks.append({
                            "id": ch.id, "text": ch.text, "run_id": run.id,
                            "source_id": s.id, "url": s.url,
                            "publisher": s.publisher,
                            "authority_tier": s.authority_tier,
                        })
            n = semantic.index_evidence(chunks)
            for c in claims:
                semantic.record_claim(c.id, c.text, run.id, c.status)
            run.log("report", f"semantic index: +{n} chunks, "
                    f"{semantic.stats()}")
            semantic.unload()   # free ~300MB so the API baseline stays small
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
