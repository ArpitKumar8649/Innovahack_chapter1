# VeriFact — 5-Minute Demo Script (optional video)

**Setup before recording:** app open at the public URL, dark theme,
one completed run visible in history (Einstein trap).

---

**0:00 — Hook (20s)**
Open a plain chatbot. Ask: *"Did Einstein win the Nobel Prize for the theory
of relativity?"* Show it answering confidently (often wrong or hedging).
Voiceover: *"This is the problem. AI research tools are confident — but
confidence isn't truth."*

**0:20 — Introduce VeriFact (30s)**
Switch to VeriFact. Show the landing page and the agent badges.
Voiceover: *"VeriFact doesn't answer — it investigates. Seven specialized
agents: a planner, a researcher, a claim extractor, three adversarial
verifiers, a contradiction detector, and a report writer."*

**0:50 — The live pipeline (90s)**
Type the same Einstein claim. Hit Verify. Walk through the live stages as
they stream in:
- *"The planner decomposes the topic into subtopics and search angles…"*
- *"The researcher pulls sources from the live web via Tavily…"*
- *"The extractor decomposes the material into atomic claims — note it
  surfaces the premise itself as Claim 1…"*
- *"Now the adversarial panel: three verifiers with different lenses —
  evidentialist, skeptic, contextualist — run in parallel. Watch the
  verdict badges flip…"*

**2:20 — The catch (60s)**
Point at Claim 1's badges: A=✗ B=✗ C=✗.
Voiceover: *"All three independently refute the premise. The contradiction
detector logs it. And the report opens with a correction — not the myth:
'Contrary to the common claim… he won for the law of the photoelectric
effect' — with clickable citations."*
Scroll the report: trust gauge, per-claim confidence bars, sources grid.

**3:20 — Clean topic (40s)**
Run *"History of the Eiffel Tower"* (or open from history).
Voiceover: *"On well-documented topics, the panel reaches consensus — high
trust score, zero false alarms. The system is calibrated: it argues when it
should, and agrees when it should."*

**4:00 — Architecture + rigor (40s)**
Show the architecture slide (or README).
Voiceover: *"Confidence is never self-reported by the model — it's computed
from verifier agreement, source coverage, source quality, and contradiction
penalties. The design is grounded in 2025 research: DebateCV's adversarial
verification, FActScore's atomic claims, and the multi-agent failure-modes
paper, which showed task-focused verifiers add 15 points of accuracy."*

**4:40 — Close (20s)**
Voiceover: *"VeriFact: every claim argued over by three independent agents
before you read it. Built in 24 hours with FastAPI, Qwen, and Tavily.
Thank you."*

---

## Submission checklist

- [ ] Deployed URL accessible (codespace public port / Render)
- [ ] PPT (6-7 slides) — `submission/VeriFact_Deck.pptx`
- [ ] Optional 5-min video (script above)
- [ ] Drive folder with **public viewing access** ("Anyone with the link can view")
- [ ] Google Form submission: https://forms.gle/J41yUTNsgbBUHhk37
- [ ] Form fields: Team Name · Team Leader · Team Members · Track = "Domain 3: Gen AI — PS1"
- [ ] Submit well before **26 July 2026, 10:00 AM IST**
- [ ] One submission only, by the Team Leader
