"""Feedback Loop (Phase9) — RLHF-style policy updates from human + AI signals.

Closes the learning loop:
1. Expert referee flags (Phase 7) → human corrections
2. Red-team findings (Phase 9) → adversarial discoveries
3. Both feed into policy updates: prompt adjustments, weight tuning,
   new trap-suite cases

The system literally learns from its own mistakes and adversarial probing.
"""
import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "feedback.db"


def init():
    """Create the feedback and policy tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            claim_text TEXT NOT NULL,
            finding TEXT NOT NULL,
            severity TEXT NOT NULL,
            created_at REAL NOT NULL,
            applied INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS policy_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            update_type TEXT NOT NULL,
            description TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at REAL NOT NULL,
            applied_at REAL
        )
    """)
    conn.commit()
    conn.close()


def record_feedback(source: str, claim_text: str, finding: str, severity: str):
    """Record a feedback signal (from referee or red-team)."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO feedback (source, claim_text, finding, severity, created_at) VALUES (?, ?, ?, ?, ?)",
        (source, claim_text, finding, severity, time.time())
    )
    conn.commit()
    conn.close()


def get_pending_feedback(limit: int = 50) -> list[dict]:
    """Get unapplied feedback signals."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, source, claim_text, finding, severity, created_at "
        "FROM feedback WHERE applied = 0 ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [
        {"id": r[0], "source": r[1], "claim_text": r[2], "finding": r[3],
         "severity": r[4], "created_at": r[5]}
        for r in rows
    ]


def mark_feedback_applied(feedback_ids: list[int]):
    """Mark feedback signals as applied."""
    if not feedback_ids:
        return
    conn = sqlite3.connect(DB_PATH)
    placeholders = ",".join("?" * len(feedback_ids))
    conn.execute(
        f"UPDATE feedback SET applied = 1 WHERE id IN ({placeholders})",
        feedback_ids
    )
    conn.commit()
    conn.close()


def record_policy_update(update_type: str, description: str, payload: dict):
    """Record a policy update (prompt change, weight adjustment, etc.)."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO policy_updates (update_type, description, payload, created_at) VALUES (?, ?, ?, ?)",
        (update_type, description, json.dumps(payload), time.time())
    )
    conn.commit()
    conn.close()


def get_policy_updates(limit: int = 20) -> list[dict]:
    """Get recent policy updates."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, update_type, description, payload, created_at, applied_at "
        "FROM policy_updates ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [
        {"id": r[0], "update_type": r[1], "description": r[2],
         "payload": json.loads(r[3]), "created_at": r[4], "applied_at": r[5]}
        for r in rows
    ]


def generate_policy_from_feedback() -> dict:
    """Analyze pending feedback and generate policy recommendations.

    This is the RLHF-style loop: aggregate human + AI signals into
    actionable policy updates.
    """
    pending = get_pending_feedback(limit=100)
    if not pending:
        return {"recommendations": [], "summary": "No pending feedback"}

    # Aggregate by source and severity
    by_source = {}
    by_severity = {"high": 0, "medium": 0, "low": 0}
    for f in pending:
        src = f["source"]
        by_source[src] = by_source.get(src, 0) + 1
        by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1

    recommendations = []

    # High-severity findings → prompt hardening
    if by_severity["high"] > 0:
        recommendations.append({
            "type": "prompt_hardening",
            "description": f"{by_severity['high']} high-severity findings detected",
            "action": "Add explicit warnings to verifier prompts about these failure modes",
            "priority": "high"
        })

    # Red-team findings → new trap cases
    redteam_count = by_source.get("red_team", 0)
    if redteam_count > 0:
        recommendations.append({
            "type": "trap_suite_expansion",
            "description": f"{redteam_count} red-team findings to convert to test cases",
            "action": "Add these as regression tests in the trap suite",
            "priority": "medium"
        })

    # Referee flags → weight tuning
    referee_count = by_source.get("referee", 0)
    if referee_count > 0:
        recommendations.append({
            "type": "weight_tuning",
            "description": f"{referee_count} expert corrections received",
            "action": "Review confidence formula weights (source_authority, evidence_coverage)",
            "priority": "medium"
        })

    return {
        "recommendations": recommendations,
        "summary": f"{len(pending)} pending signals: {by_severity['high']} high, {by_severity['medium']} medium, {by_severity['low']} low",
        "by_source": by_source,
        "by_severity": by_severity
    }


def apply_policy_update(update_type: str, payload: dict) -> bool:
    """Apply a policy update (stub — in production, this would modify prompts/weights).

    For the hackathon, we just record it as applied. In production, this would:
    - Update prompt templates in the database
    - Adjust scoring weights in scoring.py
    - Add new test cases to eval/trap_suite.json
    """
    record_policy_update(update_type, f"Applied: {update_type}", payload)
    return True


def stats() -> dict:
    """Summary stats for the feedback loop."""
    conn = sqlite3.connect(DB_PATH)
    total_feedback = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM feedback WHERE applied = 0").fetchone()[0]
    total_updates = conn.execute("SELECT COUNT(*) FROM policy_updates").fetchone()[0]
    conn.close()
    return {
        "total_feedback": total_feedback,
        "pending_feedback": pending,
        "applied_feedback": total_feedback - pending,
        "policy_updates": total_updates
    }
