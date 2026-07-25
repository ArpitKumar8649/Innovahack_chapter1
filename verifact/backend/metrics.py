"""Prometheus metrics (Phase 8) — observability for the Research Court.

Exposes counters, histograms, and gauges at /metrics for Prometheus scraping.
Tracks:
- Agent calls (by agent, model, status)
- LLM latency (by model)
- Hallucination flags (by type, severity)
- Run duration (by status)
- Active runs (gauge)

Production: scrape with Prometheus, visualize in Grafana.
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Counters
AGENT_CALLS = Counter(
    "verifact_agent_calls_total",
    "Total agent calls",
    ["agent", "model", "status"]
)

HALLUCINATION_FLAGS = Counter(
    "verifact_hallucination_flags_total",
    "Total hallucination flags",
    ["type", "severity"]
)

RUNS_COMPLETED = Counter(
    "verifact_runs_completed_total",
    "Total runs completed",
    ["status"]
)

# Histograms
LLM_LATENCY = Histogram(
    "verifact_llm_latency_seconds",
    "LLM call latency",
    ["model"],
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120]
)

RUN_DURATION = Histogram(
    "verifact_run_duration_seconds",
    "Run duration",
    ["status"],
    buckets=[10, 30, 60, 120, 300, 600, 1200]
)

# Gauges
ACTIVE_RUNS = Gauge(
    "verifact_active_runs",
    "Number of currently active runs"
)


def record_agent_call(agent: str, model: str, status: str):
    """Record an agent call."""
    AGENT_CALLS.labels(agent=agent, model=model, status=status).inc()


def record_llm_latency(model: str, duration_s: float):
    """Record LLM call latency."""
    LLM_LATENCY.labels(model=model).observe(duration_s)


def record_hallucination_flag(htype: str, severity: str):
    """Record a hallucination flag."""
    HALLUCINATION_FLAGS.labels(type=htype, severity=severity).inc()


def record_run_completed(status: str, duration_s: float):
    """Record a completed run."""
    RUNS_COMPLETED.labels(status=status).inc()
    RUN_DURATION.labels(status=status).observe(duration_s)


def increment_active_runs():
    """Increment active runs gauge."""
    ACTIVE_RUNS.inc()


def decrement_active_runs():
    """Decrement active runs gauge."""
    ACTIVE_RUNS.dec()


def get_metrics() -> bytes:
    """Generate Prometheus metrics output."""
    return generate_latest()


def get_content_type() -> str:
    """Get the Prometheus content type."""
    return CONTENT_TYPE_LATEST
