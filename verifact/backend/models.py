"""Pydantic models for the research pipeline."""
from pydantic import BaseModel, Field


class Source(BaseModel):
    id: int
    title: str
    url: str
    snippet: str
    score: float = 0.0


class Verdict(BaseModel):
    verifier: str  # "A" | "B" | "C"
    stance: str  # "support" | "refute" | "insufficient"
    reasoning: str
    source_ids: list[int] = Field(default_factory=list)


class Claim(BaseModel):
    id: int
    text: str
    claim_type: str = "fact"  # fact | statistic | date | entity | other
    status: str = "pending"  # pending | verified | disputed | contradicted | unverified
    confidence: int = 0  # 0-100
    source_ids: list[int] = Field(default_factory=list)
    verdicts: list[Verdict] = Field(default_factory=list)
    verification_note: str = ""  # plain-language note from the Writer


class Contradiction(BaseModel):
    claim_id: int
    kind: str  # verifier_disagreement | source_refuted | internal_conflict
    description: str


class Report(BaseModel):
    topic: str
    summary: str = ""
    trust_score: int = 0
    claims: list[Claim] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
