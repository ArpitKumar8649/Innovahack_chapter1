/* The Bench — left column. Live agent cards with animated avatars,
   status dots, current-goal text, and per-verifier stance meters. */
import type { RunState } from "../../../hooks/useRun";
import { AGENTS, type AgentId } from "../../../lib/agents";
import type { Stance } from "../../../types";

/** Which agents are "on stage" for a given active stage. */
const STAGE_AGENTS: Record<string, AgentId[]> = {
  intake: ["memory"],
  hypothesize: ["murli"],
  research: ["researcher"],
  extract: ["extractor"],
  verify: ["verifier-a", "verifier-b", "verifier-c"],
  deliberate: ["judge"],
  hallucinations: ["auditor"],
  contradictions: ["editor"],
  report: ["writer"],
};

/** Goal text shown while an agent is active. */
const GOALS: Record<AgentId, string> = {
  memory: "Recalling prior findings…",
  murli: "Attacking its own hypotheses…",
  researcher: "Scanning web · scholar · news…",
  extractor: "Decomposing into atomic claims…",
  "verifier-a": "Checking literal evidence…",
  "verifier-b": "Hunting for contradictions…",
  "verifier-c": "Checking dates & scope…",
  judge: "Ruling on split verdicts…",
  auditor: "Sweeping for hallucinations…",
  editor: "Flagging conflicts…",
  writer: "Compiling the briefing…",
};

/** The order agents appear on the bench. */
const ORDER: AgentId[] = [
  "murli", "researcher", "extractor",
  "verifier-a", "verifier-b", "verifier-c",
  "judge", "auditor", "editor", "writer",
];

type AgentStatus = "active" | "done" | "idle";

function agentStatus(id: AgentId, state: RunState): AgentStatus {
  if (state.status === "done") return "done";
  const stage = state.stage;
  if (!stage) return "idle";
  const activeAgents = STAGE_AGENTS[stage] ?? [];
  if (activeAgents.includes(id) && state.status === "running") return "active";
  // done if any earlier stage that used this agent has completed
  const stageOrder = ["intake", "hypothesize", "research", "extract", "verify",
    "deliberate", "hallucinations", "contradictions", "report"];
  const activeIdx = stageOrder.indexOf(stage);
  for (const [s, agents] of Object.entries(STAGE_AGENTS)) {
    if (agents.includes(id) && stageOrder.indexOf(s) < activeIdx) return "done";
  }
  if (state.stagesDone[stage as keyof typeof state.stagesDone] && activeAgents.includes(id)) {
    return "done";
  }
  return "idle";
}

/** Per-verifier stance tallies across all claims. */
function verifierStances(state: RunState, tag: string): Record<Stance, number> {
  const tally: Record<Stance, number> = { support: 0, refute: 0, insufficient: 0 };
  for (const c of state.claims) {
    for (const v of c.verdicts) {
      if (v.verifier === tag) tally[v.stance]++;
    }
  }
  return tally;
}

const VERIFIER_TAG: Partial<Record<AgentId, string>> = {
  "verifier-a": "A",
  "verifier-b": "B",
  "verifier-c": "C",
};

/** Animated avatar — CSS/SVG, no Lottie dependency. */
function AgentAvatar({ id, status }: { id: AgentId; status: AgentStatus }) {
  const agent = AGENTS[id];
  const animClass = status === "active" ? `avatar-anim avatar-${id}` : "";
  return (
    <div
      className={`agent-avatar ${status} ${animClass}`}
      style={{ ["--agent-color" as string]: agent.color }}
    >
      <span className="avatar-sigil">{agent.sigil}</span>
      {status === "active" && <span className="avatar-ring" />}
    </div>
  );
}

/** Stance confidence meter for a verifier. */
function StanceMeter({ tally }: { tally: Record<Stance, number> }) {
  const total = tally.support + tally.refute + tally.insufficient;
  if (total === 0) return null;
  const pct = (n: number) => `${(n / total) * 100}%`;
  return (
    <div className="stance-meter" title={`${tally.support} support · ${tally.refute} refute · ${tally.insufficient} unverified`}>
      <div className="stance-meter-bar">
        <span className="sm-seg sm-support" style={{ width: pct(tally.support) }} />
        <span className="sm-seg sm-refute" style={{ width: pct(tally.refute) }} />
        <span className="sm-seg sm-insuff" style={{ width: pct(tally.insufficient) }} />
      </div>
      <div className="stance-meter-labels mono">
        <span className="st-support">{tally.support}✓</span>
        <span className="st-refute">{tally.refute}✗</span>
        <span className="st-insufficient">{tally.insufficient}?</span>
      </div>
    </div>
  );
}

export function AgentCast({ state }: { state: RunState }) {
  const running = state.status === "running";
  return (
    <aside className="agent-cast">
      <div className="cast-head">
        <span className="cast-title display">The Bench</span>
        <span className="cast-count mono">
          {running ? "in session" : state.status === "done" ? "adjourned" : "awaiting"}
        </span>
      </div>
      <div className="cast-list">
        {ORDER.map((id) => {
          const agent = AGENTS[id];
          const status = agentStatus(id, state);
          const tag = VERIFIER_TAG[id];
          const tally = tag ? verifierStances(state, tag) : null;
          return (
            <div key={id} className={`cast-card ${status}`}>
              <AgentAvatar id={id} status={status} />
              <div className="cast-body">
                <div className="cast-name-row">
                  <span className="cast-name">{agent.name}</span>
                  <span className="cast-role mono">{agent.role}</span>
                  <span className={`cast-dot ${status}`} />
                </div>
                <div className="cast-goal">
                  {status === "active" ? GOALS[id] : agent.lens}
                </div>
                {tally && <StanceMeter tally={tally} />}
              </div>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
