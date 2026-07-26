/* CourtView — The Debate Theater. A 3-column command center:
   left = The Bench (agent state), center = the Argument Graph,
   right = the Evidence Drawer. The linear chat is gone; the debate is
   spatial. Intervention controls let you freeze the feed or re-argue fresh. */
import { useEffect, useState } from "react";
import { useRun } from "../../hooks/useRun";
import { api } from "../../lib/api";
import type { RunSummary } from "../../types";
import { AgentCast } from "./theater/AgentCast";
import { ArgumentGraph } from "./theater/ArgumentGraph";
import { EvidenceDrawer } from "./theater/EvidenceDrawer";
import { PhaseStepper, ConsensusDiff } from "./theater/PhaseStepper";
import { Terminal } from "./Terminal";
import { ReportPanel } from "./ReportPanel";

const EXAMPLES = [
  "Albert Einstein won the Nobel Prize for his theory of relativity",
  "The Great Wall of China is visible from space",
  "Did climate change cause the 2024 Dubai floods?",
  "History of the Eiffel Tower",
];

export function CourtView() {
  const { state, start, loadReport } = useRun();
  const [topic, setTopic] = useState(EXAMPLES[0]);
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState<RunSummary[]>([]);
  const [complianceMode, setComplianceMode] = useState(false);
  const [selectedClaimId, setSelectedClaimId] = useState<number | null>(null);
  const [showTerminal, setShowTerminal] = useState(false);

  useEffect(() => {
    api.listRuns().then((runs) => setHistory(runs.filter((r) => !r.error))).catch(() => {});
  }, [state.status]);

  useEffect(() => {
    if (state.status === "done" || state.status === "error") setBusy(false);
  }, [state.status]);

  // reset selection when a new trial starts
  useEffect(() => {
    if (state.status === "running") setSelectedClaimId(null);
  }, [state.runId, state.status]);

  const submit = async (t?: string) => {
    const value = (t ?? topic).trim();
    if (!value || busy) return;
    setBusy(true);
    try {
      await start(value, complianceMode ? "full" : undefined);
    } catch {
      setBusy(false);
    }
  };

  const inSession = state.status === "running" || state.status === "done";

  return (
    <main className="court theater">
      {/* intake — always available */}
      <section className="intake wrap">
        <form className="intake-form" onSubmit={(e) => { e.preventDefault(); void submit(); }}>
          <input
            className="intake-input"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Enter a claim to put on trial…"
            spellCheck={false}
          />
          <button className="btn btn-gold" type="submit" disabled={busy}>
            {busy ? "Trial in session…" : "Put on trial →"}
          </button>
        </form>
        <div className="intake-chips">
          <span className="chip-label mono">try:</span>
          {EXAMPLES.map((ex) => (
            <button key={ex} className="chip" onClick={() => { setTopic(ex); void submit(ex); }}>
              {ex.length > 46 ? ex.slice(0, 46) + "…" : ex}
            </button>
          ))}
        </div>
        <div className="intake-options">
          <label className="compliance-toggle">
            <input
              type="checkbox"
              checked={complianceMode}
              onChange={(e) => setComplianceMode(e.target.checked)}
            />
            <span className="mono">compliance mode</span>
          </label>
          <button
            className="metrics-link mono"
            onClick={() => setShowTerminal((s) => !s)}
            type="button"
          >
            {showTerminal ? "▾ hide pipeline log" : "▸ pipeline log"}
          </button>
          <a href="/metrics" target="_blank" rel="noopener noreferrer" className="metrics-link mono">
            📊 metrics
          </a>
        </div>
      </section>

      <PhaseStepper state={state} />

      {state.error && <div className="error-banner wrap">⚠ {state.error}</div>}

      {/* the 3-column theater */}
      {inSession ? (
        <div className="theater-grid wrap">
          <AgentCast state={state} />
          <ArgumentGraph
            state={state}
            topic={state.topic}
            selectedClaimId={selectedClaimId}
            onSelect={setSelectedClaimId}
          />
          <EvidenceDrawer
            state={state}
            selectedClaimId={selectedClaimId}
            onSelect={setSelectedClaimId}
          />
        </div>
      ) : (
        <div className="theater-idle wrap">
          <span className="idle-sigil">⚖</span>
          <h3 className="display">The court is not in session.</h3>
          <p>Put a claim on trial above and watch ten agents argue it into receipts.</p>
        </div>
      )}

      {showTerminal && <div className="wrap theater-terminal"><Terminal state={state} /></div>}

      {/* consensus diff + full report once the trial concludes */}
      {state.status === "done" && state.report && (
        <>
          <div className="wrap"><ConsensusDiff state={state} /></div>
          <ReportPanel
            report={state.report}
            attestation={state.attestation}
            runId={state.runId ?? undefined}
          />
        </>
      )}

      {history.length > 0 && (
        <section className="history wrap">
          <h4 className="section-h">Past trials</h4>
          <div className="history-list">
            {history.map((h) => (
              <button key={h.run_id} className="hist-item" onClick={() => void loadReport(h.run_id)}>
                <span className="hist-topic">{h.topic}</span>
                <span className={`hist-score mono ${
                  (h.trust_score ?? 0) >= 75 ? "st-support" : (h.trust_score ?? 0) >= 50 ? "st-insufficient" : "st-refute"
                }`}>
                  {h.trust_score ?? "–"}
                </span>
              </button>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
