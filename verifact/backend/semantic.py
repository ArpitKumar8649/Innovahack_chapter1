"""Semantic layer (Phase 6) — find the evidence keywords can't.

Keyword search matches shared *words*; semantic search matches shared
*meaning* — including passages that OPPOSE a claim while phrasing it
differently. Two persistent ChromaDB collections, embedded locally with
`bge-small-en-v1.5` (384-dim, ONNX, no torch):

- evidence  every extracted chunk, indexed by meaning
- claims    every verified claim, for cross-run semantic dedup

Counter-evidence retrieval is **contrastive**: a chunk scores by how much
it resembles the *contradiction* of the claim minus how much it resembles
the claim itself. That surfaces genuine opposition — a source that says the
wall is *not* visible — rather than restatements that merely share keywords.

Everything degrades gracefully: if fastembed/chromadb aren't installed or the
model can't load, every function is a no-op and the app runs as before.
"""
import gc
import os
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "chroma"

# tunables
COUNTER_K = 5                 # counter-evidence candidates returned
COUNTER_MIN_SCORE = 0.0       # contrastive floor: positive = net-opposing
DEDUP_THRESHOLD = 0.90        # cosine similarity above which claims are "the same"
MIN_MEMORY_MB = 500           # don't load the model if less than this is available

_model = None
_client = None
_collections: dict = {}
_disabled = False


# ---------------------------------------------------------------------------
# lazy initialization
# ---------------------------------------------------------------------------

def _log(msg: str):
    print(f"[semantic] {msg}", flush=True)


def _memory_available_mb() -> int:
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return 9999  # assume plenty if we can't check


def available() -> bool:
    """True if the semantic layer can run right now — deps present AND enough
    memory to load the model. Does NOT load the model (that's lazy, in
    _ensure_ready). Safe to call from health checks without side effects."""
    if _disabled:
        return False
    try:
        import fastembed  # noqa: F401
        import chromadb   # noqa: F401
    except ImportError:
        return False
    return _memory_available_mb() >= MIN_MEMORY_MB


def _ensure_ready():
    global _model, _client, _disabled
    if _model is not None or _disabled:
        return
    try:
        from fastembed import TextEmbedding
        import chromadb
    except Exception as e:                       # pragma: no cover
        _disabled = True
        _log(f"disabled (missing dependency): {e}")
        return
    try:
        # threads=1: onnxruntime's default per-thread buffers are the main
        # memory cost; on a constrained box (no swap) that can OOM-kill the
        # API mid-run. One thread keeps the footprint small.
        _model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5", threads=1)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(DATA_DIR))
        _collections["evidence"] = _client.get_or_create_collection(
            "evidence", metadata={"hnsw:space": "cosine"})
        _collections["claims"] = _client.get_or_create_collection(
            "claims", metadata={"hnsw:space": "cosine"})
        _log(f"ready — evidence={_collections['evidence'].count()}, "
             f"claims={_collections['claims'].count()}")
    except Exception as e:                       # pragma: no cover
        _disabled = True
        _log(f"disabled (init failed): {e}")


def unload():
    """Release the model + chroma client to free ~300MB. Call after a batch
    of semantic operations so the API's baseline stays small on constrained
    boxes (no swap). The next call to _ensure_ready() reloads everything."""
    global _model, _client
    if _model is not None:
        del _model
        _model = None
    if _client is not None:
        del _client
        _client = None
    _collections.clear()
    gc.collect()
    _log("unloaded (memory freed)")


def _embed(texts: list[str]) -> list[list[float]]:
    # cast np.float32 → native float; ChromaDB rejects numpy scalars
    return [[float(x) for x in v] for v in _model.embed(texts)]


# ---------------------------------------------------------------------------
# evidence index + counter-evidence retrieval
# ---------------------------------------------------------------------------

def index_evidence(chunks: list[dict]):
    """Add extracted chunks to the evidence index.

    Each chunk: {id, text, run_id, source_id, url, publisher, authority_tier}.
    Idempotent by chunk id (re-indexing the same run overwrites, not duplicates).
    """
    _ensure_ready()
    if _disabled or not chunks:
        return 0
    col = _collections["evidence"]
    ids, docs, metas, embs = [], [], [], []
    for ch in chunks:
        if not ch.get("text"):
            continue
        ids.append(ch["id"])
        docs.append(ch["text"])
        metas.append({
            "run_id": ch.get("run_id", ""),
            "source_id": int(ch.get("source_id", 0)),
            "url": ch.get("url", ""),
            "publisher": ch.get("publisher", ""),
            "authority_tier": int(ch.get("authority_tier", 4)),
        })
        embs.append(None)
    if not ids:
        return 0
    try:
        vectors = _embed(docs)
        # upsert so re-runs don't duplicate
        col.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=vectors)
        return len(ids)
    except Exception as e:                       # pragma: no cover
        _log(f"index_evidence failed: {e}")
        return 0


def counter_evidence(claim_text: str, k: int = COUNTER_K) -> list[dict]:
    """Find passages that OPPOSE the claim — the ones keyword search misses.

    Contrastive score = sim(chunk, "It is not true that <claim>")
                      − sim(chunk, claim)
    A positive score means the chunk sits closer to the *negation* of the
    claim than to the claim itself — genuine opposition, not a restatement.
    (Empirically chosen over "contradicts/refutes" meta-language, which lets
    keyword-sharing restatements leak through — embeddings are weak at
    negation, so we frame the query as the false claim directly.)
    """
    _ensure_ready()
    if _disabled or not claim_text:
        return []
    col = _collections["evidence"]
    if col.count() == 0:
        return []
    try:
        contra_q = f"It is not true that {claim_text}"
        v_contra, v_claim = _embed([contra_q, claim_text])
        # pull a wide candidate pool, then re-rank contrastively
        pool = col.query(query_embeddings=[v_contra], n_results=min(40, col.count()))
        cand_ids = pool["ids"][0]
        cand_docs = pool["documents"][0]
        cand_metas = pool["metadatas"][0]
        cand_embs = pool["embeddings"][0] if pool.get("embeddings") else None
        if cand_embs is None:
            cand_embs = _embed(cand_docs)
        scored = []
        for cid, doc, meta, emb in zip(cand_ids, cand_docs, cand_metas, cand_embs):
            sim_contra = _cos(emb, v_contra)
            sim_claim = _cos(emb, v_claim)
            score = sim_contra - sim_claim
            if score >= COUNTER_MIN_SCORE:
                scored.append({
                    "chunk_id": cid, "text": doc, "score": round(score, 3),
                    "source_id": meta.get("source_id"), "url": meta.get("url", ""),
                    "publisher": meta.get("publisher", ""),
                    "authority_tier": meta.get("authority_tier", 4),
                    "sim_to_claim": round(sim_claim, 3),
                })
        scored.sort(key=lambda x: -x["score"])
        return scored[:k]
    except Exception as e:                       # pragma: no cover
        _log(f"counter_evidence failed: {e}")
        return []


# ---------------------------------------------------------------------------
# claim index + semantic dedup
# ---------------------------------------------------------------------------

def record_claim(claim_id: int, text: str, run_id: str = "", status: str = ""):
    """Index a verified claim for cross-run semantic dedup."""
    _ensure_ready()
    if _disabled or not text:
        return
    col = _collections["claims"]
    try:
        vec = _embed([text])[0]
        col.upsert(
            ids=[f"c{claim_id}-{run_id or 'x'}"],
            documents=[text],
            metadatas=[{"claim_id": claim_id, "run_id": run_id, "status": status}],
            embeddings=[vec],
        )
    except Exception as e:                       # pragma: no cover
        _log(f"record_claim failed: {e}")


def find_similar_claims(text: str, threshold: float = DEDUP_THRESHOLD,
                        n: int = 3) -> list[dict]:
    """Claims from past runs that are semantically the same as `text`.

    Returns matches above `threshold` cosine similarity — the basis for
    cross-run dedup (merge evidence) and the "we've verified this before"
    signal that complements memory.py's lexical recall.
    """
    _ensure_ready()
    if _disabled or not text:
        return []
    col = _collections["claims"]
    if col.count() == 0:
        return []
    try:
        vec = _embed([text])[0]
        res = col.query(query_embeddings=[vec], n_results=min(n, col.count()))
        out = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0],
                                   res["distances"][0]):
            sim = 1 - dist   # cosine space: distance = 1 - similarity
            if sim >= threshold:
                out.append({
                    "claim_id": meta.get("claim_id"),
                    "run_id": meta.get("run_id", ""),
                    "text": doc, "similarity": round(sim, 3),
                })
        return out
    except Exception as e:                       # pragma: no cover
        _log(f"find_similar_claims failed: {e}")
        return []


# ---------------------------------------------------------------------------
# helpers + stats
# ---------------------------------------------------------------------------

def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def stats() -> dict:
    _ensure_ready()
    if _disabled:
        return {"available": False, "evidence_chunks": 0, "claims": 0,
                "model": None}
    return {
        "available": True,
        "evidence_chunks": _collections["evidence"].count(),
        "claims": _collections["claims"].count(),
        "model": "bge-small-en-v1.5",
    }
