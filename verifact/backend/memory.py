"""Cross-run memory — the system learns (Phase 3 knowledge layer).

SQLite + FTS5, three registries:

- claim_memory   normalized claim → last verdict / status / confidence,
                 times seen, last checked. Re-investigating a topic loads
                 priors; freshly-verified claims (< CACHE_TTL) are reused
                 as-is (the 40%+ re-run speedup).
- claim_fts      FTS5 index for fuzzy recall — "have we verified something
                 LIKE this before?" (token-overlap match, not just exact).
- source_registry domain → authority tier. LLM classifications are persisted
                 here so the fallback classifier runs at most ONCE per domain.
- content_hashes chunk hash → times seen across distinct URLs. A quote that
                 recurs across sources is an early circular-citation signal
                 (the Phase 6 graph's seed).
"""
import hashlib
import re
import sqlite3
import threading
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "memory.db"
_lock = threading.Lock()

CACHE_TTL_S = 24 * 3600   # claims verified within this window are reused as-is

_WORD = re.compile(r"[a-z0-9]+")


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------

def init():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock, sqlite3.connect(DB_PATH) as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS claim_memory (
                claim_hash   TEXT PRIMARY KEY,
                text         TEXT,
                last_verdict TEXT,
                status       TEXT,
                confidence   INTEGER,
                times_seen   INTEGER DEFAULT 1,
                first_seen   REAL,
                last_checked REAL,
                topic        TEXT
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS claim_fts
                USING fts5(text, claim_hash UNINDEXED);
            CREATE TABLE IF NOT EXISTS source_registry (
                domain         TEXT PRIMARY KEY,
                authority_tier INTEGER,
                tier_source    TEXT,
                times_seen     INTEGER DEFAULT 1,
                last_seen      REAL
            );
            CREATE TABLE IF NOT EXISTS content_hashes (
                hash       TEXT PRIMARY KEY,
                chunk_id   TEXT,
                first_seen REAL,
                times_seen INTEGER DEFAULT 1,
                urls       TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS evidence_cache (
                topic_hash TEXT PRIMARY KEY,
                topic      TEXT,
                sources    TEXT,
                created    REAL
            );
        """)


# ---------------------------------------------------------------------------
# claim memory
# ---------------------------------------------------------------------------

def normalize_claim(text: str) -> str:
    return " ".join(_WORD.findall(text.lower()))


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _tokens(text: str) -> list[str]:
    return [t for t in normalize_claim(text).split() if len(t) >= 3]


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a | b) else 0.0


def _row_to_prior(row, exact: bool) -> dict:
    return {
        "text": row[1], "last_verdict": row[2], "status": row[3],
        "confidence": row[4], "times_seen": row[5],
        "last_checked": row[7], "topic": row[8], "exact": exact,
        "fresh": (time.time() - row[7])< CACHE_TTL_S,
        "age_days": round((time.time() - row[7]) / 86400, 1),
    }


def lookup_claim(text: str) -> dict | None:
    """Exact normalized-hash match first, then FTS5 fuzzy (≥60% token overlap)."""
    norm = normalize_claim(text)
    h = _hash(norm)
    with _lock, sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT * FROM claim_memory WHERE claim_hash=?", (h,)
        ).fetchone()
        if row:
            return _row_to_prior(row, exact=True)
        toks = _tokens(text)
        if len(toks) < 3:
            return None
        try:
            hits = con.execute(
                "SELECT text, claim_hash FROM claim_fts WHERE claim_fts MATCH ? "
                "LIMIT 15", (" OR ".join(toks),),
            ).fetchall()
        except sqlite3.OperationalError:
            return None
        target = set(toks)
        best_hash, best_score = None, 0.0
        for hit_text, hit_hash in hits:
            hit_toks = set(_tokens(hit_text))
            # recall-biased: reward covering the claim's tokens, penalize
            # extra ones (Jaccard alone misses "X won Y" ⊂ "X won Y for Z")
            score = 0.7 * (len(target & hit_toks) / len(target)) \
                  + 0.3 * _jaccard(target, hit_toks)
            if score >= 0.55 and score > best_score:
                best_hash, best_score = hit_hash, score
        if not best_hash:
            return None
        row = con.execute(
            "SELECT * FROM claim_memory WHERE claim_hash=?", (best_hash,)
        ).fetchone()
    return _row_to_prior(row, exact=False) if row else None


def topic_priors(topic: str, limit: int = 6) -> list[dict]:
    """Past findings related to a topic — Murli's priors at intake."""
    toks = _tokens(topic)
    if len(toks) < 2:
        return []
    with _lock, sqlite3.connect(DB_PATH) as con:
        try:
            hits = con.execute(
                "SELECT claim_hash FROM claim_fts WHERE claim_fts MATCH ? LIMIT 30",
                (" OR ".join(toks),),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        out = []
        for (h,) in hits:
            row = con.execute(
                "SELECT * FROM claim_memory WHERE claim_hash=?", (h,)
            ).fetchone()
            if row:
                out.append(_row_to_prior(row, exact=False))
    out.sort(key=lambda p: -p["last_checked"])
    return out[:limit]


def record_claim(text: str, last_verdict: str, status: str, confidence: int,
                 topic: str):
    """Upsert a verified claim into memory (+ FTS index)."""
    norm = normalize_claim(text)
    if not norm:
        return
    h = _hash(norm)
    now = time.time()
    with _lock, sqlite3.connect(DB_PATH) as con:
        existing = con.execute(
            "SELECT times_seen, first_seen FROM claim_memory WHERE claim_hash=?",
            (h,),
        ).fetchone()
        if existing:
            con.execute(
                "UPDATE claim_memory SET text=?, last_verdict=?, status=?, "
                "confidence=?, times_seen=?, last_checked=?, topic=? "
                "WHERE claim_hash=?",
                (text, last_verdict, status, confidence, existing[0] + 1,
                 now, topic, h),
            )
            con.execute("DELETE FROM claim_fts WHERE claim_hash=?", (h,))
        else:
            con.execute(
                "INSERT INTO claim_memory VALUES (?,?,?,?,?,?,?,?,?)",
                (h, text, last_verdict, status, confidence, 1, now, now, topic),
            )
        con.execute("INSERT INTO claim_fts (text, claim_hash) VALUES (?,?)",
                    (norm, h))


# ---------------------------------------------------------------------------
# source registry (domain → tier, persisted LLM classifications)
# ---------------------------------------------------------------------------

def get_domain_tier(domain: str) -> tuple[int, str] | None:
    with _lock, sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT authority_tier, tier_source FROM source_registry "
            "WHERE domain=?", (domain,),
        ).fetchone()
    return (row[0], row[1]) if row else None


def record_domain(domain: str, tier: int, tier_source: str = "llm"):
    now = time.time()
    with _lock, sqlite3.connect(DB_PATH) as con:
        existing = con.execute(
            "SELECT times_seen FROM source_registry WHERE domain=?", (domain,)
        ).fetchone()
        if existing:
            con.execute(
                "UPDATE source_registry SET authority_tier=?, tier_source=?, "
                "times_seen=?, last_seen=? WHERE domain=?",
                (tier, tier_source, existing[0] + 1, now, domain),
            )
        else:
            con.execute(
                "INSERT INTO source_registry VALUES (?,?,?,?,?)",
                (domain, tier, tier_source, 1, now),
            )


def bump_domain(domain: str):
    """Count a sighting without touching the stored tier classification."""
    now = time.time()
    with _lock, sqlite3.connect(DB_PATH) as con:
        con.execute(
            "UPDATE source_registry SET times_seen = times_seen + 1, last_seen = ? "
            "WHERE domain = ?", (now, domain),
        )


# ---------------------------------------------------------------------------
# content-hash index (circular-quote signal)
# ---------------------------------------------------------------------------

def record_hash(chunk_hash: str, chunk_id: str, url: str) -> tuple[int, int]:
    """Returns (times_seen, distinct_urls) after recording this chunk."""
    now = time.time()
    with _lock, sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT times_seen, urls FROM content_hashes WHERE hash=?",
            (chunk_hash,),
        ).fetchone()
        if row:
            urls = set(filter(None, row[1].split("\n")))
            urls.add(url)
            con.execute(
                "UPDATE content_hashes SET times_seen=?, urls=? WHERE hash=?",
                (row[0] + 1, "\n".join(sorted(urls))[:4000], chunk_hash),
            )
            return row[0] + 1, len(urls)
        con.execute(
            "INSERT INTO content_hashes VALUES (?,?,?,?,?)",
            (chunk_hash, chunk_id, now, 1, url),
        )
        return 1, 1


# ---------------------------------------------------------------------------
# evidence cache (topic → extracted corpus; skips Serper/Tavily on re-run)
# ---------------------------------------------------------------------------

def get_evidence(topic: str) -> list | None:
    """Return cached Source dicts if this topic was researched within TTL."""
    import json
    h = _hash(normalize_claim(topic))
    with _lock, sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT sources, created FROM evidence_cache WHERE topic_hash=?", (h,)
        ).fetchone()
    if not row or (time.time() - row[1]) > CACHE_TTL_S:
        return None
    try:
        return json.loads(row[0])
    except Exception:
        return None


def record_evidence(topic: str, sources) -> None:
    """Cache the extracted corpus (URLs + chunks + hashes) for a topic."""
    import json
    h = _hash(normalize_claim(topic))
    payload = [s.model_dump() for s in sources]
    with _lock, sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT OR REPLACE INTO evidence_cache (topic_hash, topic, sources, created) "
            "VALUES (?,?,?,?)",
            (h, topic, json.dumps(payload), time.time()),
        )


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------

def stats() -> dict:
    with _lock, sqlite3.connect(DB_PATH) as con:
        claims = con.execute("SELECT COUNT(*) FROM claim_memory").fetchone()[0]
        domains = con.execute("SELECT COUNT(*) FROM source_registry").fetchone()[0]
        hashes = con.execute("SELECT COUNT(*) FROM content_hashes").fetchone()[0]
        recurring = con.execute(
            "SELECT COUNT(*) FROM content_hashes WHERE times_seen > 1"
        ).fetchone()[0]
    return {"claims": claims, "domains": domains, "chunks_indexed": hashes,
            "recurring_quotes": recurring}
