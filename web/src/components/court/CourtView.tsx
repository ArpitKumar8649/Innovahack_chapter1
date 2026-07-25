import { useEffect, useState } from "react";
import { useRun } from "../../hooks/useRun";
import { api } from "../../lib/api";
import type { RunSummary } from "../../types";
import { StageTrack } from "./StageTrack";
import { ChatSpace } from "./ChatSpace";
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

  useEffect(() => {
    api.listRuns().then((runs) => setHistory(runs.filter((r) => !r.error))).catch(() => {});
  }, [state.status]);

  const submit = async (t?: string) => {
    const value = (t ?? topic).trim();
    if (!value || busy) return;
    setBusy(true);
    try {
      await start(value, complianceMode ? "full" : undefined);
    } catch (e) {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (state.status === "done" || state.status === "error") setBusy(false);
  }, [state.status]);

  return (
    <main className="court wrap">
      {/* intake */}
      <section className="intake">
        <form
          className="intake-form"
          onSubmit={(e) => { e.preventDefault(); void submit(); }}
        >
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
          <a href="/metrics" target="_blank" rel="noopener noreferrer" className="metrics-link mono">
            📊 metrics
          </a>
        </div>
      </section>

      <StageTrack state={state} />

      {/* the floor + the logs */}
      <div className="court-grid">
        <ChatSpace state={state} />
        <Terminal state={state} />
      </div>

      {state.error && <div className="error-banner">⚠ {state.error}</div>}

      {state.report && (
        <ReportPanel report={state.report} attestation={state.attestation} runId={state.runId ?? undefined} />
      )}

      {history.length > 0 && (
        <section className="history">
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
