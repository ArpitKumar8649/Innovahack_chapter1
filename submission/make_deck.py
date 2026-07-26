#!/usr/bin/env python3
"""Generate the VeritasAI submission deck (10 slides, rose theme).

Usage: python3 make_deck.py  →  VeriFact_Deck.pptx
"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

BG = RGBColor(0x14, 0x06, 0x0B)       # rose-noir
CARD = RGBColor(0x24, 0x10, 0x19)     # rose panel
ACCENT = RGBColor(0xF4, 0x3F, 0x5E)   # rose-500
ACCENT2 = RGBColor(0xFB, 0x71, 0x85)  # rose-400
GREEN = RGBColor(0x3E, 0xCF, 0x8E)
RED = RGBColor(0xFF, 0x6B, 0x6B)
YELLOW = RGBColor(0xF5, 0xB9, 0x42)
TEXT = RGBColor(0xF7, 0xED, 0xF1)
MUTED = RGBColor(0xA5, 0x82, 0x8F)
LINE = RGBColor(0x4A, 0x24, 0x36)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def slide():
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = BG
    return s


def box(s, x, y, w, h):
    return s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))


def txt(tf, text, size=18, color=TEXT, bold=False, align=PP_ALIGN.LEFT, space_after=8):
    tf.word_wrap = True
    p = tf.paragraphs[0] if not tf.paragraphs[0].runs else tf.add_paragraph()
    p.text = text
    p.font.size = Pt(size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.alignment = align
    p.space_after = Pt(space_after)
    return p


def bullet(tf, text, size=16, color=TEXT, level=0):
    p = tf.add_paragraph()
    p.text = text
    p.font.size = Pt(size)
    p.font.color.rgb = color
    p.level = level
    p.space_after = Pt(6)
    return p


def title_bar(s, kicker, title):
    b = box(s, 0.7, 0.45, 12, 1.2)
    txt(b.text_frame, kicker, size=13, color=ACCENT, bold=True)
    txt(b.text_frame, title, size=34, color=TEXT, bold=True, space_after=0)


def card(s, x, y, w, h, heading, lines, head_color=ACCENT):
    shp = s.shapes.add_shape(1, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = CARD
    shp.line.color.rgb = LINE
    tf = shp.text_frame
    tf.word_wrap = True
    txt(tf, heading, size=15, color=head_color, bold=True)
    for ln in lines:
        bullet(tf, ln, size=12.5, color=MUTED)


# ============ SLIDE 1 — TITLE ============
s = slide()
b = box(s, 1.2, 1.3, 11, 3.6)
txt(b.text_frame, "⚖️  VERITASAI", size=54, color=TEXT, bold=True)
txt(b.text_frame, "The Research Court — Autonomous Multi-Agent Fact-Verification",
    size=24, color=ACCENT2, bold=True)
txt(b.text_frame,
    "Ten agents research, argue, verify, and cite in the open. Every claim is a "
    "cryptographically verifiable artifact — anchored to a Merkle tree you can "
    "check in your own browser.",
    size=17, color=MUTED)
b = box(s, 1.2, 5.2, 11, 1.6)
txt(b.text_frame, "InnovaHack Chapter 1  ·  Domain 3: Gen AI  ·  Problem Statement 1",
    size=15, color=MUTED)
txt(b.text_frame, "All 9 phases implemented · 100% trap catch-rate · 0% false alarms",
    size=14, color=GREEN, bold=True)

# ============ SLIDE 2 — PROBLEM ============
s = slide()
title_bar(s, "THE PROBLEM", "AI confidently lies. Users can't tell when.")
b = box(s, 0.7, 1.9, 12, 4.8)
tf = b.text_frame
bullet(tf, "• Generative AI hallucinates — and reports ~100% confidence while doing it "
           "(calibration research, Amazon/MIT 2024-25).", size=17)
bullet(tf, "• Single-model answers give no receipts: no sources, no dissent, no way to "
           "know what was verified — citations link URLs, not evidence.", size=17)
bullet(tf, "• Example: ask a chatbot “Did Einstein win the Nobel for relativity?” — "
           "many repeat the myth with full confidence.", size=17, color=YELLOW)
bullet(tf, "• The problem statement asks: can multiple AI agents check and challenge "
           "each other to produce trustworthy output?", size=17)
bullet(tf, "VeritasAI's answer: a self-adversarial court, not a single voice — "
           "and every receipt is math.", size=19, color=GREEN)

# ============ SLIDE 3 — ARCHITECTURE ============
s = slide()
title_bar(s, "THE SOLUTION", "The Research Court — a 10-stage pipeline")
flow = [
    ("1-2 · MURLI", "3 hypotheses +\nself-challenge →\ncounter-searches"),
    ("3 · EVIDENCE", "Serper web+scholar\n+news → Tavily\nfull-text, hashed"),
    ("4 · CLAIMS", "atomic claims\nanchored to\nchunks + dedup"),
    ("5 · COURT ×3", "span-gated quotes,\nHMAC-signed\nverdicts"),
    ("6 · DEBATE", "concede / rebut /\nhold → Judge rules\n+ records dissent"),
    ("7-10 · VERDICT", "trust engine,\nargument tree,\nMerkle root"),
]
x = 0.55
for name, desc in flow:
    shp = s.shapes.add_shape(1, Inches(x), Inches(2.3), Inches(1.9), Inches(1.7))
    shp.fill.solid()
    shp.fill.fore_color.rgb = CARD
    shp.line.color.rgb = ACCENT if "COURT" in name else LINE
    tf = shp.text_frame
    tf.word_wrap = True
    txt(tf, name, size=12.5, color=ACCENT if "COURT" in name else TEXT, bold=True,
        align=PP_ALIGN.CENTER)
    for ln in desc.split("\n"):
        bullet(tf, ln, size=11, color=MUTED).alignment = PP_ALIGN.CENTER
    if x < 10:
        arr = box(s, x + 1.88, 2.95, 0.25, 0.5)
        txt(arr.text_frame, "→", size=20, color=ACCENT, align=PP_ALIGN.CENTER, space_after=0)
    x += 2.12
b = box(s, 0.7, 4.5, 12, 2.4)
tf = b.text_frame
bullet(tf, "• Live pipeline: every stage streams to the browser over Server-Sent Events — "
           "hypotheses form, verdict badges flip, fabricated quotes get voided in real time.",
       size=15)
bullet(tf, "• Research-grounded: STORM (multi-perspective research), DebateCV SIGIR 2025 "
           "(debate-driven verification), FActScore (atomic claims), MBFC (source tiers).",
       size=15)
bullet(tf, "• Resilient: per-agent failure tolerance, JSON nudge-retry, graceful "
           "degradation, model auto-fallback on quota exhaustion.", size=15)

# ============ SLIDE 4 — MURLI ============
s = slide()
title_bar(s, "THE CORE INNOVATION", "Murli attacks its own findings first")
card(s, 0.6, 1.9, 6.0, 4.6, "SELF-ADVERSARIAL REASONING",
     ["Standard agents “yes-sir” the prompt.",
      "Murli generates 3 competing hypotheses,",
      "then for each asks:",
      "",
      "  “If this is WRONG, why would it be",
      "   wrong? What evidence would DISPROVE",
      "   it? Who disagrees, and on what",
      "   grounds?”",
      "",
      "…and issues those questions as REAL",
      "searches — not rhetorical questions."], ACCENT)
card(s, 6.9, 1.9, 5.8, 4.6, "WHAT THE COURT RECEIVES",
     ["• 3 hypotheses with prior plausibility",
      "• counter-evidence searches already run",
      "• self-identified weaknesses per hypothesis",
      "  (single-source dependence, confounders,",
      "   unverifiable premises)",
      "• full-text sources (Serper → Tavily),",
      "  chunked and SHA-256 hashed",
      "",
      "Hallucination is pre-filtered at the",
      "source — before verification begins."], GREEN)

# ============ SLIDE 5 — FEC ============
s = slide()
title_bar(s, "THE TRUST LAYER", "Citations as cryptographic artifacts (FEC)")
card(s, 0.6, 1.9, 6.0, 2.2, "SPAN GATE + SIGNED VERDICTS",
     ["Every verdict must quote an evidence span",
      "that exists VERBATIM in the corpus —",
      "fabricated quotes void the verdict.",
      "Verdicts are HMAC-signed per run."], RED)
card(s, 6.9, 1.9, 5.8, 2.2, "MERKLE ANCHORING",
     ["Every chunk hashed; the run's chunks form",
      "a Merkle tree. Each claim stores the proof",
      "path for its cited chunks — verified",
      "client-side via Web Crypto. No server trust."], ACCENT)
b = box(s, 0.7, 4.4, 12, 2.6)
tf = b.text_frame
bullet(tf, "Click any citation → the Evidence Inspector shows the exact quoted sentence "
           "highlighted in its source chunk, the authority tier, the content hash, and a "
           "Merkle proof verified in your browser.", size=15)
bullet(tf, "GET /api/reports/{id}/verify recomputes the root and re-checks every signature "
           "from stored data alone — the report proves itself.", size=15, color=GREEN)
bullet(tf, "“No more ‘I read it on the internet’ — every claim shows its receipt, "
           "and the receipt is math.”", size=16, color=YELLOW)

# ============ SLIDE 6 — MEASURED RESULTS ============
s = slide()
title_bar(s, "THE PROOF", "Measured, not vibes — the eval harness")
card(s, 0.6, 1.9, 6.0, 4.6, "50-CLAIM LABELED HARNESS (CI-GATED)",
     ["Label accuracy: 100%  (target ≥75%)",
      "Trap catch-rate:       100%  (target ≥90%)",
      "False-alarm rate:        0%  (target ≤10%)",
      "Error rate:              0%  (target ≤5%)",
      "Calibration (ECE):    0.309  (measured + shown)",
      "",
      "Einstein trap → premise REFUTED 3-0",
      "Great Wall trap → 6 fabricated quotes",
      "  caught and VOIDED by the span gate;",
      "  premise still REFUTED",
      "Clean topics → high trust, zero false alarms"], GREEN)
card(s, 6.9, 1.9, 5.8, 4.6, "PHASE 3 — MEMORY",
     ["Re-run speedup:  56% faster (55s → 24s)",
      "Claims reused from memory:  7/9",
      "Priors recalled at intake:  6",
      "",
      "PHASE 6 — SEMANTIC LAYER",
      "Counter-evidence retrieval surfaces",
      "opposing passages keyword search misses",
      "(contrastive embedding score)",
      "",
      "PHASE 7 — KNOWLEDGE GRAPH",
      "Circular citations detected in the",
      "provenance graph (blog-citing-blog)"], ACCENT)

# ============ SLIDE 7 — DEMO WALKTHROUGH ============
s = slide()
title_bar(s, "LIVE DEMO", "What the judges will see (3 minutes)")
b = box(s, 0.7, 1.8, 12, 5.0)
tf = b.text_frame
bullet(tf, "1. Open the landing page — the court is already in session (live transcript).",
       size=16)
bullet(tf, "2. Enter a trap: “The Great Wall of China is visible from space.”",
       size=16, color=YELLOW)
bullet(tf, "3. Watch the terminal: Murli forms 3 hypotheses, issues counter-searches,",
       size=16)
bullet(tf, "   publishes its own weaknesses. Evidence streams in, chunked and hashed.",
       size=16)
bullet(tf, "4. The chat space: three verifiers argue. The Skeptic disputes. Quotes that",
       size=16)
bullet(tf, "   don't exist in the corpus are VOIDED live — the span gate in action.",
       size=16, color=RED)
bullet(tf, "5. The verdict: premise REFUTED. Click a citation → Evidence Inspector shows",
       size=16)
bullet(tf, "   the exact quote, the hash, the Merkle proof verified in-browser.",
       size=16, color=GREEN)
bullet(tf, "6. The argument tree shows the Toulmin structure + weakest link.",
       size=16)
bullet(tf, "7. Re-run the same topic → 56% faster, priors recalled from memory.",
       size=16, color=ACCENT2)

# ============ SLIDE 8 — SCALABILITY & IMPACT ============
s = slide()
title_bar(s, "REAL-WORLD IMPACT", "Who needs this, and how it scales")
card(s, 0.6, 1.9, 6.0, 4.6, "WHO NEEDS THIS",
     ["Journalists & newsrooms — verify claims",
      "  before publishing, with receipts",
      "Researchers — literature-backed fact-checking",
      "  with provenance tracking",
      "Legal & compliance — auditable verification",
      "  trails (compliance mode: full reasoning)",
      "Platforms — white-label API for content",
      "  moderation at scale",
      "Education — teach critical thinking with",
      "  a system that shows its work"], ACCENT)
card(s, 6.9, 1.9, 5.8, 4.6, "BUSINESS MODEL (IMPLEMENTED)",
     ["Free / Pro ($49/mo) / Enterprise ($149/mo)",
      "Multi-tenant: API keys, usage metering,",
      "  plan-based daily limits",
      "White-label API v1 with rate limiting",
      "",
      "SCALE PATH",
      "Async pipeline (semaphore-bounded LLM calls)",
      "Workflow journal: retry / replay for",
      "  long-running investigations",
      "Prometheus metrics for observability",
      "Docker + nginx edge → horizontal scaling"], GREEN)

# ============ SLIDE 9 — TECH STACK ============
s = slide()
title_bar(s, "BUILD", "All 9 phases shipped — the full stack")
card(s, 0.6, 1.9, 6.0, 4.6, "TECH STACK",
     ["Frontend — React 18 + TypeScript + Vite",
      "  Web Crypto (client-side Merkle verification)",
      "Backend — FastAPI + asyncio, SSE streaming",
      "LLM — Qwen 3.5-plus (DashScope),",
      "  auto-fallback to qwen3.6-plus-2026-04-02",
      "Search — Serper.dev (web + scholar + news)",
      "Extraction — Tavily /extract (full text)",
      "Semantic — ChromaDB + bge-small-en-v1.5",
      "Graph — NetworkX (provenance + cycles)",
      "Storage — SQLite (journal + memory + tenants",
      "  + feedback + workflow)",
      "Deploy — Docker (multi-stage) / Render"], ACCENT)
card(s, 6.9, 1.9, 5.8, 4.6, "PHASES 0-9 (ALL IMPLEMENTED)",
     ["P0 — Foundation: Murli + evidence pipeline",
      "P1 — Full Court: span gate + signed verdicts",
      "P2 — Trust & Eval: harness + ECE + authority v2",
      "P3 — Memory & Debate: FTS5 + multi-turn + Judge",
      "P4 — React Frontend: landing + chat + terminal",
      "P5 — Argument Trees: Toulmin + radar + analytics",
      "P6 — Semantic: ChromaDB counter-evidence + dedup",
      "P7 — Knowledge Graph: provenance + circular",
      " citations + Expert Referee + API v1",
      "P8 — Durable Scale: workflow replay + metrics",
      "      + compliance mode + Sentry",
      "P9 — Enterprise: Red-Team + multi-tenant SaaS",
      "      + RLHF-style feedback loop"], ACCENT2)

# ============ SLIDE 10 — CLOSING ============
s = slide()
b = box(s, 1.2, 1.8, 11, 4.5)
txt(b.text_frame, "“Every claim shows its receipt,", size=36, color=TEXT, bold=True)
txt(b.text_frame, " and the receipt is math.”", size=36, color=ACCENT, bold=True)
txt(b.text_frame, "", size=12)
txt(b.text_frame,
    "VeritasAI doesn't just answer — it argues, verifies, and proves. "
    "Ten agents, one verdict, zero trust required in us.",
    size=18, color=MUTED)
txt(b.text_frame, "", size=12)
txt(b.text_frame,
    "100% trap catch-rate · 0% false alarms · 56% faster re-runs · "
    "Merkle-verified receipts · all 9 phases shipped",
    size=16, color=GREEN, bold=True)
b = box(s, 1.2, 6.0, 11, 1.0)
txt(b.text_frame, "InnovaHack Chapter 1  ·  Domain 3: Gen AI  ·  Problem Statement 1",
    size=14, color=MUTED)
txt(b.text_frame, "GitHub: github.com/ArpitKumar8649/Innovahack_chapter1",
    size=14, color=ACCENT2)

prs.save("VeriFact_Deck.pptx")
print(f"Saved VeriFact_Deck.pptx — {len(prs.slides._sldIdLst)} slides")
