import { useMemo, useState } from "react";
import type { Report } from "../../types";
import type { Attestation } from "../../types";
import { TrustGauge } from "./TrustGauge";
import { ClaimCard } from "./ClaimCard";
import { EvidenceInspector } from "./EvidenceInspector";

export function ReportPanel({ report, attestation }: {
  report: Report;
  attestation: Attestation | null;
}) {
  const [inspect, setInspect] = useState<{ claimId: number; chunkId?: string } | null>(null);
  const sources = useMemo(() => new Map(report.sources.map((s) => [s.id, s])), [report]);
  const inspectedClaim = inspect ? report.claims.find((c) => c.id === inspect.claimId) : null;

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
      </div>

      {report.summary && (
        <div className="summary-card">
          <h4 className="section-h">The court's summary</h4>
          <p>{report.summary}</p>
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
          <ClaimCard
            key={c.id}
            claim={c}
            sources={sources}
            onInspect={(claimId, chunkId) => setInspect({ claimId, chunkId })}
          />
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
