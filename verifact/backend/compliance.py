"""Compliance mode (Phase 8) — full reasoning chains for regulated industries.

When compliance mode is enabled (?explain=full), every agent emits its full
reasoning chain in the report. This is the brief's "explain-everything" mode
for regulated industries (finance, healthcare, legal).

Compliance reports include:
- Full agent prompts and responses
- All intermediate reasoning steps
- Complete evidence chains
- Verifier deliberation transcripts
- Hallucination detector logic

Production: compliance reports pass mock audits; every decision is traceable.
"""
import json
import time
from typing import Any


class ComplianceTrace:
    """Captures full reasoning chains for compliance mode."""

    def __init__(self, run_id: str, enabled: bool = False):
        self.run_id = run_id
        self.enabled = enabled
        self.trace: list[dict] = []

    def record(self, agent: str, step: str, data: dict[str, Any]):
        """Record a reasoning step."""
        if not self.enabled:
            return
        self.trace.append({
            "agent": agent,
            "step": step,
            "data": data,
            "at": time.time()
        })

    def record_prompt(self, agent: str, prompt: str):
        """Record an agent prompt."""
        self.record(agent, "prompt", {"prompt": prompt})

    def record_response(self, agent: str, response: str):
        """Record an agent response."""
        self.record(agent, "response", {"response": response})

    def record_reasoning(self, agent: str, reasoning: str):
        """Record intermediate reasoning."""
        self.record(agent, "reasoning", {"reasoning": reasoning})

    def record_evidence(self, agent: str, evidence: list[dict]):
        """Record evidence considered."""
        self.record(agent, "evidence", {"evidence": evidence})

    def record_verdict(self, agent: str, verdict: dict):
        """Record a verifier verdict."""
        self.record(agent, "verdict", {"verdict": verdict})

    def record_deliberation(self, round_num: int, transcript: list[dict]):
        """Record a deliberation round."""
        self.record("judge", f"deliberation_round_{round_num}", {
            "round": round_num,
            "transcript": transcript
        })

    def record_hallucination_check(self, agent: str, checks: list[dict]):
        """Record hallucination detector checks."""
        self.record(agent, "hallucination_checks", {"checks": checks})

    def to_dict(self) -> dict:
        """Export the full compliance trace."""
        return {
            "run_id": self.run_id,
            "enabled": self.enabled,
            "trace_length": len(self.trace),
            "trace": self.trace,
            "generated_at": time.time()
        }

    def to_json(self) -> str:
        """Export as JSON string."""
        return json.dumps(self.to_dict(), indent=2)


def create_compliance_trace(run_id: str, explain_param: str | None) -> ComplianceTrace:
    """Create a compliance trace based on the explain parameter."""
    enabled = explain_param == "full"
    return ComplianceTrace(run_id, enabled)
