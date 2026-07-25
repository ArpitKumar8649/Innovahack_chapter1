"""VeriFact API — multi-agent research & fact-verification system.

POST /api/research              start a run → {run_id}
GET  /api/research/{id}/stream  SSE live event stream
GET  /api/research/{id}         final report JSON
GET  /api/runs                  past runs (landing page history)
GET  /api/health                liveness + config sanity
GET  /                          frontend (static)
"""
import asyncio
import json
import os
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import llm
import tavily_client
from pipeline import Run, run_pipeline

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE.parent / "data" / "runs"
DATA_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND_DIR = HERE.parent / "frontend"

app = FastAPI(title="VeriFact", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RUNS: dict[str, Run] = {}


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
    # persist finished runs so they survive restarts
    try:
        payload = {
            "run_id": run.id,
            "topic": run.topic,
            "started": run.started,
            "error": run.error,
            "report": run.report.model_dump() if run.report else None,
        }
        (DATA_DIR / f"{run.id}.json").write_text(json.dumps(payload, indent=1))
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
            # replay any new events
            while idx < len(run.history):
                event, data = run.history[idx]
                yield f"event: {event}\ndata: {json.dumps(data)}\n\n"
                idx += 1
            if run.done:
                yield "event: end\ndata: {}\n\n"
                return
            await asyncio.sleep(0.3)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/research/{run_id}")
async def get_run(run_id: str):
    # live run first, then persisted
    run = RUNS.get(run_id)
    if run:
        return {
            "run_id": run.id,
            "topic": run.topic,
            "done": run.done,
            "error": run.error,
            "report": run.report.model_dump() if run.report else None,
        }
    path = DATA_DIR / f"{run_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    raise HTTPException(404, "run not found")


@app.get("/api/runs")
async def list_runs():
    runs = []
    for path in sorted(DATA_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime,
                       reverse=True)[:20]:
        try:
            d = json.loads(path.read_text())
            runs.append({
                "run_id": d.get("run_id"),
                "topic": d.get("topic"),
                "trust_score": (d.get("report") or {}).get("trust_score", 0),
                "error": d.get("error"),
            })
        except Exception:
            continue
    return {"runs": runs}


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "llm_base_url": llm.BASE_URL if hasattr(llm, "BASE_URL") else llm.RESPONSES_URL,
        "model": llm.MODEL,
        "tavily_configured": bool(tavily_client.TAVILY_API_KEY),
    }


# frontend last so /api routes win
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="app")
