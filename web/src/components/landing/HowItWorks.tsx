import { Reveal } from "../ui/Reveal";

const STEPS = [
  { n: "01", t: "Intake", d: "Your claim goes on trial. Memory recalls prior findings on the topic." },
  { n: "02", t: "Hypotheses", d: "Murli frames 2–3 competing theories of truth — then attacks its own." },
  { n: "03", t: "Evidence", d: "Serper web/scholar/news → Tavily full-text extract. Chunked, hashed, indexed." },
  { n: "04", t: "Claims", d: "The corpus is decomposed into atomic claims, each anchored to chunks." },
  { n: "05", t: "Court ×3", d: "Evidentialist, Skeptic, Contextualist issue independent verdicts — with exact quotes." },
  { n: "06", t: "Deliberate", d: "Split verdicts go to round 2: concede, rebut, or hold. A Judge rules if needed." },
  { n: "07", t: "Audit", d: "Typed hallucination sweep + contradiction detector comb the findings." },
  { n: "08", t: "Verdict", d: "Deterministic trust score, epistemic status, Merkle-anchored report." },
];

export function HowItWorks() {
  return (
    <section className="flow wrap" id="how">
      <Reveal>
        <span className="eyebrow">the trial</span>
        <h2 className="display section-title">How a claim becomes a verdict.</h2>
      </Reveal>
      <ol className="flow-list">
        {STEPS.map((s, i) => (
          <Reveal key={s.n} delay={(i % 4) * 70}>
            <li className="flow-item">
              <span className="flow-no mono">{s.n}</span>
              <div>
                <div className="flow-title">{s.t}</div>
                <p className="flow-desc">{s.d}</p>
              </div>
            </li>
          </Reveal>
        ))}
      </ol>
    </section>
  );
}
