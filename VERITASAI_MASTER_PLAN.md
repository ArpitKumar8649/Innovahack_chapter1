# VERITASAI — Master Implementation Plan
## Autonomous Multi-Agent Research & Fact-Verification System
### From "good demo" to "world's most trustworthy search engine"

> **Vision:** Replace black-box AI answers with a transparent *court of
> intelligent agents* that research, argue, verify, and cite in front of the
> user. Every claim in a VeritasAI report is a **verifiable artifact**:
> grounded in exact source quotes, scored by an algorithmic trust engine,
> and stress-tested by agents instructed to destroy it.

---

## 0. Where we are, where this goes

**Built today (VeriFact v1):** a working 7-agent pipeline — planner, Tavily
researcher, atomic-claim extractor, 3 adversarial verifiers, contradiction
detector, writer — with SSE live UI and deterministic confidence scoring.
It catches the Einstein and Great-Wall misconceptions 3-0. It is a good
*prototype*. It is not yet *brilliant*.

**What v1 lacks (the gap this plan closes):**

| Gap | Why it matters |
|---|---|
| Research is single-pass snippet-based | Verifiers judge claims from 200-char snippets, not real evidence |
| No self-adversarial reasoning | The system never asks "what if this is wrong?" before verifying |
| No source authority model | A random blog and NASA weigh the same in confidence scoring |
| No memory across runs | Every investigation starts from zero; the system never learns |
| No argument structure | Claims are a flat list — no hypothesis vs. counter-hypothesis tree |
| No benchmark evaluation | We *feel* it works; we cannot *prove* accuracy or calibration |
| Citations link URLs, not evidence | A user can't see the *exact sentence* a claim rests on |

**This plan** is phase-wise over ~18 months (compressed tracks noted for
hackathon contexts), each phase with deliverables, KPIs, and exit criteria.
Every technology choice below was researched against 2024-2026 literature
and — where it's an external API — **live-tested with our keys on
2026-07-25** (test results in Appendix A).

---

## 1. Research foundations (what the state of the art actually says)

| Source | Finding | Design consequence |
|---|---|---|
| **DebateCV** (SIGIR 2025) | Opposing debater agents + judge beat single-verifier fact-checking | Keep the adversarial panel; add *multi-turn* debate rounds (Phase 3) |
| **"Why Do Multi-Agent LLM Systems Fail?"** (2025) | Verifier superficiality is failure mode #1; task-focused verifiers → +15.6% accuracy | Distinct lenses + mandatory evidence citation (already in v1); add evidence *quality* gates (Phase 2) |
| **Fact-Audit** (ACL 2025, HKBU) | Adaptive multi-agent frameworks can *dynamically evaluate* LLM fact-checking | Build an evaluation harness that audits our own system continuously (Phase 2) |
| **FEVER** (Thorne et al.) | Standard benchmark: 185k claims, labels SUPPORTS / REFUTES / NOTENOUGHINFO, with gold evidence sentences; metrics = label accuracy + evidence precision/recall | Our benchmark target; proves the system scientifically (Phase 2+) |
| **FActScore** (Min et al.) | Atomic fact decomposition enables fine-grained verification | Already in v1 (Extractor); extend with typed claims (Phase 1) |
| **Stanford STORM** (2024) | Multi-perspective question-asking → higher-coverage cited articles | Murli's sub-question generation borrows this (Phase 0) |
| **LLM confidence calibration** (Amazon/MIT 2024-25) | LLMs self-report ~100% confidence even when wrong; consistency-based estimation works better | Confidence stays computed, never self-reported; add ECE calibration measurement (Phase 2) |
| **KG-based verification** (FactKG 2023, GraphCheck 2025, ClaimVer 2024) | Knowledge graphs enable multi-hop evidence chains and provenance tracking | Neo4j provenance graph is Phase 7 — *after* the value is proven, not before |
| **Provenance-enhanced statements** (2024) | Provenance itself is an epistemic signal: who said what, when, under which conditions | Every stored fact carries a provenance record from day one (Phase 1) |
| **Argument mining survey** (2024) | Claims/premises/relations structure; counter-argument generation by attacking weak premises | Argument trees with Toulmin structure (Phase 5) |
| **MBFC methodology** (Media Bias/Fact Check) | 10-point source credibility: factual reporting > bias > traffic/longevity | Source authority tiers modeled on this (Phase 2) |
| **Temporal — durable execution** (2025 docs) | Right tool for long-running multi-step workflows with real failure surfaces; gives retries + replay/audit for free | Adopt at Phase 8 when orchestration earns it — *not* at MVP |
| **AutoGen multi-agent debate pattern** | Multi-turn debate: agents exchange responses, refine based on others' | Debate rounds protocol (Phase 3) |

### What we adopt from the "VeritasAI" brief (friend's plan)

✅ Murli Agent with **self-adversarial reasoning** (the single best idea in it)
✅ Hypothesis + counter-hypothesis generation before verification
✅ Source authority scoring · ✅ Argument tree visualization
✅ Human expert "referee" escalation · ✅ Compliance/explain-everything mode
✅ Cross-run memory buffer · ✅ Red-team agent · ✅ Live debate UI · ✅ White-label API

### What we replace (and why — this is where depth shows)

| Brief's proposal | Problem | Our replacement |
|---|---|---|
| **Zero-Knowledge Proof of Truth** | ZKPs prove *computation integrity*, not *factual truth*. You cannot ZK-prove "source supports claim" without revealing the source — and revealing it is the whole point. It's crypto theater. | **Fact-Embedded Citations (FEC):** SHA-256 content hashes + exact-quote anchoring. Click a claim → see the *exact sentence* from the source, hash-verified, with URL + retrieval timestamp. Same trust goal, actually implementable, actually useful. |
| **Kong + RabbitMQ + Temporal at MVP** | Three distributed-systems components before a single user. Operational debt that kills hackathon-scale projects. | Single FastAPI + asyncio now. **Temporal at Phase 8** when multi-step durability genuinely earns its complexity. Message bus only if/when services split. |
| **4 different LLM providers day one** (Cohere+GPT-4+Gemini+Claude) | 4× the integration surface, 4× the key management, 4× the cost — before knowing if persona diversity or *model* diversity is what helps. | Persona-diverse panel on one provider now (proven in v1). **Provider-agnostic LLM layer from day one** so multi-model is a config change, adopted when evidence (our own A/B harness) shows it helps. |
| **Neo4j + ChromaDB + Postgres simultaneously** | Three databases to operate before product-market fit. | **Staged data layer:** SQLite+FTS5 (Phase 3) → ChromaDB (Phase 6) → Neo4j (Phase 7). Each added when the previous tier's limits are *measured*, not predicted. |
| **Mobile apps at month 11-12** | Distraction from the core trust engine. | Web-first; PWA if demanded. Mobile only post-Phase 9. |

---

## 2. Target architecture — "The Research Court"

```
┌────────────────────────────────────────────────────────────────────────────┐
│                            DEBATE THEATER UI                               │
│   live agent dialogue · argument tree · trust radar · evidence inspector   │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │ SSE / WebSocket
┌───────────────────────────────▼────────────────────────────────────────────┐
│                         ORCHESTRATION LAYER                                │
│   Phase 0-6: asyncio state machine (durable-run journal to SQLite)         │
│   Phase 8+:  Temporal workflows (replay, retry, audit for free)            │
│                                                                            │
│  ┌──────────────────────── THE COURT ────────────────────────────────┐     │
│  │                                                                   │     │
│  │  1. MURLI AGENT — the cognitive scientist (core)                  │     │
│  │     ├─ Hypothesis Generator   → 3 "theories of truth"             │     │
│  │     ├─ Self-Query Loop        → "if this is wrong, why?"          │     │
│  │     ├─ Evidence Requisition → Serper search/scholar/news │     │
│  │     └─ Devil's Advocate       → searches for COUNTER-evidence     │     │
│  │                                                                   │     │
│  │  2. EVIDENCE CORPUS — full-text, provenance-stamped               │     │
│  │     Serper URLs → Tavily Extract → chunked, hashed, indexed       │     │
│  │                                                                   │     │
│  │  3. VERIFIER PANEL — 3 adversarial lenses, multi-turn (Phase 3)   │     │
│  │     Evidentialist · Skeptic · Contextualist                       │     │
│  │     verdicts must quote exact evidence spans (FEC anchors)        │     │
│  │                                                                   │     │
│  │  4. HALLUCINATION DETECTOR — typed taxonomy                       │     │
│  │     entity · relation · number · date · extrapolation ·           │     │
│  │     unsupported · staleness                                       │     │
│  │                                                                   │     │
│  │  5. CONTRADICTION DETECTOR — cross-claim, source-vs-claim,        │     │
│  │     verifier-disagreement, temporal (old source vs new)           │     │
│  │                                                                   │     │
│  │  6. TRUST ENGINE — deterministic, calibrated                      │     │
│  │     verifier agreement × source authority × evidence coverage     │     │
│  │     × specificity × recency − contradiction penalty               │     │
│  │                                                                   │     │
│  │  7. SYNTHESIS / WRITER — citation-backed report                   │     │
│  │     with argument tree + epistemic status per claim               │     │
│  │                                                                   │     │
│  │  8. RED-TEAM AGENT (Phase 9) — probes reports for residual bias   │     │
│  │  9. EXPERT REFEREE (Phase 7) — human escalation + feedback loop   │     │
│  └───────────────────────────────────────────────────────────────────┘     │
│                                                                            │
│  ┌──────────────────── KNOWLEDGE LAYER (staged) ──────────────────────┐    │
│  │  P3: SQLite + FTS5 — run journal, claim memory, source registry    │    │
│  │  P6: ChromaDB — semantic index of evidence; counter-evidence │    │
│  │      retrieval ("find passages that OPPOSE this claim")            │    │
│  │  P7: Neo4j — provenance graph: Claim→Evidence→Source→Publisher,    │    │
│  │      multi-hop chains, "source A cites source B" cycles            │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
  Serper.dev              Tavily API              LLM provider(s)
  /search /scholar /search /extract        Qwen (DashScope) now
  /news (tested ✅)       (tested ✅)             provider-agnostic layer
```

### The 10-stage execution flow (target state)

1. **Intake** — topic/query in; check claim memory for prior investigations
2. **Hypothesis generation** (Murli) — 3 competing theories of truth
3. **Self-challenge** (Murli) — for each theory: "what evidence would disprove it?"
4. **Evidence requisition** — Serper web+scholar+news → Tavily full-text extract
5. **Claim decomposition** — atomic, typed claims anchored to evidence spans
6. **Adversarial verification** — 3 verifiers × N rounds, exact-quote verdicts
7. **Hallucination & contradiction sweep** — typed detection pass
8. **Trust scoring** — deterministic formula with source authority weights
9. **Synthesis** — report + argument tree + epistemic statuses
10. **Learning** — claims, verdicts, sources written to knowledge layer

---

## 3. Deep dive: the Murli Agent

**M**ulti-modal **U**nified **R**easoning **L**oop **I**ntegrator — the core
research agent. Standard agents "yes-sir" the prompt. Murli *plays devil's
advocate against itself before the court even convenes* — pre-filtering
hallucination at the source.

### 3.1 Self-Query Loop (the innovation)

```
for each source S found for hypothesis H:
    Murli asks itself:
      Q1: "If S is wrong, why would it be wrong?"        → failure modes
      Q2: "What evidence would DISPROVE H?"              → counter-queries
      Q3: "Who disagrees with S, and on what grounds?" → opposition search
      Q4: "Is S primary or hearsay? How old is it?"      → provenance check
    → issues Q2/Q3 as REAL searches (Serper), not rhetorical questions
```

### 3.2 Hypothesis Generator

Given a topic, produce **3 distinct theories of truth** — not one answer:

```
Topic: "Did climate change cause the 2023 Dubai floods?"
  H1 (attribution):  climate change intensified the rainfall event
  H2 (infrastructure): urban drainage failure was the primary cause
  H3 (null):         extreme rainfall within historical variance;
                     attribution not established
```

The Verifier panel then evaluates *evidence for each H*, and the report
presents the **most-debated answer** and the **weakest link** — not a
false binary.

### 3.3 Evidence Requisition (Serper → Tavily, tested today)

```
Serper /search   {q, num:10}  → organic[], peopleAlsoAsk[], knowledgeGraph
Serper /scholar  {q}          → academic papers (citation-weighted evidence)
Serper /news     {q, tbs}     → recency-sensitive events
        │
        ▼  top-K URLs (deduped, authority-pre-sorted)
Tavily /extract  {urls[≤20], extract_depth}  → full raw_content per URL
        │
        ▼
Evidence Corpus: {url, title, publisher_domain, retrieved_at,
                  content_hash (SHA-256), chunks[], authority_tier}
```

- `peopleAlsoAsk` feeds Murli's sub-question expansion (STORM-style coverage)
- `/scholar` results get an authority bonus (peer review signal)
- Every chunk gets a content hash → the FEC anchor (Section 6)
- Budget: ~3 Serper credits + 2-4 Tavily extract credits per run (Appendix A)

### 3.4 Output contract

```json
{
  "hypotheses": [{"id": "H1", "statement": "...", "prior_plausibility": 0.6}],
  "counter_queries_issued": ["...", "..."],
  "evidence_ids": ["E1", "E2", "..."],
  "self_identified_weaknesses": ["H1 rests on a single attribution study"],
  "claims": [{"text": "...", "type": "causal", "hypothesis": "H1",
              "evidence_spans": [{"evidence_id": "E3", "quote": "..."}]}]
}
```

---

## 4. The Verifier Panel v2 (multi-turn debate)

v1 runs one round: 3 lenses, majority vote. v2 adds **debate rounds**
(AutoGen pattern, DebateCV-grounded):

```
Round 1: A, B, C issue independent verdicts (with exact evidence quotes)
Round 2: each verifier reads the OTHERS' verdicts and may:
           - concede (with reason)
           - rebut (must cite evidence the others missed)
           - hold
Round 3 (only if no 2/3 consensus): the Judge agent weighs the final
           positions and rules, recording the dissent
```

**Anti-superficiality gates (hardened from v1):**
- verdicts must quote an evidence span ≥15 words from the corpus (no paraphrase-only)
- the Skeptic's default remains `insufficient` absent strong evidence
- a verifier that cites an evidence span the corpus doesn't contain → verdict
  auto-invalidated (catches hallucinated citations — a known LLM failure)

**Model diversity (designed-in, adopted when proven):** the LLM layer is
provider-agnostic from Phase 0. When budget allows, A/B test persona-diverse
single-model vs. model-diverse panel in our own harness (Phase 2) and let
data decide — not fashion.

---

## 5. Hallucination Detector v2 — typed taxonomy

Not one "is this hallucinated?" call. A typed sweep, each type with its own
detection prompt and evidence requirement:

| Type | Example failure | Detection method |
|---|---|---|
| **Entity** | confusing two people/companies with similar names | entity-resolution check against evidence spans |
| **Relation** | "X founded Y" when X merely *worked at* Y | relation extraction vs. source text |
| **Number** | "5,000 employees" vs. source's "500" | numeric span matching with tolerance |
| **Date** | wrong year/century | temporal expression grounding |
| **Extrapolation** | "all floods" from data on one flood | quantifier/scope check (HalluciNot-style span-level) |
| **Unsupported** | claim with zero evidence spans | coverage check against corpus |
| **Staleness** | true in 2015, false now | source-date vs. claim-tense analysis |

Each detection emits: `{claim_id, hallucination_type, severity, evidence,
corrected_version?}` — the corrected version feeds the report's
"Corrections" section.

---

## 6. Fact-Embedded Citations (FEC) — citations as verifiable artifacts

The brief's ZKP idea wanted *cryptographically verifiable truth*. ZKP itself
is the wrong tool here — it proves computation integrity, not semantic
truth, and hiding the source contradicts a problem statement that demands
*citation-backed* reports (the verifier must see the source; the user must
see the citation). What survives is the **goal**: citations as tamper-evident
cryptographic artifacts. FEC delivers it with four layers:

**Layer 1 — Content hashing.** At extraction time, each evidence chunk gets
`SHA-256(chunk_text)` + `retrieved_at` + `url` stored in the evidence
registry. Every verdict quotes an **exact span**; the span's chunk hash is
recorded alongside it.

**Layer 2 — Merkle anchoring (the ZKP-adjacent layer).** Each run's evidence
chunks form a **Merkle tree**; the report carries the **Merkle root**.
Every claim stores the Merkle **proof path** for its cited chunks, so any
verifier — client-side, no trust in our server — can cryptographically
confirm: *this exact quote was in the exact evidence set of this exact run.*
Tamper with one quote and the root breaks. This is the honest version of
"cryptographic proof of sourcing": integrity without a trusted party.

**Layer 3 — Signed verdicts (non-repudiation).** Each agent's verdict is
HMAC-signed with a per-run key; the report stores `(verifier, stance,
reasoning, quote, signature)`. The report proves *which* agent said *what*
in *which* run — agents cannot be silently re-quoted or edited after the
fact. The per-run key is published with the report, so signatures are
publicly checkable, not a shared secret.

**Layer 4 — Public verification endpoint.** `GET /api/reports/{id}/verify`
recomputes the Merkle root from stored chunks and validates every signature
and span hash, returning a machine-readable attestation. The UI renders a
**✓ Cryptographically verified** badge only when the endpoint (or the
client-side check) passes.

**The UI — Evidence Inspector.** Clicking `[3]` on any claim opens:
- the exact quoted sentence, highlighted in its source chunk
- source URL, publisher, authority tier, retrieval timestamp, content hash
- the verifier's reasoning attached to that span
- the Merkle proof, verifiable in-browser via Web Crypto (no server trust)

> "No more *I read it on the internet* — every claim shows its receipt,
> and the receipt is math."

**Where ZKP genuinely belongs (future):** if VeritasAI ever verifies claims
against *confidential* sources — corporate documents, medical or legal
records — where an outsider must be convinced *without* seeing the records,
ZKP/zkML becomes the right tool. That is a different product (enterprise
compliance), not this transparency-first PS; noted for Phase 9+ exploration.

---

## 7. Trust Engine v2 — algorithmic, calibrated, auditable

### 7.1 Source authority tiers (MBFC-inspired)

```
Tier 1 (1.0): primary sources — official records, peer-reviewed papers
              (Serper /scholar hit), government .gov, wire services
Tier 2 (0.8): established reference — encyclopedias, major institutions
Tier 3 (0.6): reputable media with editorial standards
Tier 4 (0.4): blogs, forums, aggregators
Tier 5 (0.2): unknown domains, social media
```

Tier assignment: domain registry (seeded from MBFC-style lists) + LLM
fallback classification for unknown domains + recency modifier
(>5 years old on fast-moving topics → one tier down).

### 7.2 Confidence formula v2

```
confidence(claim) =
    30 × verifier_agreement      (unanimous 1.0 · majority 0.66 · split 0.33)
  + 20 × evidence_coverage       (min(distinct_evidence_spans / 3, 1.0))
  + 20 × source_authority        (max tier weight among cited sources)
  + 10 × source_diversity        (distinct publishers / 2, capped 1.0)
  + 10 × specificity             (1.0, or 0.5 for hedged claims)
  + 10 × recency                 (freshness vs. topic velocity)
  − 35 × contradiction_penalty
  − 20 × hallucination_flag
  clamped to [5, 98]
```

### 7.3 Epistemic status taxonomy (replaces v1's 4 statuses)

| Status | Meaning |
|---|---|
| `ESTABLISHED` | ≥2 high-tier sources, unanimous panel, no contradictions |
| `SUPPORTED` | majority support, adequate evidence |
| `CONTESTED` | genuine expert disagreement — report shows BOTH sides |
| `REFUTED` | majority refute with evidence |
| `UNVERIFIABLE` | evidence insufficient — *honest unknown*, not a guess |
| `OUTDATED` | was true; superseded — shows old vs. new |

### 7.4 Calibration measurement (Phase 2)

Run the harness on FEVER/SciFact subsets; compute **Expected Calibration
Error (ECE)**: when we say 80% confidence, is the claim right ~80% of the
time? Publish the ECE in the UI footer. *A system that shows its own
calibration error is more trustworthy than one that hides it.*

---

## 8. Knowledge layer (staged — each tier earns the next)

### Phase 3 — SQLite + FTS5 (claim memory)
- **Run journal:** every run's full event log (already half-built) → replay, audit
- **Claim memory:** `(normalized_claim_text, last_verdict, confidence,
  last_checked_at, evidence_ids)` — re-investigating a topic loads prior
  findings as priors (Murli's "personal knowledge base" from the brief)
- **Source registry:** domain → authority tier, times-seen, hash index
- FTS5 full-text search over stored evidence → "have we seen this quote before?"

### Phase 6 — ChromaDB (semantic layer)
- Embed every evidence chunk (sentence-transformers, local — no API cost)
- **Counter-evidence retrieval:** given a claim, query
  `"evidence that contradicts: {claim}"` → surfaces opposing passages the
  keyword search missed. This is the brief's "find papers that oppose the
  hypothesis," made real.
- Cross-run dedup: semantically-similar claims merge their evidence

### Phase 7 — Neo4j (provenance graph)
```
(:Claim)-[:SUPPORTED_BY {quote, hash}]->(:Evidence)-[:FROM]->(:Source)
(:Source)-[:PUBLISHED_BY]->(:Publisher {authority_tier})
(:Source)-[:CITES]->(:Source)          ← circular-citation detection
(:Claim)-[:CONTRADICTS]->(:Claim)
(:Claim)-[:SUPERSEDES {date}]->(:Claim) ← temporal knowledge evolution
```
Enables multi-hop verification ("is the only source for this claim a blog
citing another blog?") and the **circular citation detector** — a genuinely
novel trust signal.

---

## 9. Argumentation layer — the report as an argument tree

Reports stop being flat claim lists. Each report carries a **Toulmin-structured
argument tree** (argument-mining literature, Phase 5):

```
                    ┌─ Evidence E1,E3 (Tier 1)
        ┌─ H1 ──────┤
        │           └─ Counter: E7 (Tier 4) — weak, single-source
Claim ──┤
        │           ┌─ Evidence E2 (Tier 2)
        └─ H2 ──────┤
                    └─ Counter: E5 (Tier 1) — strong, refutes H2
```

- nodes = hypotheses/claims; edges = supports/attacks with evidence weight
- rendered as an interactive collapsible tree in the UI (D3, no framework)
- every node shows its verdict distribution (A ✓ / B ✗ / C ✓)
- the **"weakest link" indicator** (from the brief): the load-bearing
  evidence span with the lowest authority — flagged visually

---

## 10. Debate Theater UI (Phase 5)

The frontend becomes a *theater*, not a dashboard:

1. **The Bench** — agent avatars light up as they act (v1 has this; v2 adds
   the dialogue)
2. **The Transcript** — live agent dialogue stream:
   *"Skeptic: I dispute C4 — source [2] says 320m, not 330m."
   "Evidentialist: Conceding; [2] is the 2010 figure. [5] confirms 330m
   after the antenna extension."*
3. **The Argument Tree** — Section 9's visualization, built live as verdicts land
4. **Trust Radar** — radial chart: agreement / authority / coverage /
   diversity / recency axes (the brief's "consensus score" visual)
5. **Evidence Inspector** — FEC panel (Section 6): exact quote, hash, source
6. **The Verdict** — final report with epistemic statuses and the
   corrections section

All streamed over SSE (v1's transport, proven). WebSocket upgrade only if
user interaction demands it (Phase 8).

---

## 11. Evaluation harness (Phase 2 — the difference between demo and science)

| Benchmark | What it proves | Metric |
|---|---|---|
| **FEVER subset** (1k claims) | label accuracy vs. gold SUPPORTS/REFUTES/NEI | accuracy, F1 |
| **SciFact subset** | scientific-claim verification | evidence precision/recall |
| **Misinformation trap suite** (our own, 50 claims) | catches famous misconceptions | trap catch-rate, false-alarm rate |
| **Calibration set** | confidence ↔ accuracy alignment | ECE |
| **Latency/cost budget** | usable in production | p50/p95 time, credits/run |

The harness runs in CI (GitHub Actions) on every merge — **Fact-Audit-style
continuous self-audit**. A regression in trap catch-rate blocks the merge.

---

## 12. Observability, API & enterprise (Phases 8-9)

- **Tracing:** every agent call → structured trace (agent, model, tokens,
  latency, verdict) in the run journal; Prometheus metrics endpoint
  (`verifact_agent_calls_total`, `verifact_hallucination_flags_total`…)
- **Compliance mode:** `?explain=full` forces every agent to emit its full
  reasoning chain in the report (regulated industries — the brief's idea, kept)
- **White-label API:** `POST /v1/verify` with API keys, rate limits, webhooks
  on completion; usage metering per tenant
- **Expert Referee portal** (Phase 7): domain experts flag verdicts;
  flagged topics route to an expert-context agent; flags become harness
  test cases (the feedback loop that makes the system *learn from humans*)
- **Red-Team agent** (Phase 9): continuously probes reports for residual
  bias and hallucination; its findings seed new trap-suite cases

---

## 13. Phase-wise roadmap

> Each phase: **Goal → Deliverables → Exit criteria (KPIs)**.
> Months assume a small team at sustainable pace. **Hackathon compression:**
> Phases 0-1 are achievable in24-48h (that's our current sprint); the rest
> is the 18-month product arc the brief asks for.

### Phase 0 — Foundation & Evidence Pipeline · *Month 0-1*
**Goal:** architecture frozen; Murli v1 with real evidence (not snippets).
- Serper client (`/search`, `/scholar`, `/news`) — **tested ✅ today**
- Tavily `/extract` client (full-text, ≤20 URLs/batch) — **tested ✅ today**
- Evidence corpus with content hashing + provenance records (FEC foundation)
- Murli v1: hypothesis generator + self-query loop + counter-evidence search
- Provider-agnostic LLM layer (Qwen now; swap by config)
- **Exit:** a run on the Dubai-floods example produces3 hypotheses, ≥8
  full-text sources, and a self-identified weakness list. Evidence inspector
  shows exact quotes with hashes.

### Phase 1 — The Full Court v1 · *Month 1-3*
**Goal:** Murli → Verifiers → Detector → Synthesis on full-text evidence.
- Verifier panel upgraded to quote exact evidence spans (span-validation gate)
- Typed hallucination detector (7 types, Section 5)
- Epistemic status taxonomy (Section 7.3) in reports
- Run journal → SQLite (durability, replay)
- **Exit:** report on any topic: every claim has ≥1 exact-quote citation,
  a typed status, and zero hallucinated citation spans (gate-measured).

### Phase 2 — Trust Engine & Evaluation · *Month 3-5*
**Goal:** prove the system scientifically.
- Source authority tiers (domain registry + LLM fallback + recency modifier)
- Confidence formula v2 (Section 7.2)
- Evaluation harness: FEVER-1k + SciFact + trap suite + ECE, in CI
- Multi-model A/B scaffolding (persona-diverse vs. model-diverse)
- **Exit:** ≥75% label accuracy on FEVER-1k; trap catch-rate ≥90% with
  false-alarm ≤10%; ECE measured and displayed.

### Phase3 — Memory & Multi-Turn Debate · *Month 5-7*
**Goal:** the system learns; the panel deliberates.
- Claim memory (priors from past runs) + source registry + FTS5
- Multi-turn debate rounds with Judge agent (Section 4)
- Debate transcript in the UI
- **Exit:** re-running a topic is 40%+ faster (cache hits) and cites prior
  findings; split-verdict claims show the debate transcript.

**Status — DONE (2026-07-25), measured:** re-run **56% faster** (55s→24s) via
topic-level evidence cache + claim cache (7/9 claims reused from memory);
6 priors recalled at intake; R2 deliberation observed (concede/rebut/hold
with cited evidence spans); Judge rules on unresolved splits with recorded
dissent; attestation intact on cached runs (Merkle + 9/9 signatures);
content-hash index flags recurring quotes (circular-citation seed);
model auto-fallback to qwen3.6-plus on quota exhaustion.

### Phase 4 — Debate Theater · React Frontend · *Month 7-9*
**Goal:** the court becomes a place you can watch — a crafted, living frontend.
- React + TypeScript + Vite app (replaces the vanilla-JS prototype)
- **Landing page:** long, detailed, distinctive — opens on the court in
  session (not a generic hero), sections for the agents, the FEC receipt
  stack, live measured numbers, and the debate itself
- **The Court (chat space):** each agent (Murli, Researcher, Extractor,
  Verifiers A/B/C, Judge, Writer) speaks in a live transcript as the run
  streams over SSE — verdicts, rebuttals, concessions, dissents as dialogue
- **Terminal:** a live log console mirroring the backend's stage/agent logs
- **Evidence Inspector + Trust gauge + claim verdicts** rebuilt in React,
  with client-side Merkle proof (Web Crypto) preserved
- **Exit:** the full run experience (intake → verdict) works end-to-end in
  React; landing page, chat space, and terminal all render live data;
  attestation badge passes against the real API.

### Phase 5 — Debate Theater & Argument Trees · *Month 9-11*
**Goal:** the trust gap closes visually.
- Argument tree extraction + Toulmin structure + weakest-link indicator
- Interactive tree visualization (D3) + Trust Radar + Evidence Inspector UI
- Report engagement analytics (do users read the debate?)
- **Exit:** argument tree renders for 100% of multi-hypothesis reports;
  mean report dwell time >60s (the brief's KPI).

**Status — DONE (2026-07-25), measured:** Toulmin argument tree built on every
report (root claim → hypotheses → supports/attacks evidence edges); on the
Dubai-floods run it rendered 2 hypotheses (H1: 6▲/1▼, H2: 3▲/0▼) with the
**weakest link** flagged (a T3 source the argument leans on); 5-axis **Trust
Radar** (agreement/authority/coverage/diversity/recency) computed from the
confidence components; collapsible SVG tree + radar + weakest-link banner in
the React report; **engagement analytics** (dwell time, inspector opens, tree
views) recorded client-side and aggregated at `/api/analytics` against the
>60s dwell KPI.

### Phase 6 — Semantic Layer · *Month 11-13*
**Goal:** find the evidence keywords can't.
- ChromaDB evidence index (local embeddings)
- Counter-evidence retrieval in Murli's loop
- Semantic claim dedup across runs
- **Exit:** on a 20-claim adversarial set, semantic retrieval surfaces
  opposing evidence that keyword search missed in ≥50% of cases.

### Phase 7 — Knowledge Graph & Expert Referee · *Month 13-15*
**Goal:** provenance at graph scale; humans in the loop.
- Neo4j provenance graph (Section 8) + circular-citation detector
- Multi-hop verification ("blog citing blog" downgrade)
- Expert Referee portal + flag→test-case pipeline
- Public API v1 (`POST /v1/verify`, keys, webhooks)
- **Exit:** circular citations detected on a seeded test set; ≥1 expert
  flag converted to a harness case; API serves external callers.

### Phase 8 — Durable Scale & Compliance · *Month 15-17*
**Goal:** production-grade orchestration.
- Temporal migration for run workflows (retry/replay/audit) — *now* justified
  by multi-round debates + graph lookups + human-escalation waits
- Prometheus/Grafana observability; Sentry error tracking
- Compliance mode (full reasoning chains)
- **Exit:** 100 concurrent runs p95< 90s; workflow replay reproduces a
  run's verdicts exactly; compliance report passes a mock audit.

### Phase 9 — Enterprise & Adversarial Maturity · *Month 17-18+*
**Goal:** platform, not tool.
- Red-Team agent (continuous bias/hallucination probing)
- White-label multi-tenant SaaS + usage metering
- RLHF-style loop: referee flags + red-team findings → prompt/policy updates
- Mobile/PWA only if demand signals justify
- **Exit:** 1,000+ enterprise signups target (brief's KPI); red-team
  findings trend down quarter-over-quarter.

---

## 14. Tech stack (final, with honest rationale)

| Layer | Choice | Why (and when it changes) |
|---|---|---|
| API | FastAPI + asyncio | proven in v1; SSE native; async concurrency |
| Orchestration | asyncio state machine → **Temporal (P8)** | durability earns its complexity only at multi-round + human-wait scale |
| LLM | Qwen/DashScope behind provider-agnostic layer | one working key today; multi-model is a config change, A/B-proven at P2 |
| Search | **Serper.dev** (search/scholar/news) | structured SERP JSON, PAA for sub-questions, scholar for authority; tested ✅ |
| Extraction | **Tavily /extract** | 20 URLs/call, clean raw_content; tested ✅ |
| Storage | SQLite+FTS5 (P3) → ChromaDB (P6) → Neo4j (P7) | each tier added when measured limits demand it |
| Frontend | **React + TypeScript + Vite (P4)** → D3 argument tree (P5) | prototype was vanilla JS; P4 rebuilds as a crafted SPA (landing + court chat + terminal) |
| Eval | FEVER/SciFact + custom trap suite in GitHub Actions | continuous self-audit (Fact-Audit pattern) |
| Observability | structured logs → Prometheus/Grafana/Sentry (P8) | right-sized per phase |
| Deploy | Docker + Render (now) → k8s (P8, if scale demands) | boring until it needs not to be |

---

## 15. Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| LLM verifiers hallucinate citations | High | Span-validation gate: quoted evidence must exist in corpus or verdict is void (P1) |
| Serper/Tavily quota or outage | Medium | credit budgeting per run; graceful degradation to Tavily-search-only mode (v1 behavior) |
| Single-model bias (all agents share one model's blind spots) | Medium | persona diversity now; model-diversity A/B at P2; multi-provider by config |
| Confidence miscalibration | High (literature) | ECE measured from P2; formula weights tunable from harness data |
| Scope creep (the brief's kitchen-sink) | High | staged data layer; each phase has an *exit criterion* — no phase starts early |
| Evidence paywalls (Tavily extract fails) | Medium | fallback to SERP snippets with `evidence_depth: snippet` flag; lower authority weight |
| Debate rounds explode latency | Medium | round cap (3); consensus short-circuit; async UI keeps users engaged |

---

## 16. Immediate next steps (post-plan)

1. **Phase 0, step 1:** `serper_client.py` + `tavily_extract` in the evidence
   pipeline; Evidence model with content hashes (FEC foundation)
2. **Phase 0, step 2:** Murli agent v1 — hypothesis generator + self-query
   loop + counter-evidence search, replacing v1's planner/researcher/extractor
3. **Phase 0, step 3:** Evidence Inspector UI (click citation → exact quote + hash)
4. Re-run the trap suite; confirm full-text evidence improves verdict quality
   over snippet-based v1 (measure, don't assume)

---

## Appendix A — Verified API contracts (tested 2026-07-25)

**Serper.dev** (key verified working):
```
POST https://google.serper.dev/search      headers: X-API-KEY, content-type
  {"q": "...", "num": 10}
  → {organic: [{title, link, snippet}], peopleAlsoAsk: [{question}],
     knowledgeGraph: {...}, answerBox: {...}, relatedSearches, credits}
POST https://google.serper.dev/scholar     → {organic: [{title, link, publicationInfo, citationCount?}]}
POST https://google.serper.dev/news        → {news: [{title, link, date, source}]}
Pricing: 10 results = 1 credit; 2,500 free credits; $50/50k credits
```

**Tavily** (key verified working):
```
POST https://api.tavily.com/extract        headers: Bearer tvly-...
  {"urls": [≤20], "extract_depth": "basic"|"advanced"}
  → {results: [{url, raw_content}], failed_results}
Credits: basic = 1 credit per 5 successful extractions; advanced = 2
POST https://api.tavily.com/search         (v1's current path, still used as fallback)
```

**LLM — DashScope/Qwen** (verified in v1 runs):
```
POST {base}/responses   (OpenAI Responses-API compatible)
  {"model": "qwen3.7-max-2026-06-08", "input": [messages], "enable_thinking": false}
  → {output: [{type: "message", content: [{type: "output_text", text}]}]}
Fallback: standard /chat/completions compatible endpoint (auto-detected)
```

## Appendix B — Glossary

- **FEC** — Fact-Embedded Citation: claim → exact source quote → content hash → URL
- **ECE** — Expected Calibration Error: gap between stated confidence and actual accuracy
- **Toulmin structure** — claim/grounds/warrant/backing/qualifier/rebuttal argument model
- **NEI** — Not Enough Information (FEVER's honest third label — we honor it as UNVERIFIABLE)
- **Trap suite** — our curated set of famous misconceptions (Einstein, Great Wall,
  "10% of the brain", "visible from space"…) used as regression tests
