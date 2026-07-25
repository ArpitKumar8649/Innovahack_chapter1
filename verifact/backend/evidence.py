"""FEC core — Fact-Embedded Citations.

Cryptographic integrity layer for evidence and verdicts:
- SHA-256 content hashing of every evidence chunk
- Merkle tree over a run's chunks (root published in the report;
  per-claim proofs let anyone verify quotes client-side)
- Exact-quote span validation (verifier quotes must exist in the corpus)
- Source authority tiers (MBFC-inspired domain registry)

The Merkle scheme is mirrored 1:1 in frontend/app.js (Web Crypto) so
verification needs no trust in the server.
"""
import hashlib
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# hashing & Merkle
# ---------------------------------------------------------------------------

def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def merkle_root(leaves: list[str]) -> str:
    """Deterministic Merkle root over hex-hash leaves (odd node duplicated)."""
    if not leaves:
        return sha256_hex("empty")
    level = list(leaves)
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [sha256_hex(a + b) for a, b in zip(level[0::2], level[1::2])]
    return level[0]


def merkle_proof(leaves: list[str], index: int) -> list[dict]:
    """Proof path for leaf at index: [{hash, side}], side = sibling position."""
    proof, level, idx = [], list(leaves), index
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        sib = idx ^ 1
        proof.append({"hash": level[sib], "side": "right" if sib > idx else "left"})
        level = [sha256_hex(a + b) for a, b in zip(level[0::2], level[1::2])]
        idx //= 2
    return proof


def verify_proof(leaf_hash: str, proof: list[dict], root: str) -> bool:
    cur = leaf_hash
    for p in proof:
        cur = sha256_hex(cur + p["hash"]) if p["side"] == "right" \
            else sha256_hex(p["hash"] + cur)
    return cur == root


# ---------------------------------------------------------------------------
# text normalization & span validation
# ---------------------------------------------------------------------------

_WS = re.compile(r"\s+")


def normalize_ws(text: str) -> str:
    return _WS.sub(" ", text).strip()


def validate_span(quote: str, chunk_text: str) -> bool:
    """True if the quote exists in the chunk — exact match, ellipsis-fragment
    match, or fuzzy 8-gram overlap (tolerates minor LLM transcription edits
    while still rejecting fabricated quotes)."""
    q, c = normalize_ws(quote), normalize_ws(chunk_text)
    if not q or not c:
        return False
    # 1. exact (whitespace-normalized, case-insensitive fallback)
    if q in c or q.lower() in c.lower():
        return True
    cl = c.lower()
    # 2. ellipsis handling: every substantial fragment must appear
    if "..." in q or "…" in q:
        frags = [normalize_ws(f) for f in re.split(r"\.\.\.|…", q)
                 if len(normalize_ws(f)) >= 20]
        if frags and all(f.lower() in cl for f in frags):
            return True
    # 3. fuzzy: ≥50% of the quote's 8-grams appear in the chunk
    qw, cw = q.lower().split(), cl.split()
    if len(qw) >= 8:
        cgrams = {tuple(cw[i:i + 8]) for i in range(len(cw) - 7)}
        total = len(qw) - 7
        hits = sum(1 for i in range(total) if tuple(qw[i:i + 8]) in cgrams)
        if total > 0 and hits / total >= 0.5:
            return True
    return False


# ---------------------------------------------------------------------------
# chunking
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    id: str            # "C{source_id}.{n}"
    source_id: int
    text: str
    hash: str = ""

    def __post_init__(self):
        if not self.hash:
            self.hash = sha256_hex(self.text)


def chunk_text(text: str, source_id: int, max_chunks: int = 8,
               target: int = 900) -> list[Chunk]:
    """Split extracted content into paragraph-merged chunks."""
    paras = [normalize_ws(p) for p in re.split(r"\n{2,}|\r\n{2,}", text) if p.strip()]
    chunks, buf = [], ""
    for p in paras:
        if len(buf) + len(p) <= target or not buf:
            buf = f"{buf} {p}".strip()
        else:
            chunks.append(buf)
            buf = p
        if len(chunks) >= max_chunks:
            break
    if buf and len(chunks) < max_chunks:
        chunks.append(buf)
    out = []
    for i, t in enumerate(chunks[:max_chunks]):
        t = t[:2500]  # hard cap per chunk
        out.append(Chunk(id=f"C{source_id}.{i}", source_id=source_id, text=t))
    return out


# ---------------------------------------------------------------------------
# source authority tiers (MBFC-inspired; suffix-matched on hostname)
# ---------------------------------------------------------------------------

TIER1 = {  # primary: official records, peer-reviewed, wire services
    "nobelprize.org", "nature.com", "science.org", "cell.com", "thelancet.com",
    "nejm.org", "bmj.com", "who.int", "cdc.gov", "nasa.gov", "nih.gov",
    "nsf.gov", "epa.gov", "noaa.gov", "ipcc.ch", "arxiv.org", "pnas.org",
    "springer.com", "wiley.com", "aclanthology.org", "acm.org", "ieee.org",
    "reuters.com", "apnews.com", "un.org", "europa.eu",
}
TIER2 = {  # established reference & fact-checkers
    "wikipedia.org", "britannica.com", "bbc.com", "bbc.co.uk",
    "theguardian.com", "nytimes.com", "washingtonpost.com", "economist.com",
    "ft.com", "wsj.com", "npr.org", "pbs.org", "smithsonianmag.com",
    "nationalgeographic.com", "snopes.com", "politifact.com",
    "factcheck.org", "fullfact.org", "theconversation.com",
    "sciencedirect.com", "jstor.org", "nih.nlm.gov",
}
TIER3 = {  # reputable media
    "medium.com", "forbes.com", "businessinsider.com", "independent.co.uk",
    "cnn.com", "nbcnews.com", "cbsnews.com", "abcnews.go.com",
    "usatoday.com", "time.com", "newsweek.com", "axios.com",
    "theverge.com", "arstechnica.com", "wired.com", "livescience.com",
    "space.com", "scientificamerican.com", "newscientist.com",
    "skyatnightmagazine.com",
}
TIER5 = {  # social / UGC
    "reddit.com", "facebook.com", "twitter.com", "x.com", "instagram.com",
    "tiktok.com", "youtube.com", "quora.com", "pinterest.com",
}

TIER_WEIGHT = {1: 1.0, 2: 0.8, 3: 0.6, 4: 0.4, 5: 0.2}
TIER_LABEL = {
    1: "primary / peer-reviewed",2: "established reference",
    3: "reputable media", 4: "blog / aggregator", 5: "social / UGC",
}


def authority_tier(url: str) -> int:
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return 4
    host = host.lower().removeprefix("www.")
    for tier, registry in ((1, TIER1), (2, TIER2), (3, TIER3), (5, TIER5)):
        for d in registry:
            if host == d or host.endswith("." + d):
                return tier
    if host.endswith(".gov") or host.endswith(".edu") or host.endswith(".gov.uk"):
        return 2
    return 4  # unknown → blog/aggregator tier


def publisher_of(url: str) -> str:
    try:
        return (urlparse(url).hostname or url).lower().removeprefix("www.")
    except Exception:
        return url
