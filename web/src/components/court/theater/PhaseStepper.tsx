/* PhaseStepper — groups the pipeline stages into three debate phases.
   ConsensusDiff — the "What Changed?" view: how deliberation moved each claim. */
import type { RunState } from "../../../hooks/useRun";
import type { StageName, Stance, Verdict } from "../../../types";
import { bandColor, STANCE_COLOR } from "./graphTypes";

/* ------------------------------------------------------------------ */
/*  PhaseStepper                                                       */
/* ------------------------------------------------------------------ */

const PHASES: { id: number; label: string; sub: string; stages: StageName[] }[] = [
  { id: 1, label: "Initial Claims", sub: "hypotheses + evidence", stages: ["intake", "hypothesize", "research", "extract"] },
  { id: 2, label: "Cross-Examination", sub: "verdicts + debate", stages: ["verify", "deliberate", "hallucinations", "contradictions"] },
  { id: 3, label: "Final Synthesis", sub: "scoring + verdict", stages: ["semantic", "report"] },
];

type PhaseState = "done" | "active" | "pending";

function phaseState(p: (typeof PHASES)[number], state: RunState): PhaseState {
  const allDone = p.stages.every((s) => state.stagesDone[s]);
  if (allDone) return "done";
  const isActive = state.status === "running" && state.stage != null && p.stages.includes(state.stage);
  if (isActive) return "active";
  // if any earlier stage in this phase has started, it's partially active
  const anyStarted = p.stages.some((s) => state.stagesDone[s]);
  if (anyStarted && state.status === "running") return "active";
  return "pending";
}

export function PhaseStepper({ state }: { state: RunState }) {
  if (state.status === "idle") return null;
  return (
    <div className="phase-stepper">
      {PHASES.map((p, i) => {
        const ps = phaseState(p, state);
        return (
          <div key={p.id} className="phase-wrap">
            <div className={`phase ${ps}`}>
              <span className="phase-num mono">{ps === "done" ? "✓" : p.id}</span>
              <div className="phase-text">
                <span className="phase-label">{p.label}</span>
                <span className="phase-sub mono">{p.sub}</span>
              </div>
            </div>
            {i < PHASES.length - 1 && <span className={`phase-link ${ps === "done" ? "done" : ""}`} />}
          </div>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  ConsensusDiff — "What Changed?"                                    */
/* ------------------------------------------------------------------ */

const STANCE_GLYPH: Record<Stance, string> = {
  support: "✓",
  refute: "✗",
  insufficient: "?",
};

function round1Verdicts(verdicts: Verdict[]): Verdict[] {
  return verdicts.filter((v) => v.round <= 1);
}
function laterVerdicts(verdicts: Verdict[]): Verdict[] {
  return verdicts.filter((v) => v.round > 1);
}

function stanceSummary(vs: Verdict[]): string {
  if (vs.length === 0) return "—";
  return vs
    .map((v) => `${v.verifier}${STANCE_GLYPH[v.stance]}`)
    .join(" ");
}

export function ConsensusDiff({ state }: { state: RunState }) {
  if (state.status !== "done" || state.claims.length === 0) return null;

  const rows = state.claims.map((c) => {
    const r1 = round1Verdicts(c.verdicts);
    const later = laterVerdicts(c.verdicts);
    const changed = later.length > 0;
    return { claim: c, r1, later, changed };
  });

  const changedCount = rows.filter((r) => r.changed).length;

  return (
    <div className="consensus-diff">
      <div className="cd-head">
        <span className="cd-title display">What Changed?</span>
        <span className="cd-sub mono">
          {changedCount > 0
            ? `${changedCount} claim${changedCount > 1 ? "s" : ""} moved during deliberation`
            : "panel reached consensus without rebuttal"}
        </span>
      </div>

      <div className="cd-rows">
        {rows.map(({ claim, r1, later, changed }) => (
          <div key={claim.id} className={`cd-row ${changed ? "changed" : "stable"}`}>
            <div className="cd-row-claim">
              <span className="cd-row-id mono">C{claim.id}</span>
              <span className="cd-row-text">{claim.text}</span>
            </div>
            <div className="cd-row-flow">
              <span className="cd-round mono" title="Round 1 verdicts">
                {stanceSummary(r1)}
              </span>
              <span className="cd-arrow">{changed ? "→" : "="}</span>
              <span
                className="cd-final mono"
                style={{ color: bandColor(claim.confidence) }}
                title={later.length ? `After deliberation: ${stanceSummary(later)}` : "No change"}
              >
                {claim.status} {claim.confidence}%
              </span>
            </div>
            {changed && (
              <div className="cd-row-detail mono">
                {later.map((v, i) => (
                  <span key={i} style={{ color: STANCE_COLOR[v.stance] }}>
                    {v.verifier} {v.action || "revised"}{v.dissent ? " · dissent noted" : ""}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
