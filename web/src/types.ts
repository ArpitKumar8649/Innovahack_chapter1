/* Types mirroring the FastAPI backend (verifact/backend/models.py + SSE events). */

export type Stance = "support" | "refute" | "insufficient";
export type Status =
  | "ESTABLISHED" | "SUPPORTED" | "CONTESTED"
  | "REFUTED" | "UNVERIFIABLE" | "OUTDATED" | "pending";

export interface Verdict {
  verifier: string;            // "A" | "B" | "C" | "J" (judge) | "M" (memory)
  stance: Stance;
  reasoning: string;
  quote: string;
  chunk_id: string;
  span_valid: boolean;
  signature: string;
  round: number;               // 0=cache 1=independent 2=deliberation 3=judge
  action: string;              // concede | rebut | hold | judge | cache | ""
  dissent: string;
}

export interface ChunkRef { chunk_id: string; text: string; hash: string; }

export interface Source {
  id: number;
  title: string;
  url: string;
  publisher: string;
  authority_tier: number;
  authority_label: string;
  retrieved_at: string;
  origin: string;              // web | scholar | news
  snippet: string;
  content_hash: string;
  chunks: ChunkRef[];
  published_at?: string;
}

export interface Hypothesis {
  id: string;
  statement: string;
  plausibility: number;
  counter_queries: string[];
  weaknesses?: string[];
}

export interface Claim {
  id: number;
  text: string;
  claim_type: string;
  hypothesis_id: string;
  status: Status;
  confidence: number;
  source_ids: number[];
  chunk_ids: string[];
  merkle_proofs: Record<string, MerkleStep[]>;
  verdicts: Verdict[];
  hallucinations: Hallucination[];
  verification_note: string;
  counter_evidence: CounterEvidence[];   // Phase 6: opposing passages keyword search missed
  semantic_prior?: SemanticPrior | null; // Phase 6: nearest past-run twin claim
}

export interface CounterEvidence {
  chunk_id: string;
  text: string;
  score: number;              // contrastive score: +ve = net-opposing
  source_id: number | null;
  url: string;
  publisher: string;
  authority_tier: number;
  sim_to_claim: number;
}

export interface SemanticPrior {
  claim_id: number;
  run_id: string;
  text: string;
  similarity: number;         // cosine similarity to the past-run claim
}

export interface GraphStats {
  claims: number;
  sources: number;
  publishers: number;
  edges: number;
  circular_citations: number;
  cycles: string[][];         // first 5 cycles for display
}

export interface Hallucination {
  type: string; severity: string; evidence: string; correction?: string;
}

export interface Contradiction { claim_id: number; kind: string; description: string; }

export interface MerkleStep { hash: string; side: "left" | "right"; }

export interface Prior {
  text: string; last_verdict: string; status: Status; confidence: number;
  times_seen: number; last_checked: number; topic: string;
  exact: boolean; fresh: boolean; age_days: number;
}

export interface TranscriptEntry {
  claim_id: number; claim: string; round: number; verifier: string;
  action: string; stance: Stance; reasoning: string; quote: string;
  chunk_id: string; span_valid: boolean; dissent: string;
}

export interface Report {
  topic: string;
  summary: string;
  trust_score: number;
  hypotheses: Hypothesis[];
  claims: Claim[];
  sources: Source[];
  contradictions: Contradiction[];
  transcript: TranscriptEntry[];
  priors: Prior[];
  memory_stats: { cached: number; new: number; rounds: number; priors: number };
  argument_tree: ArgumentTree;
  trust_radar: TrustRadar;
  semantic_stats: SemanticStats;   // Phase 6
  graph_stats: GraphStats;         // Phase 7
  merkle_root: string;
  run_key: string;
  verified: boolean;
}

/* ------------------------- Phase 5: argumentation ------------------------- */

export interface TreeEdge {
  claim_id: number;
  text: string;
  relation: "supports" | "attacks";
  status: Status;
  confidence: number;
  verdicts: Record<string, Stance>;
  source_ids: number[];
  weight: number;
}

export interface HypothesisNode {
  id: string;
  statement: string;
  plausibility: number;
  supports: TreeEdge[];
  attacks: TreeEdge[];
  verdicts: Record<string, Stance>;
}

export interface WeakestLink {
  source_id: number;
  claim_id: number;
  hypothesis: string;
  tier: number;
  publisher: string;
  title: string;
  note: string;
}

export interface ArgumentTree {
  root: { claim_id: number; text: string; status: Status; confidence: number; verdicts: Record<string, Stance> } | null;
  hypotheses: HypothesisNode[];
  unattributed: { claim_id: number; text: string; status: Status; confidence: number }[];
  weakest_link: WeakestLink | null;
  multi_hypothesis: boolean;
}

export interface TrustRadar {
  agreement: number;
  authority: number;
  coverage: number;
  diversity: number;
  recency: number;
}

export interface Engagement {
  reports_viewed: number;
  mean_dwell_s: number;
  inspector_opens: number;
  tree_views: number;
  dwell_target_s: number;
}

export interface Attestation {
  run_id: string; topic: string;
  merkle_root: string; merkle_valid: boolean; chunks: number;
  signatures_checked: number; signatures_valid: number; signatures_ok: boolean;
  verified: boolean; issues: string[];
}

export interface MemoryStats {
  claims: number; domains: number; chunks_indexed: number; recurring_quotes: number;
}

export interface SemanticStats {
  available: boolean;
  evidence_chunks: number;
  claims: number;
  model: string | null;
}

export interface Calibration { n: number; ece: number; }

export interface Health {
  status: string; version: string; llm_model: string;
  llm_fallback?: string; tavily_configured: boolean;
  semantic_available?: boolean;
}

export interface RunSummary {
  run_id: string; topic: string; trust_score: number | null; error: string | null;
}

/* ------------------------- SSE event payloads ------------------------- */

export type StageName =
  | "intake" | "hypothesize" | "research" | "extract" | "verify"
  | "deliberate" | "hallucinations" | "contradictions" | "semantic" | "report";

export interface StageEvent { stage: StageName; status: "started" | "done"; rounds?: number; verifier_failures?: number; }
export interface LogEvent { stage: string; message: string; }
export interface PriorsEvent { priors: Prior[]; }
export interface HypothesesEvent { hypotheses: Hypothesis[]; queries: string[]; }
export interface SourcesEvent { sources: Source[]; cached?: boolean; }
export interface ClaimsEvent { claims: Claim[]; }
export interface CacheEvent { cached: { claim_id: number; text: string; confidence: number; status: Status }[]; }
export interface VerdictEvent { claim_id: number; verifier: string; stance: Stance; reasoning: string; quote: string; chunk_id: string; span_valid: boolean; }
export interface DebateEvent { transcript: TranscriptEntry[]; rounds: number; }
export interface ArgumentEvent { tree: ArgumentTree; radar: TrustRadar; }
export interface CounterEvidenceEvent { claim_id: number; counter: CounterEvidence[]; }
export interface HallucinationEvent extends Hallucination { claim_id: number; }
export interface ScoreEvent { claim_id: number; confidence: number; status: Status; }
export interface DoneEvent { run_id: string; elapsed_s: number; claims: number; sources: number; contradictions: number; cached: number; debate_rounds: number; merkle_root: string; }
export interface ErrorEvent { message: string; }

export type SseEventMap = {
  stage: StageEvent;
  log: LogEvent;
  priors: PriorsEvent;
  hypotheses: HypothesesEvent;
  sources: SourcesEvent;
  claims: ClaimsEvent;
  cache: CacheEvent;
  verdict: VerdictEvent;
  debate: DebateEvent;
  argument: ArgumentEvent;
  counter_evidence: CounterEvidenceEvent;
  hallucination: HallucinationEvent;
  contradiction: Contradiction;
  score: ScoreEvent;
  report: Report;
  done: DoneEvent;
  error: ErrorEvent;
  end: Record<string, never>;
};
