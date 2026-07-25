# ⚖️ VeritasAI — The Research Court

**InnovaHack Chapter 1 · Domain 3: Gen AI · Problem Statement 1**

> A transparent *court of intelligent agents* that research, argue, verify,
> and cite in front of you. Every claim in a VeritasAI report is a
> **verifiable artifact**: grounded in exact source quotes, scored by a
> deterministic trust engine, stress-tested by agents instructed to destroy
> it, and anchored to a Merkle tree you can verify in your own browser.

## The problem

Generative AI tools are powerful researchers but struggle with hallucination
and unverified claims. Ask a chatbot *"Did Einstein win the Nobel Prize for
relativity?"* and it will often confidently repeat the myth. VeritasAI's
answer comes only after a self-adversarial research agent has attacked its
own hypotheses and three independent verifiers have argued about every claim
— and it shows you the receipts, cryptographically.

## Architecture — the 10-stage court

```
Topic ──► 1. MURLI · hypotheses     3 competing "theories of truth" + priors
        ──► 2. MURLI · self-challenge "if this is wrong, why?" → REAL counter-searches
        ──► 3. EVIDENCE REQUISITION   Serper web+scholar+news → Tavily full-text
                                      extract → chunked, SHA-256 hashed (FEC)
        ──► 4. CLAIM EXTRACTION       atomic claims anchored to evidence chunks
        ──► 5. VERIFIER PANEL ×3      adversarial lenses, SPAN-GATED exact quotes:
               A · Evidentialist      a verdict whose quote isn't verbatim in the
               B · Skeptic            corpus is VOID (catches hallucinated citations)
               C · Contextualist      verdicts HMAC-signed (non-repudiation)
        ──► 6. HALLUCINATION SWEEP    typed: entity · relation · number · date ·
                                      extrapolation · unsupported · staleness
        ──► 7. CONTRADICTION SWEEP    verifier disagreements · source refutations
        ──► 8. TRUST ENGINE           deterministic formula, 6 epistemic statuses
        ──► 9. SYNTHESIS              citation-backed report + Merkle root
        ──► 10. JOURNAL               SQLite run store, cryptographic re-attestation
```

All stages stream live to the browser over Server-Sent Events — you watch
hypotheses form, verdict badges flip, and the span gate void fabricated
quotes in real time.

### Murli — the self-adversarial research agent

Standard agents "yes-sir" the prompt. Murli plays devil's advocate against
itself *before the court convenes*: for each hypothesis it asks "what
evidence would disprove this?" and issues those questions as **real
searches** (Serper web + scholar + news), then extracts full text (Tavily)
and publishes its own **self-identified weaknesses**. Hallucination is
pre-filtered at the source.

### Fact-Embedded Citations (FEC) — citations as verifiable artifacts

| Layer | What it proves |
|---|---|
| **Content hashing** | every evidence chunk carries SHA-256 + retrieval timestamp |
| **Merkle anchoring** | each run's chunks form a Merkle tree; every claim stores the proof path for its cited chunks — verifiable client-side via Web Crypto, no server trust |
| **Signed verdicts** | each verdict is HMAC-signed with a per-run key (published with the report) — agents can't be silently re-quoted |
| **Verification endpoint** | `GET /api/reports/{id}/verify` recomputes the root and re-checks every signature from stored data alone |

Click any evidence chip in the UI → the **Evidence Inspector** shows the
exact quoted sentence highlighted in its source chunk, the source's
authority tier, the content hash, and a Merkle proof verified **in your
browser**.

### The span gate (anti-hallucination)

Every verifier verdict must quote an evidence span that exists verbatim in
the corpus (exact, ellipsis-fragment, or 8-gram fuzzy match). A fabricated
quote **voids the verdict** — it counts as `insufficient`, never as support
or refutation. Measured in live runs: the gate catches LLM-fabricated
citations and downgrades them to honest `UNVERIFIABLE` instead of letting
them pollute the verdict.

### Trust Engine (deterministic, never self-reported)

LLMs report ~100% confidence even when wrong (calibration research,
2024-25), so confidence is **computed**:

```
30 × verifier agreement   + 20 × evidence coverage
20 × source authority     + 10 × source diversity
10 × specificity          + 10 × recency
− 35 × contradiction penalty  − 20 × hallucination flag
clamped to [5, 98]
```

Six epistemic statuses: `ESTABLISHED · SUPPORTED · CONTESTED · REFUTED ·
UNVERIFIABLE · OUTDATED`. Source authority uses MBFC-inspired tiers
(primary/peer-reviewed → social/UGC).

## Measured results (exit-criteria harness)

| Run | Hypotheses | Full-text sources | Span gate | Attestation |
|---|---|---|---|---|
| Dubai floods attribution | 3 + 6 weaknesses | 15/15 | 0 fabricated quotes | Merkle ✓, sigs ✓ |
| Einstein Nobel trap | 3 + 6 weaknesses | 9/9 | 0 fabricated quotes | Merkle ✓, sigs ✓ — premise **REFUTED** |
| Great Wall trap | 3 + 6 weaknesses | 15/15 | 6 fabricated quotes **voided** | Merkle ✓, sigs ✓ — premise **REFUTED** |

## Tech stack

| Layer | Choice |
|---|---|
| Backend | FastAPI + asyncio, Server-Sent Events |
| LLM | Qwen (DashScope, OpenAI-compatible Responses API) |
| Search | Serper.dev (web + scholar + news) |
| Extraction | Tavily `/extract` (full text, ≤20 URLs/batch) |
| Storage | SQLite run journal + cryptographic re-attestation |
| Frontend | Vanilla JS + CSS + Web Crypto (zero build step) |
| Deploy | Docker / Render (`render.yaml`) |

## Run locally

```bash
./run.sh                    # → http://localhost:8000
```

Or with Docker:

```bash
docker build -t veritasai . && docker run -p 8000:8000 veritasai
```

Environment variables (optional — dev defaults are built in):
`DASHSCOPE_API_KEY`, `TAVILY_API_KEY`, `SERPER_API_KEY`, `LLM_MODEL`.

## API

| Endpoint | Purpose |
|---|---|
| `POST /api/research` | `{topic}` → `{run_id}` |
| `GET /api/research/{id}/stream` | SSE live event stream |
| `GET /api/research/{id}` | final report JSON |
| `GET /api/reports/{id}/verify` | cryptographic re-attestation (FEC L2-L4) |
| `GET /api/runs` | past investigations |
| `GET /api/health` | liveness + config |

## Research foundations

- Stanford STORM — multi-perspective research (Murli's sub-question expansion)
- DebateCV (SIGIR 2025) — debate-driven claim verification
- FActScore — atomic fact decomposition
- "Why Do Multi-Agent LLM Systems Fail?" (2025) — verifier superficiality
- LLM confidence calibration research (Amazon/MIT, 2024-25)
- MBFC methodology — source credibility tiers
- Provenance-enhanced statements (2024) — provenance as epistemic signal

The full 18-month roadmap (multi-turn debate, FEVER evaluation harness,
ChromaDB semantic layer, Neo4j provenance graph, expert referee portal) is
in `VERITASAI_MASTER_PLAN.md`. This submission is **Phase 0-1**: foundation,
evidence pipeline, and the full court v1.
