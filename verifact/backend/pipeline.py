"""Pipeline orchestrator — runs the 6-stage agent pipeline, emits SSE events.

Stages: plan → research → extract → verify (3 parallel) → contradictions → report
Every stage transition and notable action is recorded in run.history so SSE
subscribers can replay from the start (no missed events) and tail live.
"""
import asyncio
import time

import agents
import scoring
from models import Report

STAGES = ["plan", "research", "extract", "verify", "contradictions", "report"]


class Run:
    def __init__(self, run_id: str, topic: str):
        self.id = run_id
        self.topic = topic
        self.history: list[tuple[str, dict]] = []  # (event, data) — replay buffer
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

        # --- 1. PLAN -------------------------------------------------------
        run.emit("stage", {"stage": "plan", "status": "started"})
        plan = await agents.planner(topic, log=lambda m: run.log("plan", m))
        run.emit("plan", plan)
        run.emit("stage", {"stage": "plan", "status": "done"})

        # --- 2. RESEARCH ---------------------------------------------------
        run.emit("stage", {"stage": "research", "status": "started"})
        sources = await agents.researcher(
            plan["search_queries"], log=lambda m: run.log("research", m)
        )
        if not sources:
            raise RuntimeError(
                "No sources found — the search API may be unreachable."
            )
        run.emit("sources", {"sources": [s.model_dump() for s in sources]})
        run.emit("stage", {"stage": "research", "status": "done"})

        # --- 3. EXTRACT (atomic claims) -------------------------------------
        run.emit("stage", {"stage": "extract", "status": "started"})
        claims = await agents.extractor(
            sources, topic, log=lambda m: run.log("extract", m)
        )
        run.emit("claims", {"claims": [c.model_dump() for c in claims]})
        run.emit("stage", {"stage": "extract", "status": "done"})

        # --- 4. VERIFY (3 adversarial verifiers in parallel) ----------------
        run.emit("stage", {"stage": "verify", "status": "started"})
        by_claim, failed = await agents.verifier_panel(
            claims, sources, log=lambda m: run.log("verify", m)
        )
        for c in claims:
            c.verdicts = by_claim.get(c.id, [])
            for v in c.verdicts:
                run.emit("verdict", {
                    "claim_id": c.id, "verifier": v.verifier,
                    "stance": v.stance, "reasoning": v.reasoning,
                })
        run.emit("stage", {"stage": "verify", "status": "done",
                           "verifier_failures": failed})

        # --- 5. CONTRADICTIONS ----------------------------------------------
        run.emit("stage", {"stage": "contradictions", "status": "started"})
        contradictions = await agents.contradiction_detector(
            claims, by_claim, sources, log=lambda m: run.log("contradictions", m)
        )
        for cd in contradictions:
            run.emit("contradiction", cd.model_dump())
        run.emit("stage", {"stage": "contradictions", "status": "done"})

        # --- deterministic confidence scoring (no LLM) ----------------------
        sources_by_id = {s.id: s for s in sources}
        flagged = {cd.claim_id for cd in contradictions}
        for c in claims:
            cited = set(c.source_ids)
            for v in c.verdicts:
                cited.update(v.source_ids)
            c.source_ids = sorted(cited)
            c.confidence, c.status = scoring.score_claim(
                c.text, c.verdicts, c.source_ids, sources_by_id, c.id in flagged
            )
            run.emit("score", {
                "claim_id": c.id, "confidence": c.confidence, "status": c.status,
            })

        # --- 6. REPORT -------------------------------------------------------
        run.emit("stage", {"stage": "report", "status": "started"})
        written = await agents.writer(
            topic, claims, by_claim, contradictions, sources,
            log=lambda m: run.log("report", m),
        )
        notes = {
            n.get("claim_id"): n.get("verification_note", "")
            for n in written.get("claim_report", [])
            if isinstance(n, dict)
        }
        for c in claims:
            c.verification_note = notes.get(c.id, "")

        report = Report(
            topic=topic,
            summary=written.get("summary", ""),
            trust_score=scoring.trust_score(claims),
            claims=claims,
            sources=sources,
            contradictions=contradictions,
        )
        run.report = report
        run.emit("report", report.model_dump())
        run.emit("stage", {"stage": "report", "status": "done"})
        run.emit("done", {
            "run_id": run.id,
            "elapsed_s": round(time.time() - run.started, 1),
            "claims": len(claims),
            "sources": len(sources),
            "contradictions": len(contradictions),
            "verifier_failures": failed,
        })
    except Exception as e:
        run.error = str(e)
        run.emit("error", {"message": str(e)})
    finally:
        run.done = True
