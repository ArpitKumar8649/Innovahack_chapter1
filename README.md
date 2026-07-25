# 🛡️ VeriFact — Autonomous Multi-Agent Research & Fact-Verification System

**InnovaHack Chapter 1 · Domain 3: Gen AI · Problem Statement 1**

> A multi-agent pipeline where one agent researches a topic, three adversarial
> agents cross-verify every claim against multiple sources, a contradiction
> detector hunts for disagreements and hallucinations, and a final agent
> compiles a citation-backed report — with a confidence score for each claim.

## The problem

Generative AI tools are powerful researchers but struggle with hallucination
and unverified claims. Ask a chatbot *"Did Einstein win the Nobel Prize for
relativity?"* and it will often confidently repeat the myth. VeriFact's answer
comes only after three independent agents have argued about it — and it shows
you the receipts.

## Architecture

```
Topic ──► 1. PLANNER          decompose topic → diverse search queries
        ──► 2. RESEARCHER      Tavily web search → deduplicated sources
        ──► 3. EXTRACTOR       atomic claim decomposition (FActScore-style)
        ──► 4. VERIFIER PANEL  3 adversarial agents in parallel:
               A · Evidentialist — "what do the sources literally say?"
               B · Skeptic       — "how could this be wrong?" (default: insufficient)
               C · Contextualist — "is this precise and current?"
        ──► 5. CONTRADICTION   verifier disagreements · source refutations ·
               DETECTOR        internal conflicts between claims
        ──► 6. WRITER          citation-backed report + trust score
```

All stages stream live to the browser over Server-Sent Events — you watch
verdict badges flip per claim as the panel deliberates.

### Why three verifiers?

Single-verifier systems are superficial (see *"Why Do Multi-Agent LLM Systems
Fail?"*, 2025 — task-focused verifiers yield +15.6% accuracy). VeriFact's
panel is inspired by **DebateCV** (SIGIR 2025): opposing lenses + majority
vote. Every verdict must cite source IDs — evidence-free verdicts are
structurally invalid.

### Confidence scoring (deterministic, not self-reported)

LLMs report ~100% confidence even when wrong (calibration research, 2024-25),
so confidence is **computed** from verification signals:

```
40 × verifier agreement  + 25 × source coverage
20 × source quality      + 15 × specificity
− 30 × contradiction penalty        (clamped to [5, 98])
```

Status: ≥75 verified · 50-74 disputed · 25-49 unverified · <25 contradicted.
Report-level **trust score** = mean of claim confidences.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | FastAPI + asyncio, Server-Sent Events |
| LLM | Qwen (DashScope, OpenAI-compatible Responses API) |
| Search | Tavily API |
| Frontend | Vanilla JS + CSS (zero build step) |
| Deploy | Docker / Render (`render.yaml`) |

## Run locally

```bash
./run.sh                    # → http://localhost:8000
```

Or with Docker:

```bash
docker build -t verifact . && docker run -p 8000:8000 verifact
```

Environment variables (optional — dev defaults are built in):
`DASHSCOPE_API_KEY`, `TAVILY_API_KEY`, `LLM_MODEL`.

## API

| Endpoint | Purpose |
|---|---|
| `POST /api/research` | `{topic}` → `{run_id}` |
| `GET /api/research/{id}/stream` | SSE live event stream |
| `GET /api/research/{id}` | final report JSON |
| `GET /api/runs` | past investigations |
| `GET /api/health` | liveness + config |

## Research foundations

- Stanford STORM — multi-perspective research → cited article generation
- DebateCV (SIGIR 2025) — debate-driven claim verification
- FActScore — atomic fact decomposition for fine-grained verification
- "Why Do Multi-Agent LLM Systems Fail?" (2025) — verifier superficiality
- LLM confidence calibration research (Amazon/MIT, 2024-25)
