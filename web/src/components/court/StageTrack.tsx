import type { RunState } from "../../hooks/useRun";
import type { StageName } from "../../types";

const STAGES: { id: StageName; label: string; icon: string }[] = [
  { id: "intake", label: "Intake", icon: "◈" },
  { id: "hypothesize", label: "Hypotheses", icon: "◉" },
  { id: "research", label: "Evidence", icon: "▤" },
  { id: "extract", label: "Claims", icon: "⌗" },
  { id: "verify", label: "Court ×3", icon: "⚖" },
  { id: "deliberate", label: "Deliberate", icon: "⚔" },
  { id: "hallucinations", label: "Audit", icon: "◍" },
  { id: "contradictions", label: "Conflicts", icon: "!" },
  { id: "report", label: "Verdict", icon: "✎" },
];

/** Horizontal pipeline progress. */
export function StageTrack({ state }: { state: RunState }) {
  return (
    <div className="stage-track">
      {STAGES.map((s, i) => {
        const done = state.stagesDone[s.id];
        const active = state.stage === s.id && state.status === "running";
        return (
          <div key={s.id} className="stage-wrap">
            <div className={`stage ${done ? "done" : ""} ${active ? "active" : ""}`}>
              <span className="stage-icon">{s.icon}</span>
              <span className="stage-label">{s.label}</span>
            </div>
            {i < STAGES.length - 1 && <span className={`stage-link ${done ? "done" : ""}`} />}
          </div>
        );
      })}
    </div>
  );
}
