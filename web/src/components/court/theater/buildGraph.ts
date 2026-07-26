/* Builds the argument graph (nodes + edges) from the live run state.
   Root = the query; hypotheses orbit it; claims orbit their hypothesis. */
import type { RunState } from "../../../hooks/useRun";
import type { Claim, Hypothesis } from "../../../types";
import {
  dominantStance,
  type GraphEdge,
  type GraphNode,
} from "./graphTypes";

function claimEdgeRelation(c: Claim): GraphEdge["relation"] {
  if (c.status === "REFUTED") return "refutes";
  if (c.status === "UNVERIFIABLE" || c.status === "pending" || c.confidence < 50) {
    return "unverified";
  }
  const stance = dominantStance(c.verdicts.map((v) => v.stance));
  return stance === "refute" ? "refutes" : "supports";
}

export function buildGraph(
  state: RunState,
  topic: string,
): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];

  // root = the query on trial
  nodes.push({
    id: "root",
    kind: "root",
    label: topic,
    x: 0,
    y: 0,
    vx: 0,
    vy: 0,
  });

  const hypotheses: Hypothesis[] = state.hypotheses ?? [];
  const claims: Claim[] = state.claims ?? [];

  // hypothesis nodes
  for (const h of hypotheses) {
    nodes.push({
      id: `hyp-${h.id}`,
      kind: "hypothesis",
      label: h.statement,
      refId: h.id,
      plausibility: h.plausibility,
      x: 0,
      y: 0,
      vx: 0,
      vy: 0,
    });
    edges.push({
      source: "root",
      target: `hyp-${h.id}`,
      relation: "supports",
      weight: Math.max(0.3, h.plausibility),
    });
  }

  // claim nodes, attached to their hypothesis (or root if unattributed)
  for (const c of claims) {
    const stances = c.verdicts.map((v) => v.stance);
    const spanIssues = c.verdicts.filter((v) => v.quote && !v.span_valid).length;
    nodes.push({
      id: `claim-${c.id}`,
      kind: "claim",
      label: c.text,
      refId: c.id,
      status: c.status,
      confidence: c.confidence,
      stance: dominantStance(stances),
      verdictCount: c.verdicts.length,
      spanIssues,
      x: 0,
      y: 0,
      vx: 0,
      vy: 0,
    });
    const parent = c.hypothesis_id ? `hyp-${c.hypothesis_id}` : "root";
    edges.push({
      source: parent,
      target: `claim-${c.id}`,
      relation: claimEdgeRelation(c),
      weight: Math.max(0.15, c.confidence / 100),
    });
  }

  return { nodes, edges };
}
