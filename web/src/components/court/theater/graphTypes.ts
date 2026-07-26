/* Shared types for the Debate Theater (Phase 4 court overhaul). */
import type { Stance, Status } from "../../../types";

/** A node in the force-directed argument graph. */
export interface GraphNode {
  id: string;
  kind: "root" | "hypothesis" | "claim";
  label: string;
  /** claim id or hypothesis id, for linking back to source data */
  refId?: number | string;
  status?: Status;
  confidence?: number;      // 0-100 for claims
  stance?: Stance;          // dominant stance for claims
  plausibility?: number;    // 0-1 for hypotheses
  verdictCount?: number;    // how many verifiers have weighed in
  spanIssues?: number;      // voided quotes on this claim
  /* layout output */
  x: number;
  y: number;
  vx: number;
  vy: number;
}

/** A directed edge between two graph nodes. */
export interface GraphEdge {
  source: string;
  target: string;
  relation: "supports" | "refutes" | "unverified";
  /** edge weight 0-1 — drives stroke thickness */
  weight: number;
}

export interface LaidOutGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  width: number;
  height: number;
}

/** Confidence band per the design spec. */
export type ConfidenceBand = "high" | "medium" | "low";

export function confidenceBand(conf: number): ConfidenceBand {
  if (conf > 80) return "high";
  if (conf >= 50) return "medium";
  return "low";
}

/** CSS color for a confidence band. */
export const BAND_COLOR: Record<ConfidenceBand, string> = {
  high: "var(--green)",
  medium: "var(--amber)",
  low: "var(--red)",
};

export function bandColor(conf: number): string {
  return BAND_COLOR[confidenceBand(conf)];
}

/** CSS color for a stance. */
export const STANCE_COLOR: Record<Stance, string> = {
  support: "var(--green)",
  refute: "var(--red)",
  insufficient: "var(--amber)",
};

/** CSS color for an epistemic status. */
export const STATUS_COLOR: Record<Status, string> = {
  ESTABLISHED: "var(--green)",
  SUPPORTED: "var(--accent)",
  CONTESTED: "var(--amber)",
  REFUTED: "var(--red)",
  UNVERIFIABLE: "var(--ink-3)",
  OUTDATED: "var(--accent-2)",
  pending: "var(--ink-4)",
};

export const STANCE_LABEL: Record<Stance, string> = {
  support: "Supports",
  refute: "Refutes",
  insufficient: "Needs verification",
};

/** Dominant stance from a set of verdict stances. */
export function dominantStance(stances: Stance[]): Stance {
  const sup = stances.filter((s) => s === "support").length;
  const ref = stances.filter((s) => s === "refute").length;
  if (sup > ref) return "support";
  if (ref > sup) return "refute";
  return "insufficient";
}
