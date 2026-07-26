/* The Argument Graph — center column. Force-directed SVG: the query on the
   stand, hypotheses as theories of the case, claims as exhibits orbiting
   them. Edges are weighted (thickness = confidence) and color-coded
   (green supports / red refutes / yellow-dashed needs verification). */
import { useMemo } from "react";
import type { RunState } from "../../../hooks/useRun";
import { buildGraph } from "./buildGraph";
import { layoutGraph } from "./forceLayout";
import {
  bandColor,
  confidenceBand,
  type GraphNode,
} from "./graphTypes";

const W = 820;
const H = 620;

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

interface Props {
  state: RunState;
  topic: string;
  selectedClaimId: number | null;
  onSelect: (claimId: number | null) => void;
}

export function ArgumentGraph({ state, topic, selectedClaimId, onSelect }: Props) {
  const graph = useMemo(() => {
    const { nodes, edges } = buildGraph(state, topic);
    return layoutGraph(nodes, edges, { width: W, height: H });
    // recompute as the investigation progresses
  }, [state.claims, state.hypotheses, state.status, topic]);

  const nodeById = useMemo(
    () => new Map(graph.nodes.map((n) => [n.id, n])),
    [graph],
  );

  const hasContent = graph.nodes.length > 1;

  return (
    <section className="arg-graph">
      <div className="graph-head">
        <span className="graph-title display">The Argument</span>
        <GraphLegend />
      </div>

      <div className="graph-stage">
        {!hasContent && (
          <div className="graph-empty">
            <span className="graph-empty-sigil">⚖</span>
            <p>The court is empty. Put a claim on trial to see the argument form.</p>
          </div>
        )}

        {hasContent && (
          <svg viewBox={`0 0 ${W} ${H}`} className="graph-svg" role="img" aria-label="Argument graph">
            <defs>
              <marker id="arrow-support" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
                <path d="M0,0 L7,3 L0,6 Z" fill="var(--green)" />
              </marker>
              <marker id="arrow-refute" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
                <path d="M0,0 L7,3 L0,6 Z" fill="var(--red)" />
              </marker>
              <marker id="arrow-unverified" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
                <path d="M0,0 L7,3 L0,6 Z" fill="var(--amber)" />
              </marker>
            </defs>

            {/* edges */}
            {graph.edges.map((e, i) => {
              const a = nodeById.get(e.source);
              const b = nodeById.get(e.target);
              if (!a || !b) return null;
              const color =
                e.relation === "supports" ? "var(--green)"
                : e.relation === "refutes" ? "var(--red)"
                : "var(--amber)";
              const width = 1 + e.weight * 4;
              return (
                <line
                  key={i}
                  x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                  className={`graph-edge rel-${e.relation}`}
                  stroke={color}
                  strokeWidth={width}
                  strokeDasharray={e.relation === "unverified" ? "5 5" : undefined}
                  markerEnd={`url(#arrow-${e.relation})`}
                />
              );
            })}

            {/* nodes */}
            {graph.nodes.map((n) => (
              <GraphNodeView
                key={n.id}
                node={n}
                selected={n.kind === "claim" && n.refId === selectedClaimId}
                onSelect={onSelect}
              />
            ))}
          </svg>
        )}
      </div>
    </section>
  );
}

function GraphNodeView({
  node,
  selected,
  onSelect,
}: {
  node: GraphNode;
  selected: boolean;
  onSelect: (claimId: number | null) => void;
}) {
  if (node.kind === "root") {
    return (
      <g className="gnode-root" transform={`translate(${node.x}, ${node.y})`}>
        <circle r={34} className="root-circle" />
        <text className="root-icon" textAnchor="middle" dominantBaseline="central">⚖</text>
        <foreignObject x={-110} y={40} width={220} height={54}>
          <div className="root-label">{truncate(node.label, 64)}</div>
        </foreignObject>
      </g>
    );
  }

  if (node.kind === "hypothesis") {
    return (
      <g className="gnode-hyp" transform={`translate(${node.x}, ${node.y})`}>
        <rect x={-70} y={-22} width={140} height={44} rx={10} className="hyp-rect" />
        <text className="hyp-id" x={-58} y={-6}>{node.refId}</text>
        <foreignObject x={-64} y={-2} width={128} height={40}>
          <div className="hyp-label">{truncate(node.label, 44)}</div>
        </foreignObject>
      </g>
    );
  }

  // claim node
  const conf = node.confidence ?? 0;
  const band = confidenceBand(conf);
  const color = bandColor(conf);
  const low = band === "low";
  const r = 20;
  return (
    <g
      className={`gnode-claim ${selected ? "selected" : ""} ${low ? "low-conf" : ""}`}
      transform={`translate(${node.x}, ${node.y})`}
      onClick={() => onSelect(node.refId as number)}
      style={{ cursor: "pointer" }}
    >
      {low && <circle r={r + 6} className="claim-pulse" stroke={color} />}
      {selected && <circle r={r + 5} className="claim-select-ring" />}
      <circle r={r} className="claim-circle" stroke={color} />
      <text className="claim-id" textAnchor="middle" dominantBaseline="central">
        C{node.refId}
      </text>
      <text className="claim-conf" textAnchor="middle" y={r + 13} fill={color}>
        {conf}%
      </text>
      {node.spanIssues ? (
        <text className="claim-warn" x={r - 2} y={-r + 6} textAnchor="middle">⚠</text>
      ) : null}
    </g>
  );
}

function GraphLegend() {
  return (
    <div className="graph-legend mono">
      <span className="lg"><i className="lg-line lg-support" />supports</span>
      <span className="lg"><i className="lg-line lg-refute" />refutes</span>
      <span className="lg"><i className="lg-line lg-unverified" />needs verification</span>
      <span className="lg"><i className="lg-dot lg-high" />&gt;80</span>
      <span className="lg"><i className="lg-dot lg-medium" />50–80</span>
      <span className="lg"><i className="lg-dot lg-low" />&lt;50</span>
    </div>
  );
}
