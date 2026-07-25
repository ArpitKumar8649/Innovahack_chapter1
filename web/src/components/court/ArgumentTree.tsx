import { useMemo, useState } from "react";
import type { ArgumentTree, Stance, Status, TreeEdge } from "../../types";

/* ---- layout constants ---- */
const SLOT_W = 208; // horizontal slot per leaf
const NODE_W = 192;      // rendered node box width
const LEVEL_H = 128;     // vertical spacing between levels
const NODE_H = 108;      // rendered node box height
const PAD = 24;

interface TNode {
  id: string;
  label: string;
  kind: "root" | "hypothesis" | "supports" | "attacks";
  status?: Status;
  confidence?: number;
  verdicts?: Record<string, Stance>;
  sourceIds?: number[];
  weight?: number;
  isWeakest?: boolean;
  plausibility?: number;
  x: number;
  y: number;
  children: TNode[];
}

function edgeNode(e: TreeEdge, kind: "supports" | "attacks", weakestClaimId?: number): TNode {
  return {
    id: `e-${e.claim_id}-${kind}`,
    label: e.text,
    kind,
    status: e.status,
    confidence: e.confidence,
    verdicts: e.verdicts,
    sourceIds: e.source_ids,
    weight: e.weight,
    isWeakest: weakestClaimId != null && e.claim_id === weakestClaimId,
    x: 0, y: 0, children: [],
  };
}

function buildTree(tree: ArgumentTree): TNode {
  const weakestClaimId = tree.weakest_link?.claim_id;
  return {
    id: "root",
    label: tree.root?.text ?? "Investigation",
    kind: "root",
    status: tree.root?.status,
    confidence: tree.root?.confidence,
    verdicts: tree.root?.verdicts,
    x: 0, y: 0,
    children: tree.hypotheses.map((h) => ({
      id: h.id,
      label: h.statement,
      kind: "hypothesis" as const,
      verdicts: h.verdicts,
      plausibility: h.plausibility,
      x: 0, y: 0,
      children: [
        ...h.supports.map((e) => edgeNode(e, "supports", weakestClaimId)),
        ...h.attacks.map((e) => edgeNode(e, "attacks", weakestClaimId)),
      ],
    })),
  };
}

/** Tidy tree layout: leaves get sequential x slots, parents center above children. */
function layout(node: TNode, depth: number, cursor: { x: number }, collapsed: Set<string>) {
  node.y = PAD + depth * LEVEL_H;
  const isCollapsed = collapsed.has(node.id);
  if (isCollapsed || node.children.length === 0) {
    node.x = cursor.x;
    cursor.x += SLOT_W;
    return;
  }
  for (const child of node.children) layout(child, depth + 1, cursor, collapsed);
  const first = node.children[0].x;
  const last = node.children[node.children.length - 1].x;
  node.x = (first + last) / 2;
}

function flatten(node: TNode, collapsed: Set<string>, acc: TNode[] = []): TNode[] {
  acc.push(node);
  if (!collapsed.has(node.id)) {
    for (const c of node.children) flatten(c, collapsed, acc);
  }
  return acc;
}

function edgePath(x1: number, y1: number, x2: number, y2: number): string {
  const midY = (y1 + y2) / 2;
  return `M ${x1} ${y1} C ${x1} ${midY}, ${x2} ${midY}, ${x2} ${y2}`;
}

const VERIFIER_COLOR: Record<string, string> = {
  A: "var(--green)", B: "var(--red)", C: "var(--amber)", J: "var(--gold)", M: "var(--accent-2)",
};

function VerdictChips({ verdicts }: { verdicts?: Record<string, Stance> }) {
  if (!verdicts) return null;
  const entries = Object.entries(verdicts);
  if (!entries.length) return null;
  return (
    <span className="tree-verdicts">
      {entries.map(([tag, stance]) => (
        <span key={tag} className="tree-v" style={{ color: VERIFIER_COLOR[tag] ?? "var(--ink-3)" }}>
          {tag}{stance === "support" ? "✓" : stance === "refute" ? "✗" : "–"}
        </span>
      ))}
    </span>
  );
}

export function ArgumentTreeView({ tree }: { tree: ArgumentTree }) {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());

  const { nodes, width, height } = useMemo(() => {
    const root = buildTree(tree);
    const cursor = { x: PAD };
    layout(root, 0, cursor, collapsed);
    const all = flatten(root, collapsed);
    const maxDepth = Math.max(...all.map((n) => n.y));
    return {
      nodes: all,
      width: Math.max(cursor.x + PAD, 320),
      height: maxDepth + NODE_H + PAD,
    };
  }, [tree, collapsed]);

  const toggle = (id: string) =>
    setCollapsed((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  if (!tree.root) return null;

  return (
    <div className="arg-tree-wrap">
      <div className="arg-tree-scroll">
        <svg width={width} height={height} className="arg-tree-svg">
          {/* edges first (under nodes) */}
          {nodes.map((n) =>
            n.children.map((c) => (
              <path
                key={`${n.id}-${c.id}`}
                d={edgePath(n.x, n.y + NODE_H, c.x, c.y)}
                className={`tree-edge kind-${c.kind}`}
              />
            )),
          )}
          {/* nodes */}
          {nodes.map((n) => {
            const collapsedHere = collapsed.has(n.id) && n.children.length > 0;
            return (
              <foreignObject
                key={n.id}
                x={n.x - NODE_W / 2}
                y={n.y}
                width={NODE_W}
                height={NODE_H}
              >
                <div className={`tree-node kind-${n.kind} ${n.isWeakest ? "weakest" : ""}`}>
                  {n.kind === "root" && (
                    <>
                      <span className="tree-kind">◈ claim under trial</span>
                      <div className="tree-label">{n.label}</div>
                      <div className="tree-meta">
                        <span className={`status-pill status-${n.status}`}>{n.status}</span>
                        <span className="tree-conf mono">{n.confidence}%</span>
                        <VerdictChips verdicts={n.verdicts} />
                      </div>
                    </>
                  )}
                  {n.kind === "hypothesis" && (
                    <>
                      <div className="tree-hyp-head">
                        <span className="tree-kind">{n.id}</span>
                        <VerdictChips verdicts={n.verdicts} />
                        {n.children.length > 0 && (
                          <button className="tree-toggle mono" onClick={() => toggle(n.id)}>
                            {collapsedHere ? `▸ ${n.children.length}` : "▾"}
                          </button>
                        )}
                      </div>
                      <div className="tree-label">{n.label}</div>
                      <div className="tree-meta">
                        <span className="tree-plaus mono">
                          prior {Math.round((n.plausibility ?? 0) * 100)}%
                        </span>
                        {!collapsedHere && (
                          <span className="tree-counts mono">
                            {n.children.filter((c) => c.kind === "supports").length}▲{" "}
                            {n.children.filter((c) => c.kind === "attacks").length}▼
                          </span>
                        )}
                      </div>
                    </>
                  )}
                  {(n.kind === "supports" || n.kind === "attacks") && (
                    <>
                      <span className={`tree-relation kind-${n.kind}`}>
                        {n.kind === "supports" ? "▲ supports" : "▼ attacks"}
                        {n.isWeakest && <em className="tree-weak-flag">weakest link</em>}
                      </span>
                      <div className="tree-label">{n.label}</div>
                      <div className="tree-meta">
                        <span className={`status-pill status-${n.status}`}>{n.status}</span>
                        <span className="tree-conf mono">{n.confidence}%</span>
                        {n.sourceIds?.map((s) => (
                          <span key={s} className="tree-src mono">[{s}]</span>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              </foreignObject>
            );
          })}
        </svg>
      </div>

      {tree.unattributed.length > 0 && (
        <div className="tree-unattributed">
          <span className="tree-kind">ungrouped claims</span>
          {tree.unattributed.map((u) => (
            <span key={u.claim_id} className="tree-unattr-chip">
              <span className={`status-pill status-${u.status}`}>{u.status}</span>
              {u.text}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
