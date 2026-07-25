"""Research Court orchestrator — the 10-stage execution flow.

Intake → Hypotheses (Murli) → Self-challenge → Evidence requisition
(Serper→Tavily, full-text, hashed) → Claim extraction (anchored)
→ Adversarial verification (span-gated, signed) → Hallucination sweep
→ Contradiction sweep → Trust scoring → Synthesis + Merkle anchoring.

Every stage emits SSE events; the finished run is journaled to SQLite
with its Merkle root and signed verdicts (FEC layers 2-3).
"""
import secrets
import time

import court
import murli
import scoring
from evidence import merkle_proof, merkle_root
from models import Report

STAGES = ["hypothesize", "research", "extract", "verify",
          "hallucinations", "contradictions", "report"]


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

    def emit(self, event: str, data: dict):
        self.history.append((event, data))

    def log(self, stage: str, msg: str):
        self.emit("log", {"stage": stage, "message": msg})


async def run_pipeline(run: Run):
    try:
        topic = run.topic

        # --- 1. HYPOTHESES (Murli) -------------------------------------------
        run.emit("stage", {"stage": "hypothesize", "status": "started"})
        hypotheses, queries = await murli.hypothesize(
            topic, log=lambda m: run.log("hypothesize", m))
        await murli.self_challenge(hypotheses, log=lambda m: run.log("hypothesize", m))
        run.emit("hypotheses", {"hypotheses": [h.model_dump() for h in hypotheses],
                                "queries": queries})
        run.emit("stage", {"stage": "hypothesize", "status": "done"})

        # --- 2. EVIDENCE REQUISITION (Serper → Tavily extract) ---------------
        run.emit("stage", {"stage": "research", "status": "started"})
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

        # --- 4. ADVERSARIAL VERIFICATION (span-gated, signed) -----------------
        run.emit("stage", {"stage": "verify", "status": "started"})
        by_claim, failures = await court.verifier_panel(
            claims, sources, run.run_key, log=lambda m: run.log("verify", m))
        for c in claims:
            c.verdicts = by_claim.get(c.id, [])
            for v in c.verdicts:
                run.emit("verdict", {
                    "claim_id": c.id, "verifier": v.verifier, "stance": v.stance,
                    "reasoning": v.reasoning, "quote": v.quote,
                    "chunk_id": v.chunk_id, "span_valid": v.span_valid,
                })
        run.emit("stage", {"stage": "verify", "status": "done",
                           "verifier_failures": failures})

        # --- 5. HALLUCINATION SWEEP (typed) ------------------------------------
        run.emit("stage", {"stage": "hallucinations", "status": "started"})
        hallu = await court.detect_hallucinations(
            claims, sources, log=lambda m: run.log("hallucinations", m))
        for c in claims:
            c.hallucinations = hallu.get(c.id, [])
            for f in c.hallucinations:
                run.emit("hallucination", {"claim_id": c.id, **f})
        run.emit("stage", {"stage": "hallucinations", "status": "done"})

        # --- 6. CONTRADICTION SWEEP --------------------------------------------
        run.emit("stage", {"stage": "contradictions", "status": "started"})
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
            c.confidence, c.status = scoring.score_claim(
                c.text, c.verdicts, c.chunk_ids, c.source_ids, sources_by_id,
                c.id in flagged, c.hallucinations,
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
            "merkle_root": root[:16] + "…",
        })
    except Exception as e:
        run.error = str(e)
        run.emit("error", {"message": str(e)})
    finally:
        run.done = True


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
