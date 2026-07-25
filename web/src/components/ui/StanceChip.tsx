import type { Stance } from "../../types";

const GLYPH: Record<Stance, string> = { support: "✓", refute: "✗", insufficient: "–" };

export function StanceChip({ stance, spanValid, label }: {
  stance: Stance; spanValid?: boolean; label?: string;
}) {
  return (
    <span className={`stance-chip st-${stance}`} title={spanValid === false ? "quoted span not found in corpus — verdict voided" : undefined}>
      {GLYPH[stance]} {label ?? stance}
      {spanValid === false ? " ∅" : ""}
    </span>
  );
}
