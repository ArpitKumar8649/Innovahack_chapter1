# VeritasAI — Demo Script (3 minutes)

> For the InnovaHack Chapter 1 judge panel. Open the app at
> `http://localhost:3000` (or the deployed URL) before starting.

---

## 0:00 — Open on the landing page

"The court is already in session."

Point to the live transcript card on the landing page — agents arguing,
verdict badges flipping. This is not a mockup; it's the real SSE stream.

---

## 0:20 — The trap

Type into the court: **"The Great Wall of China is visible from space."**

"A plain chatbot will repeat this myth with full confidence. Watch what
happens when ten agents get hold of it."

---

## 0:30 — Murli (hypotheses + self-challenge)

Point to the chat space as Murli speaks:

- "Murli just formed three competing hypotheses — not one answer."
- "Now it's attacking its own findings: 'what evidence would DISPROVE this?'"
- "Those counter-questions just became real Serper searches."
- "And there — it published its own weaknesses before the court even convened."

---

## 1:00 — Evidence + span gate (the wow moment)

As verdicts stream in:

- "Three verifiers are now arguing independently. The Skeptic is trying to
  destroy every claim."
- **Wait for a voided quote** (terminal shows "span gate voided N
  unverifiable quote(s)"): "That quote the verifier just cited? It doesn't
  exist in the corpus. The span gate caught it and voided the verdict —
  fabricated citations can't pollute the result."

---

## 1:30 — The verdict + Evidence Inspector

- "Premise: REFUTED. Three-zero."
- Click a citation chip → Evidence Inspector opens: "That's the exact quoted
  sentence, highlighted in its source chunk. The SHA-256 hash. And the Merkle
  proof — verified in my browser, right now, with zero trust in our server."

---

## 1:50 — Argument tree + trust radar

- "The argument tree shows the Toulmin structure — which evidence supports
  which hypothesis, and the weakest link is flagged."
- "The trust radar: five axes, all computed, never LLM self-reported."

---

## 2:10 — Memory (re-run)

Re-run the same topic:

- "Same topic again. Watch the terminal: 'memory recall: 6 prior findings.'
  Seven of nine claims reused from memory. Fifty-six percent faster."

---

## 2:30 — The numbers

Flip to the landing page's live numbers section:

- "These aren't marketing. They're pulled from the running API: claims
  learned, domains classified, calibration error. A system that publishes
  its own calibration error is more trustworthy than one that hides it."

---

## 2:45 — Close

"Every claim shows its receipt. And the receipt is math.

One hundred percent trap catch-rate. Zero false alarms. All nine phases
shipped. Thank you."

---

## Backup: if a run is slow

- The Dubai floods topic is a good alternative (rich evidence, clean run).
- The Einstein trap ("Einstein won the Nobel for relativity") is the
  fastest trap — fewer sources, quick REFUTED.
- If the LLM is rate-limited, the system auto-falls back to the backup
  model — mention it: "That fallback just happened live. The system healed
  itself."
