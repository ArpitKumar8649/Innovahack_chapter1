import { useEffect, useMemo, useRef, useState } from "react";
import type { Attestation, Report } from "../../types";
import { api } from "../../lib/api";
import { TrustGauge } from "./TrustGauge";
import { TrustRadarChart } from "./TrustRadar";
import { ArgumentTreeView } from "./ArgumentTree";
import { ClaimCard } from "./ClaimCard";
import { EvidenceInspector } from "./EvidenceInspector";
import { ProvenanceGraph } from "./ProvenanceGraph";

export function ReportPanel({ report, attestation, runId }: {
  report: Report;
  attestation: Attestation | null;
  runId?: string;
}) {
  const [inspect, setInspect] = useState<{ claimId: number; chunkId?: string } | null>(null);
  const [complianceTrace, setComplianceTrace] = useState<any | null>(null);
  const [replayResult, setReplayResult] = useState<any | null>(null);
  const sources = useMemo(() => new Map(report.sources.map((s) => [s.id, s])), [report]);
  const inspectedClaim = inspect ? report.claims.find((c) => c.id === inspect.claimId) : null;

  // ---- Phase 5 engagement tracking (dwell time, inspector opens, tree views) ----
  const inspectorOpens = useRef(0);
  const treeViews = useRef(0);
  const startedAt = useRef(Date.now());
  const treeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    startedAt.current = Date.now();
    inspectorOpens.current = 0;
    treeViews.current = 0;
    const runId = (report as unknown as { run_id?: string }).run_id;

    // count a "tree view" when the argument section scrolls into view
    const el = treeRef.current;
    let io: IntersectionObserver | undefined;
    if (el) {
      io = new IntersectionObserver(([entry]) => {
        if (entry.isIntersecting) { treeViews.current += 1; io?.disconnect(); }
      }, { threshold: 0.3 });
      io.observe(el);
    }

    return () => {
      io?.disconnect();
      const dwell = Date.now() - startedAt.current;
      if (dwell > 1500) {
        api.recordEngagement({
          run_id: runId ?? report.topic,
          topic: report.topic,
          dwell_ms: dwell,
          inspector_opens: inspectorOpens.current,
          tree_views: treeViews.current,
        });
      }
    };
  }, [report]);

  const openInspector = (claimId: number, chunkId?: string) => {
    inspectorOpens.current += 1;
    setInspect({ claimId, chunkId });
  };

  const loadComplianceTrace = async () => {
    if (!runId) return;
    try {
      const trace = await api.getComplianceTrace(runId);
      setComplianceTrace(trace);
    } catch (e) {
      console.error("Failed to load compliance trace:", e);
    }
  };

  const loadReplayResult = async () => {
    if (!runId) return;
    try {
      const result = await api.replayWorkflow(runId);
      setReplayResult(result);
    } catch (e) {
      console.error("Failed to load replay result:", e);
    }
  };

  const hasTree = !!report.argument_tree?.root;
  const radar = report.trust_radar;
  const weakest = report.argument_tree?.weakest_link;

  return (
    <section className="report-panel">
      <div className="report-head">
        <TrustGauge score={report.trust_score} />
        <div className="report-title">
          <h3 className="display">{report.topic}</h3>
          <p className="report-stats mono">
            {report.claims.length} claims · {report.sources.length} sources ·{" "}
            {report.contradictions.length} conflicts
            {report.memory_stats?.cached ? ` · ${report.memory_stats.cached} from memory` : ""}
            {report.memory_stats?.rounds > 1 ? ` · ${report.memory_stats.rounds} debate rounds` : ""}
          </p>
          <AttestationBadge attestation={attestation} root={report.merkle_root} />
        </div>
        {radar && (
          <div className="report-radar">
            <span className="radar-title mono">trust radar</span>
            <TrustRadarChart radar={radar} />
          </div>
        )}
      </div>

      {report.summary && (
        <div className="summary-card">
          <h4 className="section-h">The court's summary</h4>
          <p>{report.summary}</p>
        </div>
      )}

      {hasTree && (
        <div className="argument-section" ref={treeRef}>
          <h4 className="section-h">The argument <span className="muted">(Toulmin structure)</span></h4>
          {weakest && (
            <div className="weakest-link">
              <span className="weakest-flag">⚠ weakest link</span>
              <span>{weakest.note}</span>
              <a href={sources.get(weakest.source_id)?.url} target="_blank" rel="noopener noreferrer" className="mono">
                [{weakest.source_id}] {weakest.publisher}
              </a>
            </div>
          )}
          <ArgumentTreeView tree={report.argument_tree} />
        </div>
      )}

      {report.graph_stats && (
        <div className="provenance-section">
          <h4 className="section-h">Provenance graph <span className="muted">(knowledge graph)</span></h4>
          <ProvenanceGraph stats={report.graph_stats} />
        </div>
      )}

      {report.contradictions.length > 0 && (
        <div className="contras">
          <h4 className="section-h contra-h">⚠ Contradictions & corrections</h4>
          {report.contradictions.map((cd, i) => (
            <div key={i} className="contra-card">
              <div className="contra-kind mono">{cd.kind.replace(/_/g, " ")}</div>
              <p>{cd.description}</p>
            </div>
          ))}
        </div>
      )}

      <h4 className="section-h">Claims & verdicts <span className="muted">({report.claims.length})</span></h4>
      <div className="claims">
        {report.claims.map((c) => (
          <ClaimCard key={c.id} claim={c} sources={sources} onInspect={openInspector} runId={runId} />
        ))}
      </div>

      <h4 className="section-h">Evidence sources <span className="muted">({report.sources.length})</span></h4>
      <div className="sources">
        {report.sources.map((s) => (
          <a key={s.id} className="source-card" href={s.url} target="_blank" rel="noopener noreferrer">
            <span className="src-id mono">[{s.id}]</span>
            <span className="src-title">{s.title}</span>
            <span className="src-meta">
              <span className={`tier tier-${s.authority_tier}`}>T{s.authority_tier}</span>
              {s.publisher}
              {s.published_at ? ` · ${s.published_at.slice(0, 10)}` : ""}
              {s.origin !== "web" ? ` · ${s.origin}` : ""}
            </span>
          </a>
        ))}
      </div>

      {inspectedClaim && (
        <EvidenceInspector
          claim={inspectedClaim}
          report={report}
          focusChunk={inspect?.chunkId}
          onClose={() => setInspect(null)}
        />
      )}

      {runId && (
        <div className="phase8-section">
          <h4 className="section-h">Phase 8: Observability & Compliance</h4>
          <div className="phase8-buttons">
            <button className="btn btn-secondary" onClick={loadComplianceTrace}>
              📋 View Compliance Trace
            </button>
            <button className="btn btn-secondary" onClick={loadReplayResult}>
              🔄 Replay Workflow
            </button>
          </div>

          {complianceTrace && (
            <div className="compliance-trace">
              <h5 className="mono">Compliance Trace ({complianceTrace.trace_length} events)</h5>
              <pre className="trace-output">{JSON.stringify(complianceTrace.trace, null, 2)}</pre>
            </div>
          )}

          {replayResult && (
            <div className="replay-result">
              <h5 className="mono">Workflow Replay Result</h5>
              <pre className="trace-output">{JSON.stringify(replayResult, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function AttestationBadge({ attestation, root }: { attestation: Attestation | null; root: string }) {
  if (!attestation) {
    return (
      <div className="verify-badge pending">
        <span>◌</span> verifying cryptographic anchors…
      </div>
    );
  }
  return attestation.verified ? (
    <div className="verify-badge ok">
      <span>✓</span> cryptographically verified — Merkle {root.slice(0, 10)}… matched,{" "}
      {attestation.signatures_valid}/{attestation.signatures_checked} signatures valid
    </div>
  ) : (
    <div className="verify-badge bad">
      <span>✗</span> attestation failed: {attestation.issues.join(", ") || "unknown"}
    </div>
  );
}
