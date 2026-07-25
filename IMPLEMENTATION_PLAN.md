# VeriFact — Implementation Plan
## Autonomous Multi-Agent Research & Fact-Verification System
### InnovaHack Chapter 1 · Domain 3: Gen AI · Problem Statement 1

---

## 1. Executive Summary

**VeriFact** takes a research topic and produces a citation-backed report where
every claim has been independently verified by an adversarial panel of AI
agents — with a confidence score and source citations for each claim, and an
explicit contradictions section showing where sources disagree.

**The one-line pitch:** *ChatGPT gives you an answer. VeriFact gives you an
answer that three independent agents argued about, sources you can click, and
an honest confidence score for every sentence.*

**Why this wins the problem statement:** the PS asks for four agents
(researcher, cross-verifier, contradiction-detector, report-compiler) with
per-claim confidence scores. VeriFact delivers exactly that — plus an
adversarial 3-verifier panel (grounded in2025 research showing single
verifiers are superficial), a transparent live pipeline UI, and a
"misinformation trap" demo that proves hallucination detection works.

---

## 2. Problem Statement Deconstruction

From the PDF (Domain 3, PS1), the graded requirements:

| # | Requirement | VeriFact delivery |
|---|---|---|
| 1 | Agent researches a topic | **Researcher** — Tavily multi-query search, dedup, rank |
| 2 | Agent cross-verifies claims against multiple sources | **3× Verifier panel** — independent adversarial lenses, majority vote |
| 3 | Agent detects contradictions/hallucinations | **Contradiction Detector** — cross-claim, source-vs-claim, verifier-disagreement analysis |
| 4 | Agent compiles citation-backed report | **Writer** — every claim linked to source IDs, inline citations |
| 5 | Confidence score per claim | Multi-signal formula (verifier agreement + source count + quality + specificity − contradiction penalty) |
| 6 | Multi-agent orchestration | 7 specialized agents, asyncio pipeline with SSE live progress |

**Suggested focus areas from PS (all covered):**
- ✅ Multi-agent orchestration (research, verification, synthesis)
- ✅ Contradiction / hallucination detection logic
- ✅ Source citation for every claim
- ✅ Per-claim confidence scoring

---

## 3. Research Foundation (what the state of the art says)

| Source | Finding | How VeriFact uses it |
|---|---|---|
| **Stanford STORM** (2024) | Multi-perspective question-asking + outline-first generation produces Wikipedia-quality cited articles | Pipeline shape: plan → research → structure → write with citations |
| **DebateCV** (SIGIR 2025) | Opposing debater agents + judge outperform single-verifier fact-checking | 3 verifiers with opposing lenses (evidentialist / skeptic / contextualist), majority vote |
| **"Why Do Multi-Agent LLM Systems Fail?"** (Mar 2025) | Verifier superficiality is the #1 failure mode; task-focused verifiers give +15.6% accuracy | Each verifier gets a distinct adversarial persona + must cite evidence IDs (no hand-waving) |
| **FActScore** (Min et al.) | Atomic claim decomposition enables fine-grained verification | Extractor decomposes research into atomic, independently-verifiable claims |
| **Confidence calibration research** (Amazon/MIT 2024-25) | LLM self-reported confidence is miscalibrated (reports 100% when wrong) | Confidence is a computed multi-signal formula, never self-reported |
| **Hallucination detection survey** (arXiv 2510.06265) | Two-phase pattern: claim extraction → evidence entailment checking | Exactly our Extractor → Verifier pipeline |

---

## 4. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (SPA)                             │
│  Topic input → Live pipeline tracker (SSE) → Verified report        │
│  (per-claim confidence badges · inline citations · contradictions)  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ POST /api/research  →  GET /api/research/{id}/stream (SSE)
┌──────────────────────────────▼──────────────────────────────────────┐
│                     FASTAPI BACKEND (async)                         │
│                                                                     │
│  ┌──────────────────────── PIPELINE ───────────────────────────┐    │
│  │                                                             │    │
│  │  1. PLANNER ──────► research plan (subtopics + queries)     │    │
│  │         │                                                   │    │
│  │  2. RESEARCHER ───► Tavily search (multi-query, dedup)      │    │
│  │         │            sources[] with snippets                │    │
│  │  3. EXTRACTOR ────► atomic claims[] from sources            │    │
│  │         │            (FActScore-style decomposition)        │    │
│  │  4. VERIFIER PANEL ── 3 agents in parallel ──┐              │    │
│  │         │   A: Evidentialist (what sources say)             │    │
│  │         │   B: Skeptic (attack each claim)    ├─► verdicts  │    │
│  │         │   C: Contextualist (nuance/dates)   ┘  + majority │    │
│  │         │                                                   │    │
│  │  5. CONTRADICTION DETECTOR ──► disagreements, refuted       │    │
│  │         │                       claims, internal conflicts  │    │
│  │  6. WRITER ───────► citation-backed report + trust score    │    │
│  │                                                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  Infrastructure: │
│  · LLM client — 5-key round-robin rotation, 429 retry w/ backoff │
│  · Run store — JSON per run (revisit reports, no DB needed)         │
│  · SSE emitter — stage/agent/claim events streamed live             │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                                 ▼
   llm.onerouter.pro (5 keys)            api.tavily.com
   qwen/qwen3.8-max-preview:free         search API
```

**Orchestration decision — custom asyncio, not LangGraph/CrewAI/AutoGen:**
the pipeline is a fixed DAG (no dynamic routing), so a framework adds
dependency risk, learning cost, and abstraction over the exact thing we need
to control (SSE event emission per agent step). Custom asyncio gives full
control in ~150 lines. *Production note for the PPT: LangGraph would be the
right choice if the pipeline needed dynamic branching (e.g., re-research on
low confidence) — documented as future work.*

---

## 5. Agent Design (7 agents)

### 5.1 Planner
- **Input:** user topic
- **Output (JSON):** `{subtopics: [...], search_queries: [... (6-8)], claim_types_to_watch: [...]}`
- **Prompt strategy:** "You are a research director. Decompose this topic into
 3-5 subtopics and generate 6-8 diverse search queries covering different
  angles (official sources, statistics, recent developments, criticisms)."
- **Why:** query diversity prevents single-source bias — the root cause of
  unverified claims.

### 5.2 Researcher
- **Input:** search queries
- **Output:** deduplicated `sources[]` (title, url, snippet, relevance score)
- **Mechanism:** parallel Tavily calls (asyncio.gather, 2 queries at a time to
  respect rate limits), dedup by URL, cap at 12 sources
- **No LLM call** — pure tool orchestration (fast, cheap)
- **Degradation:** if Tavily fails entirely → pipeline aborts with clear error
  (no point verifying without sources)

### 5.3 Extractor (Claim Decomposition Agent)
- **Input:** sources with snippets
- **Output (JSON):** `claims[]` — 6-10 **atomic** claims, each:
  `{text, claim_type: fact|statistic|date|entity, source_ids: [...]}`
- **Prompt strategy:** FActScore-style — "Decompose the research material into
  atomic, independently-verifiable claims. One fact per claim. No compound
  sentences. Tag each with the source IDs it came from."
- **Why atomic:** "X was founded in 2010 and has 5000 employees" can't be
  verified cleanly — one half may be true, the other false.

### 5.4 Verifier Panel (3 agents, parallel)
The core innovation. Each verifier sees **the same claims + sources** but
through a different adversarial lens (inspired by DebateCV + the
verifier-superficiality finding):

| Verifier | Lens | Prompt core |
|---|---|---|
| **A — Evidentialist** | "What do the sources literally say?" | Support a claim ONLY if a source explicitly states it. Quote the source snippet. |
| **B — Skeptic** | "How could this be wrong?" | Actively attack each claim. Look for outdated info, confusion between similar entities, unsourced assertions. Default to `insufficient` unless evidence is strong. |
| **C — Contextualist** | "Is this precise and current?" | Check dates, numbers, and scope. Flag claims that were true but may be outdated, or true with caveats the claim omits. |

- **Per-claim output:** `{stance: support|refute|insufficient, reasoning, source_ids}`
- **Hard rule in prompt:** every verdict MUST cite source IDs — a verdict
  without evidence is structurally invalid (this is the anti-superficiality
  mechanism from the failure-modes paper)
- **Batching:** all claims in one call per verifier (≤10 claims fits context) →
  3 LLM calls total, run concurrently on 3 different keys
- **Majority vote:** ≥2 support → verified · ≥2 refute → contradicted ·
  mixed → disputed · all insufficient → unverified

### 5.5 Contradiction Detector
- **Input:** claims + all verdicts + sources
- **Output (JSON):** `contradictions[]` — three detection channels:
 1. **Verifier disagreement:** A supports but B refutes (with both reasonings)
  2. **Source refutation:** a retrieved source directly contradicts a claim
  3. **Internal conflict:** two claims in the report contradict each other
- **Prompt strategy:** "You are a hostile fact-checking editor. Your job is to
  find every disagreement, refutation, and inconsistency. Report NONE if there
  genuinely are none — false alarms destroy trust."
- **Why a separate agent:** verification answers "is each claim true?";
  contradiction detection answers "does the picture hang together?" —
  different cognitive task, different prompt.

### 5.6 Writer (Report Compiler)
- **Input:** verified claims, verdicts, contradictions, sources
- **Output (JSON):** `{summary (3-4 sentences, with [n] citations),
  claim_report: [{text, status, confidence, citations, verification_note}]}`
- **Rules:** summary may only use verified/disputed claims; contradicted claims
  appear ONLY in a "⚠️ Contradictions & Corrections" section with the
  conflicting evidence shown; every factual sentence gets [n] citation markers.

### 5.7 Confidence Scorer (deterministic — NOT an LLM)
Computed in code from verification signals (calibration research shows
LLM self-reported confidence is unreliable):

```
confidence(claim) =
    40 × verifier_agreement        # 1.0 unanimous · 0.66 majority · 0.33 split
  + 25 × source_coverage           # min(sources_cited / 2, 1.0)
  + 20 × source_quality            # avg Tavily relevance score
  + 15 × specificity_ok            # 1.0 unless vague/hedged claim
  − 30 × contradiction_penalty     # 1.0 if flagged by contradiction detector
  clamped to [5, 98]               # never 0 (unverifiable ≠ impossible), never 100 (epistemic honesty)
```

Status mapping: ≥75 verified · 50-74 disputed · 25-49 unverified · <25 contradicted

**Trust score (report-level):** weighted mean of claim confidences, displayed
as a prominent gauge in the UI.

---

## 6. Pipeline State Machine & SSE Events

```
PLAN ──► RESEARCH ──► EXTRACT ──► VERIFY ──► CONTRADICTIONS ──► REPORT ──► DONE
                                      │
                              (3 verifiers parallel)
```

Every stage transition and notable action emits an SSE event:

| Event | Payload | UI effect |
|---|---|---|
| `stage` | `{stage, status: started\|done}` | pipeline tracker advances |
| `plan` | subtopics + queries | shows research plan |
| `sources` | source list | source cards appear |
| `claims` | atomic claims | claim chips appear |
| `verdict` | `{claim_id, verifier, stance}` | verdict badges fill in per claim (live!) |
| `contradiction` | contradiction detail | ⚠️ cards appear |
| `report` | final report JSON | report renders |
| `error` | message | toast + graceful state |
| `done` | run stats (time, calls, keys used) | completion state |

**Frontend:** `EventSource` on `/api/research/{id}/stream`. No framework —
vanilla JS + CSS. The live verdict badges filling in per claim is the demo
money-shot.

---

## 7. Tech Stack & Rationale

| Layer | Choice | Why |
|---|---|---|
| Backend | **FastAPI + uvicorn** (async) | Native SSE via StreamingResponse, async concurrency for parallel verifiers, auto API docs |
| LLM calls | **httpx async, custom client** | 5-key rotation + 429 backoff; no SDK dependency (gateway is Anthropic-compatible `/v1/messages`) |
| Search | **Tavily API** | AI-native search API, relevance-scored snippets, verified working key |
| Frontend | **Vanilla HTML/CSS/JS** | Zero build step, deploys anywhere, full control over the SSE demo UX |
| Storage | **JSON files per run** (`data/runs/`) | Revisit reports, zero infra, good enough for demo scale |
| Deploy | **Render** (free tier) | Static + FastAPI via `render.yaml`, public URL for submission |
| Config | **env vars** (12-factor) | `GATEWAY_KEYS`, `GATEWAY_BASE_URL`, `GATEWAY_MODEL`, `TAVILY_API_KEY` — secrets never in code on Render |

**Deliberate non-choices:** no LangChain/LangGraph (fixed pipeline, see §4),
no database (demo scale), no React (build-step risk in a 23h hackathon),
no vector DB (claim-level verification works on snippets; RAG over full
documents is documented future work).

---

## 8. API Design

```
POST /api/research          {topic} → {run_id}
GET  /api/research/{id}/stream   SSE event stream
GET  /api/research/{id}     final report JSON (also: revisit old runs)
GET  /api/runs              list of past runs (landing page history)
GET  /api/health liveness + config sanity (keys present, Tavily key present)
GET  /                      serves frontend (StaticFiles)
```

---

## 9. Resilience & Error Handling (industry-grade)

| Failure | Handling |
|---|---|
| Gateway 429 (2 rpm/key) | Round-robin across 5 keys + parse "try after N seconds" + sleep + retry (proven in our LiteLLM tests) |
| Gateway 5xx / network error | Retry next key, max 12 attempts total |
| One verifier agent fails | Proceed with 2 verdicts (majority still possible), mark reduced confidence |
| LLM returns invalid JSON | One nudge-retry ("return ONLY JSON"), then extract_json fallback parsing |
| Tavily down | Abort early with clear UI error (verification without sources is meaningless) |
| Claim extraction returns 0 claims | Retry once with simplified prompt, else error |
| Browser disconnects mid-SSE | Run continues server-side; report retrievable via GET by run_id |

**Observability:** every LLM call logged with agent name, key suffix, latency,
status — visible in server logs and summarized in the `done` SSE event
(total time, calls made, retries). This is the "transparent action log"
judges expect from an agent system.

---

## 10. Repository Layout

```
verifact/
├── backend/
│   ├── main.py              # FastAPI app, routes, SSE, static serving
│   ├── llm.py               # multi-key rotating LLM client + JSON extraction
│   ├── tavily_client.py     # async Tavily search
│   ├── agents.py            # 7 agents (planner→writer), each an async fn
│   ├── pipeline.py          # orchestrator: stages, concurrency, SSE emission
│   ├── scoring.py           # deterministic confidence formula
│   ├── models.py            # pydantic: Claim, Verdict, Source, Report...
│ └── requirements.txt     # fastapi uvicorn httpx pydantic
├── frontend/
│   ├── index.html           # SPA: input → pipeline tracker → report
│   ├── app.js               # EventSource SSE client + rendering
│   └── styles.css           # dark theme, confidence badges, gauges
├── data/runs/               # persisted run JSONs (gitignored)
├── render.yaml              # one-click Render deploy
├── Dockerfile               # reproducible image (also Render-compatible)
└── README.md                # architecture, run instructions, API docs
```

---

## 11. Testing & Validation Strategy

1. **Unit-level:** `scoring.py` formula (pure function — test all branches),
   `extract_json` against messy LLM outputs (fenced, prefixed, nested)
2. **Pipeline smoke test:** run topic *"History of the Eiffel Tower"*
   (well-documented → expect high confidence, zero contradictions)
3. **The misinformation trap (demo centerpiece):** run topic
   *"Albert Einstein won the Nobel Prize for his theory of relativity"*
   (common misconception — he won for the photoelectric effect). Expected:
   verifiers refute, contradiction detector fires, report shows
   ⚠️ correction with sources. **This single demo proves the entire value
   proposition** — a plain chatbot would confidently repeat the myth.
4. **Rate-limit soak:** 3 back-to-back runs to confirm key rotation holds
5. **Frontend E2E:** full browser flow — input → live stages → report render

---

## 12. Implementation Timeline (hackathon-critical path)

| Phase | Work | Est. |
|---|---|---|
| **A** | Backend core: llm.py (done), tavily_client.py (done), models.py (done), agents.py, scoring.py, pipeline.py, main.py | ~2.5h |
| **B** | Smoke test + fix loop on 2-3 real topics (incl. misinformation trap) | ~1h |
| **C** | Frontend: pipeline tracker + report UI + SSE wiring | ~2h |
| **D** | Polish: error states, loading UX, mobile-ish responsiveness | ~1h |
| **E** | Deploy: GitHub push + Render + verify public URL | ~45min |
| **F** | Submission assets: 6-7 slide PPT + demo script + README | ~1.5h |
| **Buffer** | Rate-limit surprises, deploy issues, final demo rehearsal | ~1.5h |

**Total ≈ 10h of focused build inside the 23h window.**

---

## 13. Submission Assets Plan

**PPT (6-7 slides):**
1. Title + problem ("AI confidently lies — here's the fix")
2. Solution architecture diagram (§4)
3. The adversarial verification panel (our differentiator, cite DebateCV)
4. Live demo screenshots (pipeline tracker + report + contradiction caught)
5. Confidence scoring methodology (the formula — shows rigor)
6. Tech stack + resilience (key rotation, degradation paths)
7. Future work (LangGraph dynamic re-research, full-document RAG, browser extension)

**Demo script (5-min video):**
1. (0:00) Show a chatbot confidently stating the Einstein misconception
2. (0:40) Run the same topic in VeriFact — live pipeline stages stream in
3. (2:00) Verdict badges flip to "refuted" — contradiction card appears
4. (3:00) Final report: corrected claim, citations, confidence scores
5. (4:00) Run a clean topic — show high-trust report
6. (4:30) Architecture recap + "every claim argued over by3 independent agents"

---

## 14. Risk Register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Gateway rate limits throttle the demo | Medium | 5-key rotation (built), pre-run the demo topics to warm caches, keep demo to 2 runs |
| LLM verifier produces shallow verdicts | Medium | Adversarial personas + mandatory source-ID citation + skeptic defaults to "insufficient" |
| Render free tier cold start (~30s) | High | Note in submission; warm the instance before recording video |
| Tavily quota | Low | Dev key limits are generous; search calls are few per run (6-8) |
| Model quality variance (free Qwen) | Medium | Structured JSON prompts + nudge-retry; pipeline degrades gracefully per agent |

---

## 15. Verification Checklist (definition of done)

- [ ] `POST /api/research` + SSE stream works end-to-end on a real topic
- [ ] Report has ≥6 claims, each with confidence score + ≥1 citation
- [ ] Misinformation-trap topic produces a refutation + contradiction card
- [ ] Frontend shows live stage progression + verdict badges filling in
- [ ] 3 consecutive runs succeed (key rotation proven under load)
- [ ] Deployed URL publicly accessible
- [ ] README + PPT + demo script complete
- [ ] No secrets in git (keys via env vars on Render)
