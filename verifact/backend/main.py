"""VeritasAI API — the Research Court.

API-only backend. The frontend is served separately: nginx in production
(deploy/nginx.conf), serve_frontend.py in development. This process never
serves static files.

POST /api/research                 start a run → {run_id}
GET  /api/research/{id}/stream     SSE live event stream
GET  /api/research/{id}            final report JSON
GET  /api/reports/{id}/verify      cryptographic re-attestation (FEC L2-L4)
GET  /api/runs                     past investigations
GET  /api/health                   liveness + config
"""
import asyncio
import json
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import journal
import llm
import memory
import tavily_client
from pipeline import Run, run_pipeline

app = FastAPI(title="VeritasAI", version="2.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

RUNS: dict[str, Run] = {}


@app.on_event("startup")
def _startup():
    journal.init()
    memory.init()


class ResearchRequest(BaseModel):
    topic: str


@app.post("/api/research")
async def start_research(req: ResearchRequest):
    topic = req.topic.strip()
    if not topic:
        raise HTTPException(400, "topic is required")
    run_id = uuid.uuid4().hex[:12]
    run = Run(run_id, topic)
    RUNS[run_id] = run
    asyncio.create_task(_run_and_persist(run))
    return {"run_id": run_id}


async def _run_and_persist(run: Run):
    await run_pipeline(run)
    try:
        journal.save_run(run)
    except Exception:
        pass


@app.get("/api/research/{run_id}/stream")
async def stream(run_id: str):
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(404, "run not found")

    async def gen():
        idx = 0
        while True:
            while idx < len(run.history):
                event, data = run.history[idx]
                yield f"event: {event}\ndata: {json.dumps(data)}\n\n"
                idx += 1
            if run.done:
                yield "event: end\ndata: {}\n\n"
                return
            await asyncio.sleep(0.3)

    return StreamingResponse(
        gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/research/{run_id}")
async def get_run(run_id: str):
    run = RUNS.get(run_id)
    if run:
        return {
            "run_id": run.id, "topic": run.topic, "done": run.done,
            "error": run.error,
            "report": run.report.model_dump() if run.report else None,
        }
    stored = journal.load_run(run_id)
    if stored:
        return stored
    raise HTTPException(404, "run not found")


@app.get("/api/reports/{run_id}/verify")
async def verify_report(run_id: str):
    """Cryptographic re-attestation: recompute Merkle root + check signatures."""
    run = RUNS.get(run_id)
    report = run.report.model_dump() if (run and run.report) else None
    if report is None:
        stored = journal.load_run(run_id)
        report = (stored or {}).get("report")
    if report is None:
        raise HTTPException(404, "report not found")
    result = journal.verify_report(report)
    result["run_id"] = run_id
    result["topic"] = report.get("topic", "")
    return result


@app.get("/api/runs")
async def list_runs():
    return {"runs": journal.list_runs()}


@app.get("/api/calibration")
async def calibration():
    """Expected Calibration Error over labeled eval runs — the system
    publishing its own calibration error (Phase 2)."""
    return journal.calibration()


@app.get("/api/memory")
async def memory_stats():
    """Cross-run memory state (Phase 3): claims learned, domains classified,
    content hashes indexed, recurring quotes (circular-citation seed)."""
    return memory.stats()


class EngagementEvent(BaseModel):
    run_id: str
    topic: str = ""
    dwell_ms: int = 0
    inspector_opens: int = 0
    tree_views: int = 0


@app.post("/api/engagement")
async def record_engagement(ev: EngagementEvent):
    """Report engagement analytics (Phase 5) — client posts dwell time etc."""
    try:
        journal.record_engagement(ev.run_id, ev.topic, ev.dwell_ms,
                                  ev.inspector_opens, ev.tree_views)
    except Exception:
        pass
    return {"ok": True}


@app.get("/api/analytics")
async def analytics():
    """Aggregate report engagement — do users read the debate? (Phase 5 KPI)"""
    return journal.engagement_stats()


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "llm_model": llm.current_model(),
        "llm_fallback": llm.FALLBACK_MODEL,
        "tavily_configured": bool(tavily_client.TAVILY_API_KEY),
    }
