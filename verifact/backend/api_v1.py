"""Public API v1 (Phase 7) — external access with API key auth.

Endpoints:
- POST /v1/verify — submit a claim for verification (async, returns run_id)
- GET /v1/status/{run_id} — check run status
- GET /v1/result/{run_id} — get full report
- POST /v1/keys — generate a new API key (admin only)
- GET /v1/keys — list API keys (admin only)

Auth: Bearer token (API key) in Authorization header.
Rate limiting: 10 requests/minute per key (in-memory, resets on restart).
"""
import secrets
import time
from collections import defaultdict
from pathlib import Path
import sqlite3

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel

router = APIRouter(prefix="/v1", tags=["public-api"])

DB_PATH = Path(__file__).parent / "api_keys.db"
RATE_LIMIT = 10  # requests per minute
RATE_WINDOW = 60  # seconds

# In-memory rate limiter: {api_key: [timestamps]}
_rate_limits = defaultdict(list)


def init():
    """Create the api_keys table if it doesn't exist.

    Bootstraps a single admin key on first run (when the table is empty) so
    the API is usable out of the box. Set VERITAS_ADMIN_KEY to pin it;
    otherwise one is generated and printed to stdout.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            key TEXT PRIMARY KEY,
            created_at REAL NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    """)
    count = conn.execute("SELECT COUNT(*) FROM api_keys").fetchone()[0]
    if count == 0:
        import os
        key = os.environ.get("VERITAS_ADMIN_KEY") or f"vai_{secrets.token_urlsafe(32)}"
        conn.execute(
            "INSERT INTO api_keys (key, created_at, is_admin) VALUES (?, ?, 1)",
            (key, time.time())
        )
        print(f"[api_v1] bootstrap admin key: {key}", flush=True)
    conn.commit()
    conn.close()


def generate_key(is_admin: bool = False) -> str:
    """Generate a new API key."""
    key = f"vai_{secrets.token_urlsafe(32)}"
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO api_keys (key, created_at, is_admin) VALUES (?, ?, ?)",
        (key, time.time(), int(is_admin))
    )
    conn.commit()
    conn.close()
    return key


def validate_key(key: str) -> bool:
    """Check if an API key is valid."""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT key FROM api_keys WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row is not None


def is_admin_key(key: str) -> bool:
    """Check if an API key has admin privileges."""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT is_admin FROM api_keys WHERE key = ?", (key,)).fetchone()
    conn.close()
    return bool(row and row[0])


def check_rate_limit(key: str):
    """Enforce rate limiting. Raises HTTPException if limit exceeded."""
    now = time.time()
    # Clean old timestamps
    _rate_limits[key] = [t for t in _rate_limits[key] if now - t < RATE_WINDOW]
    if len(_rate_limits[key]) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded (10 req/min)")
    _rate_limits[key].append(now)


async def get_api_key(authorization: str = Header(...)) -> str:
    """Extract and validate the API key from the Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    key = authorization[7:]
    if not validate_key(key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    check_rate_limit(key)
    return key


class VerifyRequest(BaseModel):
    claim: str


class VerifyResponse(BaseModel):
    run_id: str
    status: str


@router.post("/verify", response_model=VerifyResponse)
async def verify_claim(req: VerifyRequest, api_key: str = Depends(get_api_key)):
    """Submit a claim for verification. Returns a run_id for polling."""
    # Import here to avoid circular dependency
    from main import start_research, ResearchRequest

    result = await start_research(ResearchRequest(topic=req.claim))
    return VerifyResponse(run_id=result["run_id"], status="started")


@router.get("/status/{run_id}")
async def get_status(run_id: str, api_key: str = Depends(get_api_key)):
    """Check the status of a verification run."""
    from main import get_run

    result = await get_run(run_id)
    return {
        "run_id": run_id,
        "done": result["done"],
        "error": result.get("error")
    }


@router.get("/result/{run_id}")
async def get_result(run_id: str, api_key: str = Depends(get_api_key)):
    """Get the full report for a completed run."""
    from main import get_run

    result = await get_run(run_id)
    if not result["done"]:
        raise HTTPException(status_code=400, detail="Run not complete yet")
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    return result["report"]


class KeyResponse(BaseModel):
    key: str
    is_admin: bool


@router.post("/keys", response_model=KeyResponse)
async def create_key(is_admin: bool = False, api_key: str = Depends(get_api_key)):
    """Generate a new API key (admin only)."""
    if not is_admin_key(api_key):
        raise HTTPException(status_code=403, detail="Admin key required")
    new_key = generate_key(is_admin=is_admin)
    return KeyResponse(key=new_key, is_admin=is_admin)


@router.get("/keys")
async def list_keys(api_key: str = Depends(get_api_key)):
    """List all API keys (admin only)."""
    if not is_admin_key(api_key):
        raise HTTPException(status_code=403, detail="Admin key required")
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT key, created_at, is_admin FROM api_keys").fetchall()
    conn.close()
    return [
        {"key": r[0][:12] + "...", "created_at": r[1], "is_admin": bool(r[2])}
        for r in rows
    ]
