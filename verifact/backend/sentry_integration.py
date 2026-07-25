"""Sentry error tracking (Phase 8) — error tracking with run context.

Captures exceptions with full run context (run_id, stage, agent, claim_id)
for debugging production issues.

Production: Sentry DSN configured via environment variable.
"""
import os
import sentry_sdk
from sentry_sdk import capture_exception, set_context, set_tag


def init():
    """Initialize Sentry if DSN is configured."""
    dsn = os.environ.get("SENTRY_DSN")
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
        )


def set_run_context(run_id: str, topic: str, stage: str = None):
    """Set run context for error tracking."""
    set_tag("run_id", run_id)
    set_tag("topic", topic)
    if stage:
        set_tag("stage", stage)


def set_agent_context(agent: str, claim_id: int = None):
    """Set agent context for error tracking."""
    set_tag("agent", agent)
    if claim_id:
        set_tag("claim_id", str(claim_id))


def capture_error(error: Exception, context: dict = None):
    """Capture an exception with optional context."""
    if context:
        set_context("error_context", context)
    capture_exception(error)
