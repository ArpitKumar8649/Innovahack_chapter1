import { useState } from "react";

interface RedTeamFinding {
  claim_id: number;
  attack_vector: string;
  severity: "high" | "medium" | "low";
  finding: string;
  recommendation: string;
}

export function RedTeamPanel({ findings }: { findings: RedTeamFinding[] }) {
  const [expanded, setExpanded] = useState(false);

  if (!findings || findings.length === 0) {
    return (
      <div className="redteam-panel">
        <h4 className="section-h">🔴 Red-Team Agent</h4>
        <p className="muted">No adversarial findings — the report withstood probing.</p>
      </div>
    );
  }

  const highCount = findings.filter(f => f.severity === "high").length;
  const mediumCount = findings.filter(f => f.severity === "medium").length;
  const lowCount = findings.filter(f => f.severity === "low").length;

  const vectorLabels: Record<string, string> = {
    source_quality: "Source Quality",
    staleness: "Staleness",
    scope_creep: "Scope Creep",
    entity_confusion: "Entity Confusion",
    missing_evidence: "Missing Evidence",
  };

  return (
    <div className="redteam-panel">
      <h4 className="section-h">
        🔴 Red-Team Agent
        <span className="muted">({findings.length} findings)</span>
      </h4>

      <div className="redteam-summary">
        {highCount > 0 && <span className="severity-badge high">{highCount} high</span>}
        {mediumCount > 0 && <span className="severity-badge medium">{mediumCount} medium</span>}
        {lowCount > 0 && <span className="severity-badge low">{lowCount} low</span>}
      </div>

      <button
        className="btn btn-secondary"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? "Hide findings" : "Show findings"}
      </button>

      {expanded && (
        <div className="redteam-findings">
          {findings.map((f, i) => (
            <div key={i} className={`redteam-finding severity-${f.severity}`}>
              <div className="finding-header">
                <span className="finding-vector">{vectorLabels[f.attack_vector] || f.attack_vector}</span>
                <span className={`severity-badge ${f.severity}`}>{f.severity}</span>
                <span className="finding-claim mono">C{f.claim_id}</span>
              </div>
              <p className="finding-text">{f.finding}</p>
              {f.recommendation && (
                <p className="finding-recommendation">
                  <strong>Recommendation:</strong> {f.recommendation}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
