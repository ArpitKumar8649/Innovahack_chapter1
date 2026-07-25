# PHASE 4 — Debate Theater · React Frontend
## Implementation Plan

> **Goal:** replace the vanilla-JS prototype with a crafted React + TypeScript
> SPA. Three surfaces: a **landing page** (long, detailed, alive), **the Court**
> (a chat space where the agents argue in real time), and a **Terminal** (live
> backend logs). All driven by the existing SSE API — no backend changes needed
> beyond serving the built assets.

---

## 0. What we're reusing (the backend is done)

The FastAPI backend (`verifact/backend/main.py`) already emits everything over
SSE. The frontend is a pure consumer:

| Endpoint | Purpose |
|---|---|
| `POST /api/research` | start a run → `{run_id}` |
| `GET /api/research/{id}/stream` | **SSE** live events (the heart) |
| `GET /api/research/{id}` | final report JSON |
| `GET /api/reports/{id}/verify` | cryptographic re-attestation |
| `GET /api/runs` | past investigations |
| `GET /api/memory` | cross-run memory stats |
| `GET /api/calibration` | ECE |
| `GET /api/health` | liveness + model |

**SSE events** (from `pipeline.py`): `stage`, `log`, `priors`, `hypotheses`,
`sources`, `claims`, `cache`, `verdict`, `debate`, `hallucination`,
`contradiction`, `score`, `report`, `done`, `error`, `end`.

The client-side Merkle proof (Web Crypto) is re-implemented in TS to mirror
`evidence.py` exactly.

---

## 1. Architecture

```
web/                          ← new Vite + React + TS app
├── index.html
├── vite.config.ts            ← dev proxy /api → :8000
├── tsconfig.json
├── package.json
└── src/
    ├── main.tsx
    ├── App.tsx               ← router: Landing | Court
    ├── styles/
    │   ├── tokens.css        ← design tokens (color, type, motion)
    │   └── global.css
    ├── types.ts              ← API/SSE/report types
    ├── lib/
    │   ├── api.ts            ← REST calls
    │ ├── sse.ts            ← EventSource wrapper (typed events)
    │   ├── merkle.ts         ← sha256 + verifyProof (Web Crypto)
    │   └── agents.ts         ← agent roster: id, name, role, lens, color
    ├── hooks/
    │   └── useRun.ts         ← the run state machine (SSE → state)
    └── components/
        ├── landing/          ← Landing page sections
        │   ├── Landing.tsx
        │   ├── CourtOpening.tsx   ← opens on the court in session
        │   ├── AgentRoster.tsx
        │   ├── ReceiptStack.tsx   ← FEC layers, receipt aesthetic
        │   ├── LiveNumbers.tsx    ← memory/calibration/health
        │   └── HowItWorks.tsx
        ├── court/            ← the run experience
        │   ├── CourtView.tsx      ← layout shell (chat | terminal | report)
        │   ├── StageTrack.tsx     ← pipeline progress
        │   ├── ChatSpace.tsx      ← agent dialogue (the star)
        │   ├── AgentMessage.tsx
        │   ├── Terminal.tsx       ← live log console
        │   ├── ReportPanel.tsx    ← trust gauge, claims, verdicts
        │   ├── ClaimCard.tsx
        │   ├── TrustGauge.tsx
        │   └── EvidenceInspector.tsx  ← modal w/ in-browser Merkle proof
        └── ui/               ← shared primitives (Badge, Pill, Section…)
```

**State model** (`useRun`): a reducer that folds SSE events into:
`{ stage, logs[], messages[], claims[], sources[], hypotheses[], report,
   attestation, memoryStats, status }`.
Chat messages and terminal lines are both *derived from the same event stream*
— a `verdict` becomes an agent message *and* a terminal line. This keeps the
chat and terminal perfectly in sync with the backend.

---

## 2. The Court chat space (the centerpiece)

Each agent gets an identity (name, role, lens, accent color). As events stream
in, they're translated into dialogue:

| Event | Becomes |
|---|---|
| `hypotheses` | **Murli** posts the competing theories + self-challenges |
| `sources` | **Researcher** reports the evidence haul (count, best tier) |
| `claims` | **Extractor** lists the atomic claims |
| `verdict` | **Verifier A/B/C** each speak: stance + reasoning + quoted span |
| `debate` (round>1) | the same verifiers **concede / rebut / hold**, visibly |
| `debate` (judge) | **The Judge** rules, dissent on the record |
| `cache` | **Memory** notes reused findings |
| `hallucination` | **Auditor** flags a typed failure |
| `contradiction` | **Editor** calls out a conflict |
| `report` | **Writer** delivers the summary |

Messages render as a vertical feed: avatar (colored sigil), name + role,
stance chip, the quoted evidence span in a blockquote, and a span-valid/voided
mark. Auto-scroll, subtle entrance animation, "…is typing" shimmer while a
stage is active.

## 3. The Terminal

A mono-font console fed by `log` + `stage` events (and a mirror of key verdict
lines). Timestamped, color-coded by level, auto-scroll, blinking cursor. Reads
like a real pipeline log — this is the "receipts" the brief demands.

##4. The landing page

Opens **on the court in session**, not a generic hero: a live-styled mock of the
chat + terminal mid-debate, with the product name and one line. Then:

1. **The Bench** — the agents, each with lens + what it attacks
2. **The Receipt Stack** — FEC as layered receipts: content hash → Merkle root
   → signed verdicts → public verify endpoint (receipt/docket aesthetic)
3. **Live numbers** — pulled from `/api/memory`, `/api/calibration`, `/api/health`
   (claims learned, ECE, model) — real, not marketing
4. **How a trial runs** — the 10-stage flow
5. **Enter the court** → routes to the Court with a topic input

## 5. Design system

- **Type:** a distinctive display face (e.g. "Fraunces" or "Space Grotesk") for
  headings + a readable body ("Inter" is banned as the sole family — pair it).
  Terminal uses a true mono ("JetBrains Mono" / "IBM Plex Mono").
- **Color:** dark courtroom palette — deep ink navy base, **gold** (the bench),
  a **verdict green**, a **refute red**, a **doubt amber**. Avoid the
  indigo/violet/pink gradient cliché and single-neon-on-black.
- **Motion:** scroll-reveals on landing sections, message entrance animations,
  gauge sweep, live "in session" pulse. Respect `prefers-reduced-motion`.
- **Layout:** asymmetric, layered backgrounds (subtle grid/texture), strong
  type-size contrast. No centered hero trio, no equal feature-card rows.

## 6. Dev / build / deploy

- **Dev:** `vite` on :3000 with `server.proxy` → `http://localhost:8000`
  (replaces `serve_frontend.py` for the new app).
- **Build:** `vite build` → `web/dist`.
- **Serve:** backend stays API-only. `run.sh` serves `web/dist` on :3000 (a
  tiny static server that proxies `/api`), mirroring production.
- **Docker/nginx:** `deploy/nginx.conf` serves `web/dist` and proxies `/api`
  (update the `root`).

## 7. Exit criteria (Phase 4)

- [ ] `vite build` passes with zero TS errors
- [ ] Full run (intake → verdict) works end-to-end in React
- [ ] Landing page, chat space, and terminal all render **live** data
- [ ] Attestation badge passes against the real `/verify` endpoint
- [ ] Client-side Merkle proof verifies in-browser (Web Crypto)
- [ ] Old vanilla `frontend/` retired (kept until React is proven, then removed)

## 8. Order of work

1. Scaffold + config (vite, ts, proxy)
2. `types.ts` + `lib/*` + `hooks/useRun.ts` (the data spine)
3. Court view: ChatSpace + Terminal + StageTrack (live, against real SSE)
4. ReportPanel + ClaimCard + TrustGauge + EvidenceInspector
5. Landing page sections
6. Dev/build/deploy wiring; retire vanilla frontend
7. Verify end-to-end; commit + push
