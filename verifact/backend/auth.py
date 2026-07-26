"""User authentication — register, login, JWT, per-user run ownership.

Passwords hashed with bcrypt. Tokens are HS256 JWTs signed with JWT_SECRET
(env var; falls back to a dev-only default). The frontend stores the token
in localStorage and sends it as `Authorization: Bearer <token>`.
"""
import os
import secrets
import sqlite3
import threading
import time
from pathlib import Path

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "auth.db"
_lock = threading.Lock()

JWT_SECRET = os.environ.get("JWT_SECRET", "veritasai-dev-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
TOKEN_TTL_S = 7 * 24 * 3600  # 7 days

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------

def init():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock, sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         TEXT UNIQUE NOT NULL,
                name          TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at    REAL NOT NULL
            )""")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _make_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),   # PyJWT requires `sub` to be a string (RFC 7519)
        "email": email,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_TTL_S,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


def _get_user_by_id(user_id: int) -> dict | None:
    with _lock, sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT id, email, name, created_at FROM users WHERE id=?", (user_id,)
        ).fetchone()
    if not row:
        return None
    return {"id": row[0], "email": row[1], "name": row[2], "created_at": row[3]}


# ---------------------------------------------------------------------------
# FastAPI dependency — extract current user from Bearer token
# ---------------------------------------------------------------------------

def get_current_user(request: Request) -> dict | None:
    """Returns the user dict if a valid token is present, else None.
    Does NOT raise — callers decide whether auth is required."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    try:
        payload = _decode_token(token)
    except HTTPException:
        return None
    return _get_user_by_id(int(payload["sub"]))


def require_user(request: Request) -> dict:
    """Like get_current_user but raises 401 if no valid token."""
    user = get_current_user(request)
    if user is None:
        raise HTTPException(401, "Authentication required")
    return user


# ---------------------------------------------------------------------------
# request / response models
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    token: str
    user: dict


# ---------------------------------------------------------------------------
# endpoints
# ---------------------------------------------------------------------------

@router.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest):
    if len(req.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    pw_hash = _hash_password(req.password)
    with _lock, sqlite3.connect(DB_PATH) as con:
        existing = con.execute(
            "SELECT id FROM users WHERE email=?", (req.email,)
        ).fetchone()
        if existing:
            raise HTTPException(409, "An account with this email already exists")
        cur = con.execute(
            "INSERT INTO users (email, name, password_hash, created_at) VALUES (?,?,?,?)",
            (req.email, req.name, pw_hash, time.time()),
        )
        user_id = cur.lastrowid
    token = _make_token(user_id, req.email)
    user = _get_user_by_id(user_id)
    return AuthResponse(token=token, user=user)


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest):
    with _lock, sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT id, email, name, password_hash, created_at FROM users WHERE email=?",
            (req.email,),
        ).fetchone()
    if not row or not _check_password(req.password, row[3]):
        raise HTTPException(401, "Invalid email or password")
    token = _make_token(row[0], row[1])
    user = {"id": row[0], "email": row[1], "name": row[2], "created_at": row[4]}
    return AuthResponse(token=token, user=user)


@router.get("/me")
def me(user: dict = Depends(require_user)):
    return {"user": user}
