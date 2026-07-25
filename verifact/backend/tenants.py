"""Multi-tenant SaaS (Phase 9) — white-label API with usage metering.

Provides:
- Tenant registry (SQLite): tenant_id, name, api_key, plan, created_at
- Usage metering: track runs per tenant per day
- Plan-based rate limits: free (10 runs/day), pro (100), enterprise (unlimited)
- API key validation and tenant resolution

Production: this is the white-label API layer — each tenant gets their own
API key, usage is metered, and rate limits are enforced per plan.
"""
import secrets
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "tenants.db"

PLANS = {
    "free": {"daily_limit": 10, "label": "Free"},
    "pro": {"daily_limit": 100, "label": "Pro"},
    "enterprise": {"daily_limit": None, "label": "Enterprise"},  # unlimited
}


def init():
    """Create the tenants and usage tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            tenant_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            plan TEXT NOT NULL DEFAULT 'free',
            created_at REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usage (
            tenant_id TEXT NOT NULL,
            date TEXT NOT NULL,
            runs INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (tenant_id, date)
        )
    """)
    conn.commit()
    conn.close()


def create_tenant(name: str, plan: str = "free") -> dict:
    """Create a new tenant with a generated API key."""
    if plan not in PLANS:
        raise ValueError(f"Invalid plan: {plan}. Must be one of {list(PLANS.keys())}")
    tenant_id = f"t_{secrets.token_hex(8)}"
    api_key = f"vai_tenant_{secrets.token_urlsafe(32)}"
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO tenants (tenant_id, name, api_key, plan, created_at) VALUES (?, ?, ?, ?, ?)",
        (tenant_id, name, api_key, plan, time.time())
    )
    conn.commit()
    conn.close()
    return {"tenant_id": tenant_id, "name": name, "api_key": api_key, "plan": plan}


def get_tenant_by_key(api_key: str) -> dict | None:
    """Resolve a tenant from their API key."""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT tenant_id, name, api_key, plan, created_at FROM tenants WHERE api_key = ?",
        (api_key,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "tenant_id": row[0], "name": row[1], "api_key": row[2],
        "plan": row[3], "created_at": row[4]
    }


def get_tenant(tenant_id: str) -> dict | None:
    """Get a tenant by ID."""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT tenant_id, name, api_key, plan, created_at FROM tenants WHERE tenant_id = ?",
        (tenant_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "tenant_id": row[0], "name": row[1], "api_key": row[2],
        "plan": row[3], "created_at": row[4]
    }


def list_tenants() -> list[dict]:
    """List all tenants."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT tenant_id, name, plan, created_at FROM tenants ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [
        {"tenant_id": r[0], "name": r[1], "plan": r[2], "created_at": r[3]}
        for r in rows
    ]


def _today() -> str:
    return time.strftime("%Y-%m-%d")


def record_usage(tenant_id: str):
    """Record a run for a tenant (increments today's counter)."""
    today = _today()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO usage (tenant_id, date, runs) VALUES (?, ?, 1) "
        "ON CONFLICT(tenant_id, date) DO UPDATE SET runs = runs + 1",
        (tenant_id, today)
    )
    conn.commit()
    conn.close()


def get_usage(tenant_id: str, days: int = 30) -> list[dict]:
    """Get usage history for a tenant (last N days)."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT date, runs FROM usage WHERE tenant_id = ? ORDER BY date DESC LIMIT ?",
        (tenant_id, days)
    ).fetchall()
    conn.close()
    return [{"date": r[0], "runs": r[1]} for r in rows]


def check_rate_limit(tenant_id: str) -> tuple[bool, str]:
    """Check if a tenant has exceeded their daily limit.

    Returns (allowed, message).
    """
    tenant = get_tenant(tenant_id)
    if not tenant:
        return False, "Tenant not found"

    plan = PLANS.get(tenant["plan"], PLANS["free"])
    limit = plan["daily_limit"]
    if limit is None:
        return True, "Unlimited (enterprise)"

    today = _today()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT runs FROM usage WHERE tenant_id = ? AND date = ?",
        (tenant_id, today)
    ).fetchone()
    conn.close()

    used = row[0] if row else 0
    if used >= limit:
        return False, f"Daily limit reached ({used}/{limit} on {plan['label']} plan)"
    return True, f"{used}/{limit} used today ({plan['label']} plan)"


def stats() -> dict:
    """Summary stats for the tenant system."""
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM tenants").fetchone()[0]
    by_plan = {}
    for plan in PLANS:
        count = conn.execute(
            "SELECT COUNT(*) FROM tenants WHERE plan = ?", (plan,)
        ).fetchone()[0]
        by_plan[plan] = count
    today = _today()
    runs_today = conn.execute(
        "SELECT COALESCE(SUM(runs), 0) FROM usage WHERE date = ?", (today,)
    ).fetchone()[0]
    conn.close()
    return {
        "total_tenants": total,
        "by_plan": by_plan,
        "runs_today": runs_today,
    }
