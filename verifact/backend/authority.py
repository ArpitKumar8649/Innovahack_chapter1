"""Source authority v2 — registry + LLM fallback + recency modifier.

Phase 2 of the master plan (MBFC-inspired, §7.1):
- domain registry (evidence.py) handles known publishers
- unknown domains (tier 4) get an LLM classification, cached in SQLite
  so each domain is judged once, not per-run
- recency modifier: media/blog sources (tier ≥3) older than 5 years drop
  one tier — primary/reference sources never decay (historical facts)
"""
import datetime
import re
import sqlite3
import threading
from pathlib import Path

import llm

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "journal.db"
_lock = threading.Lock()
_cache: dict[str, int] = {}

CLASSIFY_SYSTEM = """You classify a website's credibility for fact-checking, using
the Media Bias/Fact Check methodology (factual reporting record first, then
bias, then longevity).
Tiers: 1 = primary source / peer-reviewed / government / wire service;
2 = established reference / major institution / fact-checker;
3 = reputable media with editorial standards;
4 = blog / aggregator / unknown;
5 = social media / user-generated content.
Return JSON: {"tier": 3, "reason": "one short phrase"}"""


def _init_cache_table():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock, sqlite3.connect(DB_PATH) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS domain_tiers (
            domain TEXT PRIMARY KEY, tier INTEGER, reason TEXT)""")


async def classify_domain(domain: str) -> tuple[int, str]:
    """LLM classification for an unknown domain, cached in SQLite."""
    domain = domain.lower().removeprefix("www.")
    if domain in _cache:
        return _cache[domain], "cached"
    _init_cache_table()
    with _lock, sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT tier, reason FROM domain_tiers WHERE domain=?", (domain,)
        ).fetchone()
    if row:
        _cache[domain] = row[0]
        return row[0], "cached"
    try:
        data = await llm.chat_json(
            CLASSIFY_SYSTEM, f"Domain: {domain}",
            temperature=0.0, max_tokens=200)
        tier = int(data.get("tier", 4))
        reason = (data.get("reason") or "")[:120]
    except Exception:
        tier, reason = 4, "classification failed"
    tier = max(1, min(5, tier))
    _cache[domain] = tier
    try:
        with _lock, sqlite3.connect(DB_PATH) as con:
            con.execute(
                "INSERT OR REPLACE INTO domain_tiers (domain, tier, reason) VALUES (?,?,?)",
                (domain, tier, reason))
    except Exception:
        pass
    return tier, reason


# ---------------------------------------------------------------------------
# date parsing (news dates + content scan)
# ---------------------------------------------------------------------------

_MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"])}

_REL_RE = re.compile(r"(\d+)\s*(minute|hour|day|week|month|year)s?\s*ago", re.I)
_ISO_RE = re.compile(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b")
_LONG_RE = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2}),?\s*(20\d{2})\b",
    re.I)
_LONG2_RE = re.compile(
    r"\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s*(20\d{2})\b",
    re.I)


def parse_date(text: str, now: datetime.datetime | None = None) -> str | None:
    """Best-effort publication date → ISO string, or None."""
    if not text:
        return None
    now = now or datetime.datetime.now(datetime.timezone.utc)
    text = text[:3000]

    m = _REL_RE.search(text)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        delta = {"minute": datetime.timedelta(minutes=n),
                 "hour": datetime.timedelta(hours=n),
                 "day": datetime.timedelta(days=n),
                 "week": datetime.timedelta(weeks=n),
                 "month": datetime.timedelta(days=30 * n),
                 "year": datetime.timedelta(days=365 * n)}[unit]
        return (now - delta).date().isoformat()

    m = _ISO_RE.search(text)
    if m:
        y, mo, d = (int(g) for g in m.groups())
        if 1 <= mo <= 12 and 1 <= d <= 31:
            try:
                return datetime.date(y, mo, d).isoformat()
            except ValueError:
                pass

    m = _LONG_RE.search(text)
    if m:
        mo = _MONTHS[m.group(1).lower()[:3]]
        try:
            return datetime.date(int(m.group(3)), mo, int(m.group(2))).isoformat()
        except ValueError:
            pass

    m = _LONG2_RE.search(text)
    if m:
        mo = _MONTHS[m.group(2).lower()[:3]]
        try:
            return datetime.date(int(m.group(3)), mo, int(m.group(1))).isoformat()
        except ValueError:
            pass
    return None


def age_years(iso_date: str, now: datetime.datetime | None = None) -> float | None:
    """Age in years of an ISO date, or None if unparseable."""
    try:
        d = datetime.date.fromisoformat(iso_date[:10])
    except (ValueError, TypeError):
        return None
    now = now or datetime.datetime.now(datetime.timezone.utc)
    return (now.date() - d).days / 365.25


def recency_score(iso_dates: list[str]) -> float:
    """Recency component of confidence: newest cited source's age.

    1.0 ≤2y · 0.7 ≤5y · 0.4 >5y · 0.8 unknown (slight penalty for undated)."""
    ages = [a for a in (age_years(d) for d in iso_dates if d) if a is not None]
    if not ages:
        return 0.8
    newest = min(ages)
    if newest <= 2:
        return 1.0
    if newest <= 5:
        return 0.7
    return 0.4


def recency_tier_modifier(tier: int, iso_date: str) -> int:
    """Media/blog sources (tier ≥3) older than 5 years drop one tier.
    Primary/reference sources (tier 1-2) never decay — historical facts."""
    if tier >= 3:
        age = age_years(iso_date) if iso_date else None
        if age is not None and age > 5:
            return min(5, tier + 1)
    return tier
