import type { GraphStats } from "../../types";

/**
 * ProvenanceGraph — visualizes the knowledge graph stats.
 * Shows claim→source→publisher flow and highlights circular citations.
 */
export function ProvenanceGraph({ stats }: { stats: GraphStats }) {
  const hasCircular = stats.circular_citations > 0;

  return (
    <div className="provenance-graph">
      <div className="provenance-header">
        <h4>Provenance Graph</h4>
        {hasCircular && (
          <span className="circular-badge" title="Circular citations detected">
            ⚠ {stats.circular_citations} circular
          </span>
        )}
      </div>

      <div className="provenance-stats">
        <div className="stat-item">
          <span className="stat-value">{stats.claims}</span>
          <span className="stat-label">claims</span>
        </div>
        <div className="stat-arrow">→</div>
        <div className="stat-item">
          <span className="stat-value">{stats.sources}</span>
          <span className="stat-label">sources</span>
        </div>
        <div className="stat-arrow">→</div>
        <div className="stat-item">
          <span className="stat-value">{stats.publishers}</span>
          <span className="stat-label">publishers</span>
        </div>
      </div>

      <div className="provenance-meta mono">
        {stats.edges} edges · {stats.circular_citations} cycles
      </div>

      {hasCircular && stats.cycles.length > 0 && (
        <div className="circular-cycles">
          <div className="cycles-header">Circular citation chains:</div>
          {stats.cycles.map((cycle, i) => (
            <div key={i} className="cycle-chain mono">
              {cycle.join(" → ")}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
