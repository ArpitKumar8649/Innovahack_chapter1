"""Pydantic models for the Research Court pipeline (v2 — FEC-aware)."""
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# evidence layer
# ---------------------------------------------------------------------------

class ChunkRef(BaseModel):
    chunk_id: str
    text: str = ""      # chunk content (lets the inspector + verifier work offline)
    hash: str = ""      # SHA-256 of the chunk text


class Source(BaseModel):
    id: int
    title: str
    url: str
    publisher: str = ""
    authority_tier: int = 4          # 1 (primary) … 5 (social)
    authority_label: str = "unknown"
    retrieved_at: str = ""
    published_at: str = ""           # best-effort publication date (ISO)
    origin: str = "web"              # web | scholar | news
    snippet: str = ""
    content_hash: str = ""           # SHA-256 of the full extracted content
    chunks: list[ChunkRef] = Field(default_factory=list)  # chunk_id + hash only
    score: float = 0.0               # SERP relevance (kept for compatibility)


# ---------------------------------------------------------------------------
# hypotheses (Murli)
# ---------------------------------------------------------------------------

class Hypothesis(BaseModel):
    id: str                          # H1, H2, H3
    statement: str
    plausibility: float = 0.5        # prior plausibility 0-1
    counter_queries: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)  # self-identified (Murli)


# ---------------------------------------------------------------------------
# claims, verdicts, hallucinations
# ---------------------------------------------------------------------------

class Verdict(BaseModel):
    verifier: str                    # "A" | "B" | "C"
    stance: str                      # support | refute | insufficient
    reasoning: str
    quote: str = ""                  # exact evidence span (span-gate enforced)
    chunk_id: str = ""
    span_valid: bool = False         # quote verified against corpus
    signature: str = ""              # HMAC over canonical verdict fields


class Claim(BaseModel):
    id: int
    text: str
    claim_type: str = "fact"         # fact | statistic | date | entity | causal | other
    hypothesis_id: str = ""          # which H this claim belongs to
    status: str = "pending"          # epistemic status (see STATUS below)
    confidence: int = 0              # 0-100, computed
    source_ids: list[int] = Field(default_factory=list)
    chunk_ids: list[str] = Field(default_factory=list)
    merkle_proofs: dict = Field(default_factory=dict)  # chunk_id -> proof path
    verdicts: list[Verdict] = Field(default_factory=list)
    hallucinations: list[dict] = Field(default_factory=list)
    verification_note: str = ""


class Contradiction(BaseModel):
    claim_id: int
    kind: str                        # verifier_disagreement | source_refuted | internal_conflict
    description: str


# ---------------------------------------------------------------------------
# epistemic status taxonomy (v2 — replaces v1's 4 statuses)
# ---------------------------------------------------------------------------

STATUS = {
    "ESTABLISHED": "unanimous panel, high-tier sources, no contradictions",
    "SUPPORTED": "majority support with adequate evidence",
    "CONTESTED": "genuine disagreement — both sides shown",
    "REFUTED": "majority refute with evidence",
    "UNVERIFIABLE": "evidence insufficient — honest unknown",
    "OUTDATED": "was true; superseded by newer evidence",
}


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

class Report(BaseModel):
    topic: str
    summary: str = ""
    trust_score: int = 0
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    # FEC anchors
    merkle_root: str = ""
    run_key: str = ""                # per-run HMAC key (public, for signature checks)
    verified: bool = False           # result of /api/reports/{id}/verify
