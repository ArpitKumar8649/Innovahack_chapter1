/* Evidence Drawer — right column. Context-aware: shows the selected claim's
   verdicts (with exact quotes), source credibility cards, counter-evidence,
   and hallucination flags. Falls back to a run overview when nothing is
   selected. */
import type { RunState } from "../../../hooks/useRun";
import { AGENTS, agentForVerifier } from "../../../lib/agents";
import type { Claim, Source, Verdict } from "../../../types";
import { bandColor, STANCE_COLOR, STANCE_LABEL } from "./graphTypes";

interface Props {
  state: RunState;
  selectedClaimId: number | null;
  onSelect: (claimId: number | null) => void;
}

export function EvidenceDrawer({ state, selectedClaimId, onSelect }: Props) {
  const claim = selectedClaimId != null
    ? state.claims.find((c) => c.id === selectedClaimId)
    : null;

  return (
    <aside className="evidence-drawer glow-card">
      {claim ? (
        <ClaimDetail claim={claim} state={state} onClear={() => onSelect(null)} />
      ) : (
        <RunOverview state={state} />
      )}
    </aside>
  );
}

/* ------------------------------------------------------------------ */

function RunOverview({ state }: { state: RunState }) {
  const report = state.report;
  const att = state.attestation;
  return (
    <div className="drawer-inner">
      <div className="drawer-head">
        <span className="drawer-title display">Case File</span>
        <span className="drawer-sub mono">select an exhibit to inspect</span>
      </div>

      {state.topic && (
        <div className="overview-topic">
          <span className="overview-label mono">on trial</span>
          <p className="overview-text">{state.topic}</p>
        </div>
      )}

      {report && (
        <>
          <div className="overview-trust">
            <span className="overview-label mono">trust score</span>
            <div className="trust-big">
              <span className="trust-num display" style={{ color: bandColor(report.trust_score) }}>
                {report.trust_score}
              </span>
              <span className="trust-denom mono">/100</span>
            </div>
          </div>

          {report.summary && (
            <div className="overview-summary">
              <span className="overview-label mono">the court's summary</span>
              <p>{report.summary}</p>
            </div>
          )}

          <div className="overview-stats">
            <Stat label="claims" value={report.claims.length} />
            <Stat label="sources" value={report.sources.length} />
            <Stat label="conflicts" value={report.contradictions.length} />
            <Stat label="rounds" value={report.memory_stats?.rounds ?? 1} />
          </div>

          {att && (
            <div className={`overview-attest ${att.verified ? "ok" : "bad"}`}>
              <span className="attest-icon">{att.verified ? "✓" : "✗"}</span>
              <span>
                {att.verified
                  ? `Cryptographically verified — ${att.signatures_valid}/${att.signatures_checked} signatures`
                  : `Attestation failed: ${att.issues.join(", ") || "unknown"}`}
              </span>
            </div>
          )}
        </>
      )}

      {!report && !state.topic && (
        <div className="drawer-empty">
          <span className="drawer-empty-icon">▤</span>
          <p>Evidence and sources will appear here as the court examines them.</p>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="ov-stat">
      <span className="ov-stat-num display">{value}</span>
      <span className="ov-stat-label mono">{label}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */

function ClaimDetail({ claim, state, onClear }: {
  claim: Claim;
  state: RunState;
  onClear: () => void;
}) {
  const sourcesById = new Map(state.sources.map((s) => [s.id, s]));
  const color = bandColor(claim.confidence);

  return (
    <div className="drawer-inner">
      <div className="drawer-head">
        <span className="drawer-title display">Exhibit C{claim.id}</span>
        <button className="drawer-close mono" onClick={onClear}>✕ close</button>
      </div>

      <p className="claim-detail-text">{claim.text}</p>

      <div className="claim-detail-meta">
        <span className="cd-status" style={{ color: bandColor(claim.confidence), borderColor: bandColor(claim.confidence) }}>
          {claim.status}
        </span>
        <span className="cd-conf mono" style={{ color }}>
          {claim.confidence}% confidence
        </span>
        {claim.hypothesis_id && (
          <span className="cd-hyp mono">{claim.hypothesis_id}</span>
        )}
      </div>

      {/* verdicts */}
      <div className="cd-section">
        <span className="cd-section-h mono">verdicts ({claim.verdicts.length})</span>
        {claim.verdicts.length === 0 && (
          <p className="cd-muted">No verdicts yet — the panel hasn't weighed in.</p>
        )}
        {claim.verdicts.map((v, i) => (
          <VerdictCard key={i} v={v} />
        ))}
      </div>

      {/* hallucinations */}
      {claim.hallucinations.length > 0 && (
        <div className="cd-section">
          <span className="cd-section-h mono">auditor flags</span>
          {claim.hallucinations.map((h, i) => (
            <div key={i} className={`hallu-flag sev-${h.severity}`}>
              <span className="hallu-type mono">{h.type}</span>
              <span className="hallu-sev mono">{h.severity}</span>
              <p>{h.evidence}</p>
            </div>
          ))}
        </div>
      )}

      {/* counter-evidence */}
      {claim.counter_evidence.length > 0 && (
        <div className="cd-section">
          <span className="cd-section-h mono">counter-evidence (semantic)</span>
          {claim.counter_evidence.map((ce, i) => (
            <div key={i} className="counter-card">
              <div className="counter-head">
                <span className="counter-score mono">+{ce.score.toFixed(2)}</span>
                <span className="counter-pub mono">{ce.publisher || "unknown"}</span>
                <span className={`tier tier-${ce.authority_tier}`}>T{ce.authority_tier}</span>
              </div>
              <p>{ce.text.slice(0, 220)}{ce.text.length > 220 ? "…" : ""}</p>
              {ce.url && (
                <a href={ce.url} target="_blank" rel="noopener noreferrer" className="counter-link mono">
                  source ↗
                </a>
              )}
            </div>
          ))}
        </div>
      )}

      {/* sources */}
      <div className="cd-section">
        <span className="cd-section-h mono">sources ({claim.source_ids.length})</span>
        {claim.source_ids.map((sid) => {
          const s = sourcesById.get(sid);
          if (!s) return null;
          return <SourceCard key={sid} s={s} />;
        })}
      </div>
    </div>
  );
}

function VerdictCard({ v }: { v: Verdict }) {
  const agent = AGENTS[agentForVerifier(v.verifier)];
  const stanceColor = STANCE_COLOR[v.stance];
  return (
    <div className="verdict-card" style={{ ["--stance" as string]: stanceColor }}>
      <div className="verdict-head">
        <span className="verdict-agent" style={{ color: agent.color }}>
          {agent.sigil} {agent.name}
        </span>
        <span className="verdict-stance mono" style={{ color: stanceColor }}>
          {STANCE_LABEL[v.stance]}
        </span>
        {v.round > 1 && <span className="verdict-round mono">R{v.round}</span>}
      </div>
      <p className="verdict-reasoning">{v.reasoning}</p>
      {v.quote && (
        <blockquote className={`verdict-quote ${v.span_valid ? "valid" : "void"}`}>
          “{v.quote}”
          <span className="quote-validity mono">
            {v.span_valid ? `✓ ${v.chunk_id}` : "⚠ quote not in corpus — voided"}
          </span>
        </blockquote>
      )}
      {v.dissent && <p className="verdict-dissent">Dissent: {v.dissent}</p>}
    </div>
  );
}

function SourceCard({ s }: { s: Source }) {
  return (
    <a className="source-card-mini" href={s.url} target="_blank" rel="noopener noreferrer">
      <div className="scm-head">
        <span className="scm-id mono">[{s.id}]</span>
        <span className={`tier tier-${s.authority_tier}`}>T{s.authority_tier}</span>
        <span className="scm-origin mono">{s.origin}</span>
      </div>
      <span className="scm-title">{s.title}</span>
      <span className="scm-pub mono">{s.publisher || "unknown publisher"}</span>
    </a>
  );
}
