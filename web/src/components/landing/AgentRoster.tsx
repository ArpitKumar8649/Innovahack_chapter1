import { Reveal } from "../ui/Reveal";
import { AGENTS, type AgentId } from "../../lib/agents";
import { Avatar } from "../ui/Avatar";

const ORDER: AgentId[] = [
  "murli", "researcher", "extractor",
  "verifier-a", "verifier-b", "verifier-c",
  "judge", "auditor", "editor", "writer",
];

export function AgentRoster() {
  return (
    <section className="roster wrap" id="agents">
      <Reveal>
        <span className="eyebrow">the bench</span>
        <h2 className="display section-title">Ten agents, one verdict.</h2>
        <p className="section-sub">
          Each agent has a single job and a bias built in — so no single
          perspective, and no single model's blind spot, gets the final word.
        </p>
      </Reveal>
      <div className="roster-grid">
        {ORDER.map((id, i) => {
          const a = AGENTS[id];
          return (
            <Reveal key={id} delay={(i % 5) * 70}>
              <div className="agent-card glow-card" style={{ ["--agent-color" as string]: a.color }}>
                <Avatar agent={a} size={44} />
                <div>
                  <div className="agent-card-name">{a.name} <span className="agent-card-role">{a.role}</span></div>
                  <p className="agent-card-lens">{a.lens}</p>
                </div>
              </div>
            </Reveal>
          );
        })}
      </div>
    </section>
  );
}
