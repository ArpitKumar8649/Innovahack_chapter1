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

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import api_v1
import auth
import feedback
import journal
import llm
import memory
import metrics
import redteam
import referee
import semantic
import sentry_integration
import tavily_client
import tenants
import workflow
from fastapi.responses import Response
from pipeline import Run, run_pipeline

app = FastAPI(title="VeritasAI", version="2.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

RUNS: dict[str, Run] = {}


@app.on_event("startup")
def _startup():
    auth.init()
    journal.init()
    memory.init()
    referee.init()
    api_v1.init()
    workflow.init()
    sentry_integration.init()
    tenants.init()
    feedback.init()


# user authentication (register / login / me)
app.include_router(auth.router)


class ResearchRequest(BaseModel):
    topic: str
    explain: str | None = None  # Phase 8: compliance mode (?explain=full)
    tenant_id: str | None = None  # Phase 9: multi-tenant support


@app.post("/api/research")
async def start_research(req: ResearchRequest, request: Request):
    topic = req.topic.strip()
    if not topic:
        raise HTTPException(400, "topic is required")

    # Phase 9: tenant rate limiting
    if req.tenant_id:
        allowed, msg = tenants.check_rate_limit(req.tenant_id)
        if not allowed:
            raise HTTPException(429, msg)

    # tag the run with the authenticated user (if any)
    user = auth.get_current_user(request)
    user_id = user["id"] if user else None

    run_id = uuid.uuid4().hex[:12]
    run = Run(run_id, topic, explain=req.explain, tenant_id=req.tenant_id)
    run.user_id = user_id
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
async def list_runs(request: Request):
    user = auth.get_current_user(request)
    user_id = user["id"] if user else None
    return {"runs": journal.list_runs(user_id=user_id)}


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


@app.get("/api/semantic")
async def semantic_stats():
    """Semantic layer state (Phase 6): indexed evidence chunks + claims,
    the model in use, and availability."""
    return semantic.stats()


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "llm_model": llm.current_model(),
        "llm_fallback": llm.FALLBACK_MODEL,
        "tavily_configured": bool(tavily_client.TAVILY_API_KEY),
        "semantic_available": semantic.available(),
    }


# ---------------------------------------------------------------------------
# Phase 7 — Expert Referee endpoints
# ---------------------------------------------------------------------------

class FlagRequest(BaseModel):
    run_id: str
    claim_id: int
    expert_name: str
    reason: str


@app.post("/api/flag")
async def flag_verdict(req: FlagRequest):
    """An expert flags a verdict for review."""
    try:
        flag_id = referee.flag_verdict(
            req.run_id, req.claim_id, req.expert_name, req.reason
        )
        return {"ok": True, "flag_id": flag_id}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get("/api/flags")
async def list_flags(run_id: str = None, limit: int = 50):
    """List expert flags, optionally filtered by run_id."""
    return {"flags": referee.get_flags(run_id, limit)}


@app.post("/api/flags/{flag_id}/convert")
async def convert_flag(flag_id: int):
    """Convert a flag into a harness test case."""
    try:
        test_case = referee.convert_to_test_case(flag_id)
        return {"ok": True, "test_case": test_case}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get("/api/referee/stats")
async def referee_stats():
    """Expert referee system stats."""
    return referee.stats()


# ---------------------------------------------------------------------------
# Phase 7 — Public API v1 (external access with API key auth)
# ---------------------------------------------------------------------------

app.include_router(api_v1.router)


# ---------------------------------------------------------------------------
# Phase 8 — Observability & Compliance endpoints
# ---------------------------------------------------------------------------

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint (Phase 8)."""
    return Response(
        content=metrics.get_metrics(),
        media_type=metrics.get_content_type()
    )


@app.get("/api/reports/{run_id}/compliance")
async def get_compliance_trace(run_id: str):
    """Get the full compliance trace for a run (Phase 8)."""
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    trace = getattr(run, "compliance_trace", None)
    if trace is None or not trace.enabled:
        raise HTTPException(400, "compliance mode not enabled for this run (use explain=full)")
    return trace.to_dict()


@app.get("/api/workflows/{run_id}/replay")
async def replay_workflow(run_id: str):
    """Replay a workflow from its journal (Phase 8)."""
    try:
        return workflow.replay_run(run_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.get("/api/workflows")
async def list_workflows(limit: int = 50):
    """List recent workflow runs (Phase 8)."""
    return {"workflows": workflow.list_runs(limit)}


# ---------------------------------------------------------------------------
# Phase 9 — Enterprise & Adversarial Maturity endpoints
# ---------------------------------------------------------------------------

@app.get("/api/reports/{run_id}/redteam")
async def get_redteam_findings(run_id: str):
    """Get red-team findings for a run (Phase 9)."""
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return {"findings": run.red_team_findings}


@app.post("/api/tenants")
async def create_tenant(name: str, plan: str = "free"):
    """Create a new tenant (Phase 9)."""
    try:
        return tenants.create_tenant(name, plan)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/tenants")
async def list_tenants():
    """List all tenants (Phase 9)."""
    return {"tenants": tenants.list_tenants()}


@app.get("/api/tenants/stats")
async def tenant_stats():
    """Tenant system stats (Phase 9)."""
    return tenants.stats()


@app.get("/api/tenants/{tenant_id}")
async def get_tenant(tenant_id: str):
    """Get a tenant by ID (Phase 9)."""
    tenant = tenants.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(404, "tenant not found")
    return tenant


@app.get("/api/tenants/{tenant_id}/usage")
async def get_tenant_usage(tenant_id: str, days: int = 30):
    """Get usage history for a tenant (Phase 9)."""
    return {"usage": tenants.get_usage(tenant_id, days)}


@app.get("/api/feedback/pending")
async def get_pending_feedback(limit: int = 50):
    """Get pending feedback signals (Phase 9)."""
    return {"feedback": feedback.get_pending_feedback(limit)}


@app.get("/api/feedback/policy")
async def get_policy_recommendations():
    """Generate policy recommendations from feedback (Phase 9)."""
    return feedback.generate_policy_from_feedback()


@app.get("/api/feedback/updates")
async def get_policy_updates(limit: int = 20):
    """Get recent policy updates (Phase 9)."""
    return {"updates": feedback.get_policy_updates(limit)}


@app.get("/api/feedback/stats")
async def feedback_stats():
    """Feedback loop stats (Phase 9)."""
    return feedback.stats()
