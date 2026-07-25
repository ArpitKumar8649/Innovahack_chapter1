#!/usr/bin/env python3
"""Generate the VeriFact submission deck (6-7 slides, dark theme).

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
b = box(s, 1.2, 1.6, 11, 3.2)
txt(b.text_frame, "🛡️  VERIFACT", size=54, color=TEXT, bold=True)
txt(b.text_frame, "Autonomous Multi-Agent Research & Fact-Verification System",
    size=24, color=ACCENT, bold=True)
txt(b.text_frame,
    "Every claim argued over by three independent AI agents — "
    "with citations and a confidence score you can trust.",
    size=17, color=MUTED)
b = box(s, 1.2, 5.4, 11, 1.2)
txt(b.text_frame, "InnovaHack Chapter 1  ·  Domain 3: Gen AI  ·  Problem Statement 1",
    size=15, color=MUTED)
txt(b.text_frame, "Team submission — Round 1", size=13, color=MUTED)

# ============ SLIDE 2 — PROBLEM ============
s = slide()
title_bar(s, "THE PROBLEM", "AI confidently lies. Users can't tell when.")
b = box(s, 0.7, 1.9, 12, 4.8)
tf = b.text_frame
bullet(tf, "• Generative AI hallucinates — and reports ~100% confidence while doing it "
           "(calibration research, Amazon/MIT 2024-25).", size=17)
bullet(tf, "• Single-model answers give no receipts: no sources, no dissent, no way to "
           "know what was verified.", size=17)
bullet(tf, "• Example: ask a chatbot “Did Einstein win the Nobel for relativity?” — "
           "many repeat the myth with full confidence.", size=17, color=YELLOW)
bullet(tf, "• The problem statement asks: can multiple AI agents check and challenge "
           "each other to produce trustworthy output?", size=17)
bullet(tf, "VeriFact's answer: an adversarial panel, not a single voice.", size=19,
       color=GREEN)

# ============ SLIDE 3 — ARCHITECTURE ============
s = slide()
title_bar(s, "THE SOLUTION", "A 7-agent pipeline with an adversarial core")
flow = [
    ("1 · PLANNER", "topic → subtopics +\n8 diverse search queries"),
    ("2 · RESEARCHER", "Tavily web search →\n12 deduped sources"),
    ("3 · EXTRACTOR", "atomic claim\ndecomposition"),
    ("4 · VERIFIERS ×3", "adversarial panel,\nparallel, majority vote"),
    ("5 · CONTRADICTION", "disagreements &\nrefutations surfaced"),
    ("6 · WRITER", "citation-backed report\n+ trust score"),
]
x = 0.55
for name, desc in flow:
    shp = s.shapes.add_shape(1, Inches(x), Inches(2.3), Inches(1.9), Inches(1.7))
    shp.fill.solid()
    shp.fill.fore_color.rgb = CARD
    shp.line.color.rgb = ACCENT if "VERIFIER" in name else RGBColor(0x23, 0x2E, 0x47)
    tf = shp.text_frame
    tf.word_wrap = True
    txt(tf, name, size=12.5, color=ACCENT if "VERIFIER" in name else TEXT, bold=True,
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
           "verdict badges flip per claim in real time.", size=15)
bullet(tf, "• Research-grounded: Stanford STORM (multi-perspective research), DebateCV "
           "SIGIR 2025 (debate-driven verification), FActScore (atomic claims).", size=15)
bullet(tf, "• Resilient: per-agent failure tolerance, JSON nudge-retry, graceful degradation.",
       size=15)

# ============ SLIDE 4 — ADVERSARIAL PANEL ============
s = slide()
title_bar(s, "THE DIFFERENTIATOR", "Three verifiers. Three lenses. Majority vote.")
card(s, 0.6, 1.9, 3.9, 2.6, "A · EVIDENTIALIST",
     ["“What do the sources literally say?”",
      "Supports a claim ONLY if a source",
      "explicitly states it. Never infers."], GREEN)
card(s, 4.7, 1.9, 3.9, 2.6, "B · SKEPTIC",
     ["“How could this be wrong?”",
      "Actively attacks each claim; defaults",
      "to insufficient without strong evidence."], RED)
card(s, 8.8, 1.9, 3.9, 2.6, "C · CONTEXTUALIST",
     ["“Is this precise and current?”",
      "Checks dates, numbers, scope —",
      "flags outdated or overstated claims."], YELLOW)
b = box(s, 0.7, 4.8, 12, 2.2)
tf = b.text_frame
bullet(tf, "Why it matters: “Why Do Multi-Agent LLM Systems Fail?” (2025) found verifier "
           "superficiality is the #1 failure mode — task-focused verifiers gave +15.6% accuracy.",
       size=15)
bullet(tf, "Anti-superficiality rule: every verdict MUST cite source IDs. "
           "Evidence-free verdicts are structurally invalid.", size=15, color=GREEN)
bullet(tf, "≥2 support → verified · ≥2 refute → contradicted · mixed → disputed · "
           "all insufficient → unverified.", size=15)

# ============ SLIDE 5 — CONFIDENCE SCORING ============
s = slide()
title_bar(s, "RIGOR", "Confidence is computed — never self-reported")
b = box(s, 0.7, 1.9, 12, 1.4)
txt(b.text_frame,
    "LLMs report ~100% confidence even when wrong. VeriFact derives confidence "
    "deterministically from verification signals:", size=16, color=MUTED)
card(s, 0.6, 3.2, 7.6, 3.4, "THE FORMULA",
     ["confidence = 40 × verifier agreement",
      "               + 25 × source coverage",
      "               + 20 × source quality (relevance)",
      "               + 15 × specificity",
      "               − 30 × contradiction penalty",
      "",
      "clamped to [5, 98] — never 0 (unverifiable ≠ false),",
      "never 100 (epistemic honesty)"], ACCENT)
card(s, 8.5, 3.2, 4.2, 3.4, "STATUS BANDS",
     ["≥ 75  →  verified",
      "50-74 →  disputed",
      "25-49 →  unverified",
      "< 25  →  contradicted",
      "",
      "Report trust score =",
      "mean of claim confidences"], GREEN)

# ============ SLIDE 6 — DEMO ============
s = slide()
title_bar(s, "THE PROOF", "The misinformation trap — caught live")
b = box(s, 0.7, 1.8, 12, 1.1)
txt(b.text_frame, "Query: “Albert Einstein won the Nobel Prize for his theory of relativity”",
    size=17, color=YELLOW, bold=True)
card(s, 0.6, 3.0, 6.0, 3.6, "WHAT HAPPENED",
     ["1. Extractor surfaced the premise itself as Claim 1",
      "2. All three verifiers: A=refute B=refute C=refute",
      "3. Claim 1 → CONTRADICTED (95% confidence it is false)",
      "4. Report opens: “Contrary to the common claim…",
      "   he won for the law of the photoelectric effect [1][5]”",
      "5. Trust score 92 across 8 verified claims"], RED)
card(s, 6.9, 3.0, 5.8, 3.6, "WHY JUDGES SHOULD CARE",
     ["A plain chatbot repeats the myth confidently.",
      "VeriFact refutes it with receipts.",
      "",
      "Same pipeline on clean topics (Eiffel Tower,",
      "mRNA vaccines) → high-trust reports,",
      "zero false alarms."], GREEN)

# ============ SLIDE 7 — TECH + FUTURE ============
s = slide()
title_bar(s, "BUILD & WHAT'S NEXT", "Tech stack and roadmap")
card(s, 0.6, 1.9, 6.0, 4.6, "TECH STACK",
     ["Backend — FastAPI + asyncio, SSE streaming",
      "LLM — Qwen (DashScope, OpenAI-compatible)",
      "Search — Tavily API",
      "Frontend — vanilla JS/CSS (zero build step)",
      "Deploy — Docker + Render (render.yaml)",
      "",
      "~2,500 lines · 7 agents · fully async",
      "Typical run: 30-40 seconds end-to-end"], ACCENT)
card(s, 6.9, 1.9, 5.8, 4.6, "FUTURE WORK",
     ["Dynamic re-research: low-confidence claims",
      "trigger targeted follow-up searches (LangGraph)",
      "Full-document RAG over uploaded PDFs",
      "Browser extension: verify any article in-place",
      "Claim history: track how facts change over time",
      "Multi-model panel: different LLMs per verifier",
      "for true model diversity"], ACCENT2)

prs.save("VeriFact_Deck.pptx")
print(f"Saved VeriFact_Deck.pptx — {len(prs.slides._sldIdLst)} slides")
