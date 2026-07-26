/* Deterministic force-directed layout (Fruchterman–Reingold).
   Synchronous + seeded so the graph is stable across renders — no jitter,
   no requestAnimationFrame bugs. Radial seeding keeps it readable. */
import type { GraphEdge, GraphNode, LaidOutGraph } from "./graphTypes";

interface LayoutOpts {
  width: number;
  height: number;
  iterations?: number;
}

/** Seed positions radially: root center, hypotheses on an inner ring,
    claims on an outer ring grouped near their hypothesis. */
function seed(nodes: GraphNode[], edges: GraphEdge[], w: number, h: number) {
  const cx = w / 2;
  const cy = h / 2;
  const root = nodes.find((n) => n.kind === "root");
  const hyps = nodes.filter((n) => n.kind === "hypothesis");
  const claims = nodes.filter((n) => n.kind === "claim");

  if (root) {
    root.x = cx;
    root.y = cy;
  }
  const rHyp = Math.min(w, h) * 0.22;
  hyps.forEach((n, i) => {
    const a = (i / Math.max(hyps.length, 1)) * Math.PI * 2 - Math.PI / 2;
    n.x = cx + Math.cos(a) * rHyp;
    n.y = cy + Math.sin(a) * rHyp;
  });

  // place each claim near its hypothesis (via its incoming edge), else outer ring
  const hypById = new Map(hyps.map((n) => [n.id, n]));
  const parentOf = new Map<string, string>();
  edges.forEach((e) => parentOf.set(e.target, e.source));
  const rClaim = Math.min(w, h) * 0.4;
  const orphans: GraphNode[] = [];
  claims.forEach((n) => {
    const parent = hypById.get(parentOf.get(n.id) ?? "");
    if (parent) {
      const a = Math.atan2(parent.y - cy, parent.x - cx);
      const jitter = ((hash(n.id) % 100) / 100 - 0.5) * 0.9;
      n.x = cx + Math.cos(a + jitter) * rClaim;
      n.y = cy + Math.sin(a + jitter) * rClaim;
    } else {
      orphans.push(n);
    }
  });
  orphans.forEach((n, i) => {
    const a = (i / Math.max(orphans.length, 1)) * Math.PI * 2;
    n.x = cx + Math.cos(a) * rClaim;
    n.y = cy + Math.sin(a) * rClaim;
  });
}

/** Small deterministic hash for stable per-node jitter. */
function hash(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return Math.abs(h);
}

export function layoutGraph(
  nodes: GraphNode[],
  edges: GraphEdge[],
  opts: LayoutOpts,
): LaidOutGraph {
  const { width: w, height: h } = opts;
  const iterations = opts.iterations ?? 260;

  // reset velocity
  nodes.forEach((n) => {
    n.vx = 0;
    n.vy = 0;
  });
  seed(nodes, edges, w, h);

  if (nodes.length <= 1) {
    return { nodes, edges, width: w, height: h };
  }

  const area = w * h;
  const k = Math.sqrt(area / nodes.length) * 0.85; // ideal edge length
  const idx = new Map(nodes.map((n, i) => [n.id, i]));
  const edgeIdx = edges
    .map((e) => [idx.get(e.source), idx.get(e.target)] as const)
    .filter(([a, b]) => a !== undefined && b !== undefined) as [number, number][];

  let temp = Math.min(w, h) * 0.12;
  const cool = temp / (iterations + 1);

  for (let it = 0; it < iterations; it++) {
    // repulsive forces (all pairs)
    for (let i = 0; i < nodes.length; i++) {
      const a = nodes[i];
      let fx = 0;
      let fy = 0;
      for (let j = 0; j < nodes.length; j++) {
        if (i === j) continue;
        const b = nodes[j];
        let dx = a.x - b.x;
        let dy = a.y - b.y;
        let dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
        if (dist > k * 4) continue; // cutoff for performance
        const rep = (k * k) / dist;
        fx += (dx / dist) * rep;
        fy += (dy / dist) * rep;
      }
      a.vx = fx;
      a.vy = fy;
    }

    // attractive forces (edges)
    for (const [ai, bi] of edgeIdx) {
      const a = nodes[ai];
      const b = nodes[bi];
      let dx = a.x - b.x;
      let dy = a.y - b.y;
      let dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
      const att = (dist * dist) / k;
      const ux = dx / dist;
      const uy = dy / dist;
      a.vx -= ux * att;
      a.vy -= uy * att;
      b.vx += ux * att;
      b.vy += uy * att;
    }

    // gentle pull toward center (keeps the graph framed)
    for (const n of nodes) {
      n.vx += (w / 2 - n.x) * 0.008;
      n.vy += (h / 2 - n.y) * 0.008;
    }

    // integrate, capped by temperature
    for (const n of nodes) {
      if (n.kind === "root") continue; // pin the root at center
      const disp = Math.sqrt(n.vx * n.vx + n.vy * n.vy) || 0.01;
      const capped = Math.min(disp, temp);
      n.x += (n.vx / disp) * capped;
      n.y += (n.vy / disp) * capped;
      // keep inside the frame with padding
      const pad = 46;
      n.x = Math.max(pad, Math.min(w - pad, n.x));
      n.y = Math.max(pad, Math.min(h - pad, n.y));
    }
    temp -= cool;
  }

  return { nodes, edges, width: w, height: h };
}
