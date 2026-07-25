# VeritasAI — 5-Minute Demo Script (optional video)

**Setup before recording:** app open at the public URL, dark theme, one
completed run visible in history (Einstein trap). Have a plain chatbot tab
open beside it.

---

**0:00 — Hook (20s)**
Open a plain chatbot. Ask: *"Did Einstein win the Nobel Prize for the theory
of relativity?"* Show it answering confidently (often wrong or hedging).
Voiceover: *"This is the problem. AI research tools are confident — but
confidence isn't truth."*

**0:20 — Introduce VeritasAI (30s)**
Switch to VeritasAI. Show the landing page and the agent bench.
Voiceover: *"VeritasAI doesn't answer — it convenes a court. A self-adversarial
research agent, three adversarial verifiers, a hallucination auditor, a
contradiction detector, and a synthesis writer. And every claim it makes
carries a cryptographic receipt."*

**0:50 — The live pipeline (90s)**
Type the same Einstein claim. Hit "Put on trial". Walk through the live
stages as they stream in:
- *"Murli forms three competing hypotheses — including the claim itself and
  its strongest negation — and publishes a weakness for each…"*
- *"It issues its own counter-searches: Serper across web, scholar, and news,
  then Tavily extracts the full text of every source — chunked and SHA-256
  hashed…"*
- *"The extractor decomposes the corpus into atomic claims anchored to exact
  evidence chunks — note the premise itself is Claim 1…"*
- *"Now the court: three verifiers with different lenses — evidentialist,
  skeptic, contextualist — in parallel. Watch the badges flip…"*

**2:20 — The catch (60s)**
Point at Claim 1's badges: A=✗ B=✗ C=✗.
Voiceover: *"All three independently refute the premise — each with an exact
quote from the corpus. And here's the guardrail: if a verifier fabricates a
quote, the span gate voids its verdict on the spot."*
Open the **Evidence Inspector** on a claim:
- *"This is the receipt: the exact quoted sentence, highlighted in its source
  chunk, the source's authority tier, the content hash — and a Merkle proof
  verified right here in the browser. No trust in our server required."*
Point at the attestation badge: *"Merkle root matched, all verdict signatures
valid. The report proves itself."*

**3:20 — Clean topic (40s)**
Open *"History of the Eiffel Tower"* from history (or run it live).
Voiceover: *"On a clean topic the court reaches consensus — high-trust claims,
zero false alarms, and genuinely contested interpretations stay marked
CONTESTED instead of being flattened into a fake certainty."*

**4:00 — The vision (60s)**
Voiceover: *"This is Phase 0-1 of an 18-month plan: the research court with
cryptographic citations. Next: a FEVER-benchmarked evaluation harness that
proves accuracy scientifically, multi-turn debate rounds, claim memory across
runs, semantic counter-evidence retrieval, and a provenance graph that catches
blogs citing blogs. The destination: the world's most trustworthy search
engine — where every claim shows its receipt, and the receipt is math."*

---

**Backup beats** (if time allows):
- Show the Great Wall run from history: *"six fabricated verifier quotes were
  caught and voided by the span gate — the premise was still refuted."*
- `GET /api/reports/{id}/verify` in a browser tab: machine-readable
  attestation, recomputed from stored data alone.

---

## Submission checklist

- [ ] Deployed URL accessible (codespace public port / Render)
- [ ] PPT (7 slides) — `submission/VeriFact_Deck.pptx`
- [ ] Optional 5-min video (script above)
- [ ] Drive folder with **public viewing access** ("Anyone with the link can view")
- [ ] Google Form submission: https://forms.gle/J41yUTNsgbBUHhk37
- [ ] Form fields: Team Name · Team Leader · Team Members · Track = "Domain 3: Gen AI — PS1"
- [ ] Submit well before **26 July 2026, 10:00 AM IST**
- [ ] One submission only, by the Team Leader
