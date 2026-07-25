"""Run journal — SQLite persistence + cryptographic re-attestation (FEC L2-L3).

Stores finished runs (full report incl. chunk texts + Merkle root + run key)
so reports survive restarts and GET /api/reports/{id}/verify can recompute
the Merkle root and re-check every verdict signature from stored data alone.
"""
import json
import sqlite3
import threading
from pathlib import Path

from court import sign_verdict
from evidence import merkle_root, sha256_hex

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "journal.db"
_lock = threading.Lock()


def init():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock, sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id      TEXT PRIMARY KEY,
                topic       TEXT,
                started     REAL,
                finished    REAL,
                trust_score INTEGER,
                merkle_root TEXT,
                run_key     TEXT,
                error       TEXT,
                report      TEXT
            )""")
        cols = [r[1] for r in con.execute("PRAGMA table_info(runs)")]
        if "gold" not in cols:
            con.execute("ALTER TABLE runs ADD COLUMN gold TEXT")


def save_run(run):
    if run.report is None and run.error is None:
        return
    payload = run.report.model_dump() if run.report else None
    with _lock, sqlite3.connect(DB_PATH) as con:
        con.execute(
            """INSERT OR REPLACE INTO runs
               (run_id, topic, started, finished, trust_score, merkle_root,
                run_key, error, report, gold)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (run.id, run.topic, run.started, _now(),
             run.report.trust_score if run.report else None,
             run.report.merkle_root if run.report else "",
             run.run_key, run.error,
             json.dumps(payload) if payload else None,
             getattr(run, "gold", None)),
        )


def load_run(run_id: str) -> dict | None:
    with _lock, sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT topic, started, error, report FROM runs WHERE run_id=?",
            (run_id,)).fetchone()
    if not row:
        return None
    return {"run_id": run_id, "topic": row[0], "started": row[1],
            "done": True, "error": row[2],
            "report": json.loads(row[3]) if row[3] else None}


def list_runs(limit: int = 20) -> list[dict]:
    with _lock, sqlite3.connect(DB_PATH) as con:
        rows = con.execute(
            """SELECT run_id, topic, trust_score, error FROM runs
               WHERE run_id NOT LIKE 'eval-%'
               ORDER BY finished DESC LIMIT ?""", (limit,)).fetchall()
    return [{"run_id": r[0], "topic": r[1], "trust_score": r[2], "error": r[3]}
            for r in rows]


# ---------------------------------------------------------------------------
# cryptographic re-attestation
# ---------------------------------------------------------------------------

def verify_report(report: dict) -> dict:
    """Recompute the Merkle root and re-check all verdict signatures.

    Everything needed is in the report itself (chunk texts, hashes, proofs,
    run key) — attestation trusts no external state.
    """
    issues = []

    # 1. chunk hashes match their text
    leaves, chunk_hashes = [], {}
    for s in report.get("sources", []):
        for ch in s.get("chunks", []):
            recomputed = sha256_hex(ch.get("text", ""))
            if ch.get("hash") and ch["hash"] != recomputed:
                issues.append(f"chunk {ch['chunk_id']} hash mismatch")
            leaves.append(ch.get("hash") or recomputed)
            chunk_hashes[ch["chunk_id"]] = ch.get("hash") or recomputed

    # 2. Merkle root
    root = merkle_root(leaves) if leaves else ""
    merkle_valid = bool(root) and root == report.get("merkle_root", "")
    if not merkle_valid:
        issues.append("merkle root mismatch")

    # 3. verdict signatures (HMAC over verifier|claim|stance|quote)
    run_key = report.get("run_key", "")
    checked = valid = 0
    for c in report.get("claims", []):
        for v in c.get("verdicts", []):
            checked += 1
            expected = sign_verdict(run_key, v["verifier"], c["id"],
                                    v["stance"], v.get("quote", "")[:600])
            if v.get("signature") == expected:
                valid += 1
            else:
                issues.append(f"bad signature C{c['id']}/{v['verifier']}")

    return {
        "merkle_root": root,
        "merkle_valid": merkle_valid,
        "chunks": len(leaves),
        "signatures_checked": checked,
        "signatures_valid": valid,
        "signatures_ok": checked == valid,
        "verified": merkle_valid and checked == valid and not issues,
        "issues": issues[:10],
    }


def _now() -> float:
    import time
    return time.time()


# ---------------------------------------------------------------------------
# calibration (Phase 2: a system that shows its own calibration error)
# ---------------------------------------------------------------------------

STATUS_TO_LABEL = {
    "ESTABLISHED": "SUPPORTS", "SUPPORTED": "SUPPORTS",
    "REFUTED": "REFUTES", "OUTDATED": "REFUTES",
    "CONTESTED": "NOTENOUGHINFO", "UNVERIFIABLE": "NOTENOUGHINFO",
}


def _topic_claim(report: dict) -> dict | None:
    """The claim that states the topic itself (best word overlap)."""
    import re
    topic = re.sub(r"[^a-z0-9 ]", "", (report.get("topic") or "").lower()).split()
    if not topic:
        return None
    topic_set, best, best_score = set(topic), None, 0
    for c in report.get("claims", []):
        words = set(re.sub(r"[^a-z0-9 ]", "", c.get("text", "").lower()).split())
        score = len(topic_set & words)
        if score > best_score:
            best, best_score = c, score
    return best if best_score >= max(3, len(topic_set) // 2) else None


def calibration(bins: int = 10) -> dict:
    """ECE over eval runs (runs with a gold label) — when we say 80%
    confidence, is the claim right ~80% of the time?"""
    pairs = []  # (confidence 0-1, correct bool)
    with _lock, sqlite3.connect(DB_PATH) as con:
        rows = con.execute(
            "SELECT report, gold FROM runs WHERE gold IS NOT NULL AND report IS NOT NULL"
        ).fetchall()
    for report_json, gold in rows:
        report = json.loads(report_json)
        claim = _topic_claim(report)
        if claim is None:
            continue
        label = STATUS_TO_LABEL.get(claim.get("status", ""), "NOTENOUGHINFO")
        pairs.append((claim.get("confidence", 0) / 100, label == gold))

    ece, bin_data = 0.0, []
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        in_bin = [(c, ok) for c, ok in pairs
                  if lo <= c < hi or (b == bins - 1 and c == hi)]
        if not in_bin:
            continue
        acc = sum(ok for _, ok in in_bin) / len(in_bin)
        conf = sum(c for c, _ in in_bin) / len(in_bin)
        ece += (len(in_bin) / len(pairs)) * abs(acc - conf)
        bin_data.append({"lo": round(lo, 1), "n": len(in_bin),
                         "accuracy": round(acc, 3), "mean_conf": round(conf, 3)})
    return {"ece": round(ece, 3), "n": len(pairs), "bins": bin_data}
