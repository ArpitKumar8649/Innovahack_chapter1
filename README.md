# ⚖️ VeritasAI — The Research Court

**InnovaHack Chapter 1 · Domain 3: Gen AI · Problem Statement 1**

> A transparent *court of intelligent agents* that research, argue, verify,
> and cite in front of you. Every claim in a VeritasAI report is a
> **verifiable artifact**: grounded in exact source quotes, scored by a
> deterministic trust engine, stress-tested by agents instructed to destroy
> it, and anchored to a Merkle tree you can verify in your own browser.

---

## The problem

Generative AI tools are powerful researchers but struggle with hallucination
and unverified claims. Ask a chatbot *"Did Einstein win the Nobel Prize for
relativity?"* and it will often confidently repeat the myth. There is no
transparent, auditable way to know *why* an AI believes what it says.

VeritasAI replaces black-box answers with a **court of adversarial agents**
that argue in the open. Every verdict quotes its exact source span, is scored
by a deterministic formula (never LLM self-reported confidence), and is
anchored to a Merkle tree you can verify client-side.

---

## What's built — all 9 phases

| Phase | What | Status |
|---|---|---|
| **0 — Foundation** | Murli agent (3 hypotheses + self-adversarial counter-searches), Serper→Tavily full-text pipeline, SHA-256 content hashing | ✅ Measured |
| **1 — Full Court** | Span-gated verifier panel (fabricated quotes voided), HMAC-signed verdicts, typed hallucination detector (7 types), 6-status epistemic taxonomy, SQLite journal | ✅ Measured |
| **2 — Trust & Eval** | 50-claim labeled eval harness + CI gates, source authority v2 (LLM fallback + recency), ECE calibration, multi-model A/B scaffolding | ✅ 100% accuracy |
| **3 — Memory & Debate** | Cross-run claim memory (FTS5), multi-turn debate (concede/rebut/hold + Judge), content-hash index | ✅ 56% faster re-runs |
| **4 — React Frontend** | React + TypeScript + Vite SPA: landing page, live agent chat, terminal, Evidence Inspector, debate transcript | ✅ |
| **5 — Argument Trees** | Toulmin argument tree, Trust Radar (5 axes), weakest-link detection, engagement analytics | ✅ |
| **6 — Semantic Layer** | ChromaDB + bge-small-en-v1.5, contrastive counter-evidence retrieval, semantic claim dedup | ✅ |
| **7 — Knowledge Graph** | NetworkX provenance graph, circular-citation detection, Expert Referee portal, public API v1 | ✅ |
| **8 — Durable Scale** | Workflow journal (checkpoint/retry/replay), Prometheus metrics, compliance mode, Sentry integration | ✅ |
| **9 — Enterprise** | Red-Team agent (5 attack vectors), multi-tenant SaaS (API keys, usage metering, plan limits), RLHF-style feedback loop | ✅ |

---

## Architecture — the 10-stage court

```
Topic ──► 1. INTAKE           memory recall: prior findings on this topic
        ──► 2. MURLI           3 competing hypotheses + self-adversarial counter-searches
        ──► 3. EVIDENCE        Serper web+scholar+news → Tavily full-text extract
                               → chunked, SHA-256 hashed, semantically indexed
        ──► 4. CLAIMS          atomic claims anchored to evidence chunks
                               + semantic dedup against prior runs
        ──► 5. CACHE CHECK     freshly-verified claims reused from memory (56% speedup)
        ──► 6. VERIFIER ×3     adversarial lenses, SPAN-GATED exact quotes:
               A · Evidentialist   fabricated quote → verdict VOID
               B · Skeptic         verdicts HMAC-signed (non-repudiation)
               C · Contextualist
        ──► 7. DEBATE          split verdicts → round 2 (concede/rebut/hold)
                               → Judge rules if no consensus, records dissent
        ──► 8. AUDIT           typed hallucination sweep (7 types)
                               + contradiction detector + provenance graph
        ──► 9. SCORING         deterministic trust formula, 6 epistemic statuses
                               + argument tree + trust radar + weakest link
        ──► 10. SYNTHESIS      citation-backed report + Merkle root
                               + red-team probe + memory write + journal
```

All stages stream live to the browser over Server-Sent Events.

### Fact-Embedded Citations (FEC) — citations as verifiable artifacts

| Layer | What it proves |
|---|---|
| **Content hashing** | every evidence chunk carries SHA-256 + retrieval timestamp |
| **Merkle anchoring** | each run's chunks form a Merkle tree; every claim stores the proof path — verifiable client-side via Web Crypto, no server trust |
| **Signed verdicts** | each verdict is HMAC-signed with a per-run key (published with the report) — agents can't be silently re-quoted |
| **Verification endpoint** | `GET /api/reports/{id}/verify` recomputes the root and re-checks every signature from stored data alone |

### The span gate (anti-hallucination)

Every verifier verdict must quote an evidence span that exists verbatim in
the corpus. A fabricated quote **voids the verdict** — it counts as
`insufficient`, never as support or refutation. Measured: the gate caught
and voided **6 fabricated quotes** in the Great Wall trap run.

### Trust Engine (deterministic, never self-reported)

LLMs report ~100% confidence even when wrong (calibration research, 2024-25),
so confidence is **computed**:

```
30 × verifier agreement   + 20 × evidence coverage
20 × source authority     + 10 × source diversity
10 × specificity          + 10 × recency
− 35 × contradiction penalty  − 20 × hallucination flag
clamped to [5, 98]
```

Six epistemic statuses: `ESTABLISHED · SUPPORTED · CONTESTED · REFUTED ·
UNVERIFIABLE · OUTDATED`.

---

## Measured results

### Phase 2 — evaluation harness (50 labeled claims, CI-gated)

| Metric | Result | Target |
|---|---|---|
| Label accuracy | **100%** | ≥75% |
| Trap catch-rate | **100%** | ≥90% |
| False-alarm rate | **0%** | ≤10% |
| Error rate | **0%** | ≤5% |
| ECE (calibration) | **0.309** | measured + displayed |

### Phase 0-1 — live runs

| Run | Hypotheses | Full-text sources | Span gate | Attestation |
|---|---|---|---|---|
| Dubai floods attribution | 3 + 6 weaknesses | 15/15 | 0 fabricated | Merkle ✓, sigs ✓ |
| Einstein Nobel trap | 3 + 6 weaknesses | 9/9 | 0 fabricated | premise **REFUTED** 3-0 |
| Great Wall trap | 3 + 6 weaknesses | 15/15 | 6 fabricated **voided** | premise **REFUTED** |

### Phase 3 — memory

| Metric | Result |
|---|---|
| Re-run speedup (cached topic) | **56% faster** (55s → 24s) |
| Claims reused from memory | 7/9 |
| Priors recalled at intake | 6 |

---

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | React 18 + TypeScript + Vite, Web Crypto (Merkle verification) |
| Backend | FastAPI + asyncio, Server-Sent Events |
| LLM | Qwen 3.5-plus (DashScope), auto-fallback to qwen3.6-plus-2026-04-02 |
| Search | Serper.dev (web + scholar + news) |
| Extraction | Tavily `/extract` (full text, ≤20 URLs/batch) |
| Semantic | ChromaDB + bge-small-en-v1.5 (fastembed, ONNX) |
| Graph | NetworkX (provenance + circular-citation detection) |
| Storage | SQLite (journal + memory + tenants + feedback + workflow) |
| Deploy | Docker (multi-stage: Node build → nginx edge + uvicorn) / Render |

---

## Run locally

```bash
./run.sh
# → API:      http://localhost:8000
# → Frontend: http://localhost:3000   ← open this
```

Or with Docker:

```bash
docker build -t veritasai . && docker run -p 8080:8080 veritasai
# → http://localhost:8080
```

Environment variables (optional — dev defaults are built in):
`DASHSCOPE_API_KEY`, `TAVILY_API_KEY`, `SERPER_API_KEY`, `LLM_MODEL`.

---

## API

| Endpoint | Purpose |
|---|---|
| `POST /api/research` | `{topic}` → `{run_id}` |
| `GET /api/research/{id}/stream` | SSE live event stream |
| `GET /api/research/{id}` | final report JSON |
| `GET /api/reports/{id}/verify` | cryptographic re-attestation (FEC) |
| `GET /api/reports/{id}/compliance` | full reasoning chain (compliance mode) |
| `GET /api/runs` | past investigations |
| `GET /api/memory` | cross-run memory stats |
| `GET /api/calibration` | ECE calibration data |
| `GET /api/semantic` | semantic index stats |
| `GET /api/analytics` | report engagement analytics |
| `POST /api/engagement` | record dwell time / inspector opens |
| `POST /api/flag` | expert referee flag → harness test case |
| `GET /api/flags` | pending expert flags |
| `POST /api/redteam/{id}` | red-team probe a completed report |
| `GET /api/tenants` | tenant registry |
| `POST /api/tenants` | create tenant (API key + plan) |
| `GET /api/tenants/{id}/usage` | usage metering |
| `GET /api/feedback/policy` | feedback loop → policy recommendations |
| `GET /api/workflows/{id}/replay` | workflow replay (durable execution) |
| `POST /v1/verify` | public API v1 (API key auth, rate-limited) |
| `GET /metrics` | Prometheus metrics |
| `GET /api/health` | liveness + config |

---

## Project structure

```
├── web/                        # React + TypeScript frontend
│   └── src/
│       ├── components/
│       │   ├── landing/        # Landing page (hero, agents, receipts, numbers, flow, footer)
│       │   ├── court/          # Court view (chat, terminal, report, inspector, tree, radar)
│       │   ├── auth/           # Sign in / Sign up (glass card, 3D tilt, light beams)
│       │   └── pricing/        # Pricing (WebGL shader, glass cards, ripple buttons)
│       ├── hooks/              # useRun (SSE state machine)
│       ├── lib/                # api client, agents, merkle (Web Crypto)
│       └── styles/             # tokens, global, app, auth, pricing CSS
├── verifact/
│   └── backend/                # FastAPI backend
│       ├── main.py             # API routes
│       ├── pipeline.py         # 10-stage orchestrator
│       ├── murli.py            # self-adversarial research agent
│       ├── court.py            # verifier panel + debate + span gate
│       ├── evidence.py         # extraction + chunking + FEC hashing
│       ├── scoring.py          # trust engine + radar
│       ├── argument.py         # Toulmin argument tree + weakest link
│       ├── semantic.py         # ChromaDB counter-evidence + dedup
│       ├── graph.py            # NetworkX provenance + circular citations
│       ├── memory.py           # cross-run memory (FTS5)
│       ├── journal.py          # SQLite run journal + attestation
│       ├── workflow.py         # durable workflow (checkpoint/retry/replay)
│       ├── metrics.py          # Prometheus counters/histograms
│       ├── compliance.py       # full reasoning trace
│       ├── redteam.py          # adversarial report probing
│       ├── tenants.py          # multi-tenant SaaS + usage metering
│       ├── feedback.py         # RLHF-style feedback loop
│       └── llm.py              # provider-agnostic LLM client
├── eval/                       # evaluation harness (trap suite + FEVER + ECE)
├── deploy/                     # nginx.conf + entrypoint.sh
├── submission/                 # deck + demo script
├── Dockerfile                  # multi-stage: Node build → nginx + uvicorn
├── render.yaml                 # Render deployment config
├── run.sh                      # local dev launcher
└── VERITASAI_MASTER_PLAN.md    # full 18-month roadmap
```

---

## Scalability & real-world impact

**Who needs this:**
- **Journalists & newsrooms** — verify claims before publishing, with receipts
- **Researchers** — literature-backed fact-checking with provenance tracking
- **Legal & compliance** — auditable verification trails (compliance mode)
- **Platforms** — white-label API for content moderation at scale

**Business model (implemented):**
- Free / Pro ($49/mo) / Enterprise ($149/mo) tiers with usage metering
- White-label API v1 with API key auth and rate limiting
- Multi-tenant architecture with plan-based daily limits

**Scale path:**
- Async pipeline handles concurrent runs (semaphore-bounded LLM calls)
- Workflow journal enables retry/replay for long-running investigations
- Prometheus metrics for production observability
- Docker + nginx edge for horizontal scaling behind a load balancer

---

## Research foundations

- Stanford STORM — multi-perspective research (Murli's sub-question expansion)
- DebateCV (SIGIR 2025) — debate-driven claim verification
- FActScore — atomic fact decomposition
- "Why Do Multi-Agent LLM Systems Fail?" (2025) — verifier superficiality
- LLM confidence calibration research (Amazon/MIT, 2024-25)
- MBFC methodology — source credibility tiers
- Provenance-enhanced statements (2024) — provenance as epistemic signal

The full 18-month roadmap is in `VERITASAI_MASTER_PLAN.md`.
