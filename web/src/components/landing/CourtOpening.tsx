import { Link } from "react-router-dom";
import { Reveal } from "../ui/Reveal";
import { AGENTS } from "../../lib/agents";
import { Avatar } from "../ui/Avatar";

/** A scripted slice of a real transcript — opens the page on the court mid-debate. */
const SAMPLE = [
  { agent: "verifier-b", stance: "refute", text: "I dispute C4 — the 330 m figure. Source [2] says 320 m.", quote: "…the tower stood 300 metres tall at completion in 1889…", chunk: "C2.1" },
  { agent: "verifier-a", stance: "support", text: "Conceding the 1889 height; [5] confirms 330 m only after the antenna was added.", quote: "…with its broadcasting antenna the structure reaches 330 metres…", chunk: "C5.0" },
  { agent: "judge", stance: "support", text: "Ruling: the claim is precise only with the antenna. Dissent recorded.", quote: "", chunk: "" },
];

export function CourtOpening() {
  return (
    <section className="opening wrap">
      <div className="opening-copy">
        <Reveal>
          <span className="eyebrow">◈ autonomous multi-agent fact-verification</span>
          <h1 className="display opening-title">
            A court of agents<br />that argues every claim<br /><em>into receipts.</em>
          </h1>
          <p className="opening-sub">
            VeritasAI convenes a bench of adversarial agents — a self-doubting
            researcher, three rival verifiers, a judge — and streams the whole
            trial. Every verdict quotes its exact source span, anchored by a
            Merkle root you can check in your own browser.
          </p>
          <div className="opening-cta">
            <Link to="/court" className="btn btn-gold">Enter the court →</Link>
            <a href="#how" className="btn">How a trial runs</a>
          </div>
        </Reveal>
      </div>

      <Reveal delay={150} className="opening-stage">
        <div className="stage-card">
          <div className="stage-card-head">
            <span className="live-dot" /> <span className="mono">in session — claim C4</span>
          </div>
          {SAMPLE.map((s, i) => {
            const a = AGENTS[s.agent as keyof typeof AGENTS];
            return (
              <div key={i} className="sample-msg" style={{ ["--agent-color" as string]: a.color, animationDelay: `${i * 0.25}s` }}>
                <Avatar agent={a} size={32} />
                <div>
                  <div className="sample-head">
                    <b style={{ color: a.color }}>{a.name}</b>
                    <span className={`stance-chip st-${s.stance}`}>{s.stance}</span>
                  </div>
                  <p>{s.text}</p>
                  {s.quote && <blockquote className="agent-quote">“{s.quote}” <span className="quote-chunk mono">{s.chunk}</span></blockquote>}
                </div>
              </div>
            );
          })}
          <div className="stage-card-foot mono">
            merkle 9f2c…a1 · 3/3 signatures valid · <span className="st-support">✓ verified in browser</span>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
