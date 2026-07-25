"""Expert Referee (Phase 7) — domain experts flag verdicts for review.

When an expert flags a verdict (e.g., "this claim is actually wrong" or
"the evidence is misinterpreted"), the flag is stored and can be converted
into a harness test case — closing the feedback loop between human expertise
and automated verification.

Storage: SQLite (referee.db) — simple, persistent, no external dependencies.
"""
import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "referee.db"


def init():
    """Create the referee table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            claim_id INTEGER NOT NULL,
            expert_name TEXT NOT NULL,
            reason TEXT NOT NULL,
            created_at REAL NOT NULL,
            converted_to_test INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def flag_verdict(run_id: str, claim_id: int, expert_name: str, reason: str) -> int:
    """Store an expert flag. Returns the flag ID."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "INSERT INTO flags (run_id, claim_id, expert_name, reason, created_at) VALUES (?, ?, ?, ?, ?)",
        (run_id, claim_id, expert_name, reason, time.time())
    )
    flag_id = cur.lastrowid
    conn.commit()
    conn.close()
    return flag_id


def get_flags(run_id: str = None, limit: int = 50) -> list[dict]:
    """Retrieve flags, optionally filtered by run_id."""
    conn = sqlite3.connect(DB_PATH)
    if run_id:
        rows = conn.execute(
            "SELECT id, run_id, claim_id, expert_name, reason, created_at, converted_to_test "
            "FROM flags WHERE run_id = ? ORDER BY created_at DESC LIMIT ?",
            (run_id, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, run_id, claim_id, expert_name, reason, created_at, converted_to_test "
            "FROM flags ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [
        {
            "id": r[0], "run_id": r[1], "claim_id": r[2],
            "expert_name": r[3], "reason": r[4], "created_at": r[5],
            "converted_to_test": bool(r[6])
        }
        for r in rows
    ]


def convert_to_test_case(flag_id: int) -> dict:
    """Convert a flag into a harness test case.

    Returns a test case dict that can be added to eval/cases.json.
    Marks the flag as converted.
    """
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT run_id, claim_id, expert_name, reason FROM flags WHERE id = ?",
        (flag_id,)
    ).fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Flag {flag_id} not found")

    run_id, claim_id, expert_name, reason = row

    # Load the run to get the claim text
    import journal
    run_data = journal.load_run(run_id)
    if not run_data or not run_data.get("report"):
        conn.close()
        raise ValueError(f"Run {run_id} not found or has no report")

    report = run_data["report"]
    claim = next((c for c in report["claims"] if c["id"] == claim_id), None)
    if not claim:
        conn.close()
        raise ValueError(f"Claim {claim_id} not found in run {run_id}")

    # Build the test case
    test_case = {
        "claim": claim["text"],
        "expected_label": "REFUTES" if claim["status"] in ["REFUTED", "CONTESTED"] else "SUPPORTS",
        "expert_flag": {
            "flag_id": flag_id,
            "expert_name": expert_name,
            "reason": reason,
            "original_status": claim["status"],
            "original_confidence": claim["confidence"]
        },
        "source": "expert_referee",
        "created_at": time.time()
    }

    # Mark as converted
    conn.execute("UPDATE flags SET converted_to_test = 1 WHERE id = ?", (flag_id,))
    conn.commit()
    conn.close()

    return test_case


def stats() -> dict:
    """Summary stats for the referee system."""
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM flags").fetchone()[0]
    converted = conn.execute("SELECT COUNT(*) FROM flags WHERE converted_to_test = 1").fetchone()[0]
    conn.close()
    return {
        "total_flags": total,
        "converted_to_tests": converted,
        "pending_review": total - converted
    }
