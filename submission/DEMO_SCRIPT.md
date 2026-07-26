# VeritasAI — 5-Minute Demo Video Script

> **Format:** Narration over screen recording. Read the quoted lines aloud.
> [BRACKETED] = what to show on screen. Keep a steady, confident pace.
> Total runtime: ~5:00. Practice once with a timer before recording.

---

## 0:00 – 0:35 · THE PROBLEM (35 seconds)

[ON SCREEN: A plain chatbot (ChatGPT/any) being asked "Did Einstein win the
Nobel Prize for relativity?" — it answers "Yes" confidently.]

**Say:**

"Ask any chatbot whether Einstein won the Nobel Prize for relativity. It will
tell you yes — confidently, fluently, and completely wrong. He won it for the
photoelectric effect.

This is the core problem with generative AI: it hallucinates, and it reports
near-hundred-percent confidence while doing it. Calibration research from MIT
and Amazon in twenty twenty-four confirmed this — LLMs are maximally
confident even when maximally wrong.

For a user, there is no way to know what was verified and what was invented.
Citations link URLs, not evidence. There is no dissent. There is no receipt."

---

## 0:35 – 1:20 · THE SOLUTION (45 seconds)

[ON SCREEN: VeritasAI landing page — the live transcript card with agents
arguing, the moving-dot animation.]

**Say:**

"VeritasAI replaces the single black-box answer with a transparent court of
intelligent agents. Ten agents — a self-adversarial researcher, three rival
verifiers, a judge, an auditor, an editor, and a writer — research, argue,
verify, and cite in the open.

Every claim in a VeritasAI report is a verifiable artifact. It is grounded in
exact source quotes, scored by a deterministic trust engine — never
LLM self-reported confidence — and stress-tested by agents explicitly
instructed to destroy it.

And every receipt is anchored to a Merkle tree that you can verify in your
own browser. No trust in our server required. The receipt is math."

---

## 1:20 – 2:20 · THE ARCHITECTURE (60 seconds)

[ON SCREEN: The court view. Walk through the 3-column Debate Theater as you
narrate. Point to each column.]

**Say:**

"Let me walk you under the hood. This is the Debate Theater — our three-column
command center.

[Point to LEFT column — The Bench]
On the left, the Bench. Ten agents, each with a single job and a built-in
bias. You can see their live status, what they're currently doing, and their
stance confidence meters filling in as verdicts land.

[Point to CENTER — The Argument Graph]
In the center, the Argument Graph. The query sits on the stand. Murli — our
cognitive scientist — forms three competing hypotheses, then attacks its own
findings before the court even convenes. It asks 'what evidence would disprove
this?' and issues those as real searches. Claims orbit their hypothesis as
exhibits. Green edges support, red edges refute, yellow-dashed means the
evidence is still insufficient.

[Point to RIGHT — Evidence Drawer]
On the right, the Evidence Drawer. Click any claim and you see the exact
verdicts, the verbatim quotes with span validation, source credibility tiers,
and semantic counter-evidence that keyword search would have missed.

[Scroll down to the pipeline / terminal]
The pipeline runs ten stages: intake with memory recall, hypothesis
generation, evidence requisition through Serper and Tavily, atomic claim
extraction, a span-gated verifier panel where fabricated quotes are voided,
multi-turn debate with a Judge who rules on splits and records the dissent,
a typed hallucination sweep, contradiction detection, deterministic trust
scoring, and synthesis with Merkle anchoring.

Everything streams live over Server-Sent Events. You watch the argument form
in real time."

---

## 2:20 – 3:50 · LIVE DEMO (90 seconds)

[ON SCREEN: Type into the court input.]

**Say:**

"Let's put a claim on trial. I'll type: 'The Great Wall of China is visible
from space.' A plain chatbot repeats this myth. Watch what ten agents do with
it."

[Type and submit. Let the pipeline run. Narrate as events stream:]

"Murli just formed three hypotheses and is attacking its own findings — those
counter-questions just became real Serper searches across web, scholar, and
news.

Evidence is streaming in — full-text extraction, chunked, SHA-256 hashed.

Now the verifiers are arguing. The Skeptic is trying to destroy every claim.
And there — [wait for span-gate void] — that quote the verifier just cited
doesn't exist in the corpus. The span gate caught it and voided the verdict.
Fabricated citations cannot pollute the result."

[Scroll to the verdict / report]

"Premise: REFUTED. Three-zero. Every verifier cited an exact span from a real
source.

[Click a citation → Evidence Inspector]
Click any citation and the Evidence Inspector opens: the exact quoted sentence
highlighted in its source chunk, the content hash, and the Merkle proof —
verified in my browser right now, with zero trust in our server.

[Point to the argument tree / trust radar]
The argument tree shows the Toulmin structure with the weakest link flagged.
The trust radar plots five axes — all computed, never self-reported.

[Re-run the same topic]
Same topic again. Watch: 'memory recall — six prior findings.' Seven of nine
claims reused from memory. Fifty-six percent faster. The system learns."

---

## 3:50 – 4:35 · IMPACT & SCALABILITY (45 seconds)

[ON SCREEN: Landing page live numbers section, then the pricing page.]

**Say:**

"Why does this matter? Because trustworthy AI research is not a nice-to-have —
it's a prerequisite for AI in journalism, law, medicine, and compliance.

Our evaluation harness — fifty labeled claims, CI-gated — measures one hundred
percent trap catch-rate, zero false alarms, and publishes its own calibration
error. A system that shows its own uncertainty is more trustworthy than one
that hides it.

For scalability: the pipeline is fully async, semaphore-bounded for concurrent
runs. The workflow journal enables retry and replay. Prometheus metrics are
exposed for production observability. And the deployment is containerized —
Docker with an nginx edge, horizontally scalable behind a load balancer.

The business model is implemented: Free, Pro at forty-nine a month, and
Enterprise at one-forty-nine — with multi-tenant API keys, usage metering,
and a white-label API. This isn't a prototype; it's a product skeleton ready
for real users."

---

## 4:35 – 5:00 · CLOSE (25 seconds)

[ON SCREEN: The landing page hero, or the verified attestation badge.]

**Say:**

"VeritasAI doesn't just answer — it argues, verifies, and proves.

Ten agents. One verdict. Zero trust required in us.

One hundred percent trap catch-rate. Zero false alarms. All nine phases
shipped. Frontend on Vercel, backend on Render, source on GitHub.

Every claim shows its receipt. And the receipt is math.

Thank you."

---

## Production notes

- **Pre-warm the backend** before recording (free tier sleeps). Run one
  trial 5 minutes before you start recording so the first demo run is fast.
- **Have a completed run ready** in history as a backup — if the live run
  is slow, click into the cached one and narrate over it.
- **Pacing:**130–140 words per minute. This script is ~720 words of
  narration ≈ 5:00–5:20 at natural pace. Trim the architecture section
  first if you're running long.
- **The wow moments** (in priority order): span-gate voiding a fabricated
  quote, the Merkle proof verifying in-browser, the 56% memory speedup.
  Make sure the camera lingers on each.
- **Judging criteria coverage:**
  - Presentation (10): clear 4-part structure, live demo, easy to follow
  - Scalability & Impact (10): async pipeline, Docker, metrics, business
    model, real-world verticals named
  - Documentation (5): mention GitHub + README + deployed links in the close
