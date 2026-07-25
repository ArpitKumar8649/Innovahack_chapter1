#!/usr/bin/env python3
"""Generate the VeritasAI submission deck (7 slides, dark theme).

Usage: python3 make_deck.py  →  VeriFact_Deck.pptx
"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

BG = RGBColor(0x0A, 0x0E, 0x17)
CARD = RGBColor(0x14, 0x1B, 0x2D)
ACCENT = RGBColor(0x4F, 0x8C, 0xFF)
ACCENT2 = RGBColor(0x7C, 0x5C, 0xFF)
GREEN = RGBColor(0x2E, 0xCC, 0x8F)
RED = RGBColor(0xFF, 0x5D, 0x6C)
YELLOW = RGBColor(0xF5, 0xB9, 0x42)
TEXT = RGBColor(0xE8, 0xEC, 0xF4)
MUTED = RGBColor(0x8B, 0x96, 0xAD)

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
    shp = s.shapes.add_shape(1, Inches(x), Inches(y), Inches(w), Inches(h))  # rectangle
    shp.fill.solid()
    shp.fill.fore_color.rgb = CARD
    shp.line.color.rgb = RGBColor(0x23, 0x2E, 0x47)
    tf = shp.text_frame
    tf.word_wrap = True
    txt(tf, heading, size=15, color=head_color, bold=True)
    for ln in lines:
        bullet(tf, ln, size=12.5, color=MUTED)


# ============ SLIDE 1 — TITLE ============
s = slide()
b = box(s, 1.2, 1.5, 11, 3.4)
txt(b.text_frame, "⚖️  VERITASAI", size=54, color=TEXT, bold=True)
txt(b.text_frame, "The Research Court — Autonomous Multi-Agent Fact-Verification",
    size=24, color=ACCENT, bold=True)
txt(b.text_frame,
    "Every claim argued over by three adversarial agents, grounded in exact "
    "source quotes, and anchored to a Merkle tree you can verify in your browser.",
    size=17, color=MUTED)
b = box(s, 1.2, 5.4, 11, 1.2)
txt(b.text_frame, "InnovaHack Chapter 1  ·  Domain 3: Gen AI  ·  Problem Statement 1",
    size=15, color=MUTED)
txt(b.text_frame, "Phase 0-1 of the 18-month master plan", size=13, color=MUTED)

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
    ("4 · CLAIMS", "atomic claims\nanchored to\nevidence chunks"),
    ("5 · COURT ×3", "span-gated quotes,\nHMAC-signed\nverdicts"),
    ("6-7 · SWEEPS", "typed hallucination\n+ contradiction\ndetection"),
    ("8-10 · VERDICT", "trust engine,\nMerkle root,\nSQLite journal"),
]
x = 0.55
for name, desc in flow:
    shp = s.shapes.add_shape(1, Inches(x), Inches(2.3), Inches(1.9), Inches(1.7))
    shp.fill.solid()
    shp.fill.fore_color.rgb = CARD
    shp.line.color.rgb = ACCENT if "COURT" in name else RGBColor(0x23, 0x2E, 0x47)
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
           "degradation to snippet-only mode if extraction fails.", size=15)

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
card(s, 0.6, 1.9, 6.0, 2.2, "SPANN GATE + SIGNED VERDICTS",
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

# ============ SLIDE 6 — DEMO ============
s = slide()
title_bar(s, "THE PROOF", "The misinformation trap — caught live")
b = box(s, 0.7, 1.8, 12, 1.1)
txt(b.text_frame, "Query: “Albert Einstein won the Nobel Prize for his theory of relativity”",
    size=17, color=YELLOW, bold=True)
card(s, 0.6, 3.0, 6.0, 3.6, "WHAT HAPPENED",
     ["1. Murli formed 3 hypotheses + counter-searches",
      "2. Extractor surfaced the premise as Claim 1",
      "3. All three verifiers: A=refute B=refute C=refute",
      "4. Claim 1 → REFUTED with exact quotes from",
      "   nobelprize.org, span-validated + signed",
      "5. Report opens with the correction, not the myth",
      "6. Attestation: Merkle root ✓, all signatures ✓"], RED)
card(s, 6.9, 3.0, 5.8, 3.6, "WHY JUDGES SHOULD CARE",
     ["A plain chatbot repeats the myth confidently.",
      "VeritasAI refutes it with verifiable receipts.",
      "",
      "Measured: Great Wall trap → 6 fabricated",
      "verifier quotes caught and voided by the",
      "span gate; premise still REFUTED.",
      "Clean topics → high-trust, zero false alarms."], GREEN)

# ============ SLIDE 7 — TECH + ROADMAP ============
s = slide()
title_bar(s, "BUILD & WHAT'S NEXT", "Phase 0-1 shipped · 18-month arc planned")
card(s, 0.6, 1.9, 6.0, 4.6, "TECH STACK (SHIPPED)",
     ["Backend — FastAPI + asyncio, SSE streaming",
      "LLM — Qwen (DashScope, provider-agnostic layer)",
      "Search — Serper.dev (web + scholar + news)",
      "Extraction — Tavily /extract (full text)",
      "Storage — SQLite journal + re-attestation",
      "Frontend — vanilla JS + Web Crypto",
      "",
      "~2,900 lines · 10-stage court · fully async",
      "Typical run: 60-90 seconds end-to-end"], ACCENT)
card(s, 6.9, 1.9, 5.8, 4.6, "ROADMAP (MASTER PLAN)",
     ["P2 — Trust engine v2 + FEVER/SciFact eval",
     "       harness in CI (prove it scientifically)",
      "P3 — Claim memory + multi-turn debate rounds",
      "P4 — Argument trees + Debate Theater UI",
      "P5 — ChromaDB: counter-evidence retrieval",
      "P6 — Neo4j provenance graph + expert referee",
      "P7 — Temporal durable orchestration",
      "P8 — Red-team agent + white-label API"], ACCENT2)

prs.save("VeriFact_Deck.pptx")
print(f"Saved VeriFact_Deck.pptx — {len(prs.slides._sldIdLst)} slides")
