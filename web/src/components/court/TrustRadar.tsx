import type { TrustRadar } from "../../types";

const AXES: { key: keyof TrustRadar; label: string }[] = [
  { key: "agreement", label: "Agreement" },
  { key: "authority", label: "Authority" },
  { key: "coverage", label: "Coverage" },
  { key: "diversity", label: "Diversity" },
  { key: "recency", label: "Recency" },
];

const SIZE = 240;
const CX = SIZE / 2;
const CY = SIZE / 2;
const R = 88;
const RINGS = [0.25, 0.5, 0.75, 1.0];

function point(axisIndex: number, value: number): [number, number] {
  const angle = (-90 + axisIndex * (360 / AXES.length)) * (Math.PI / 180);
  return [CX + R * value * Math.cos(angle), CY + R * value * Math.sin(angle)];
}

/** 5-axis trust radar — the report's confidence profile, computed not vibes. */
export function TrustRadarChart({ radar }: { radar: TrustRadar }) {
  const ringPaths = RINGS.map((rv) =>
    AXES.map((_, i) => point(i, rv)).map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" "),
  );
  const dataPoints = AXES.map((a, i) => point(i, radar[a.key] ?? 0));
  const dataPath = dataPoints.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");

  return (
    <div className="trust-radar">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="radar-svg" role="img" aria-label="Trust radar">
        {ringPaths.map((pts, i) => (
          <polygon key={i} points={pts} className="radar-ring" />
        ))}
        {AXES.map((_, i) => {
          const [x, y] = point(i, 1);
          return <line key={i} x1={CX} y1={CY} x2={x} y2={y} className="radar-axis" />;
        })}
        <polygon points={dataPath} className="radar-data" />
        {dataPoints.map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r={3} className="radar-dot" />
        ))}
        {AXES.map((a, i) => {
          const [x, y] = point(i, 1.22);
          return (
            <text key={a.key} x={x} y={y} className="radar-label" textAnchor="middle" dominantBaseline="middle">
              {a.label}
            </text>
          );
        })}
      </svg>
      <div className="radar-legend">
        {AXES.map((a) => (
          <div key={a.key} className="radar-legend-row">
            <span className="radar-legend-label">{a.label}</span>
            <span className="radar-legend-bar">
              <span className="radar-legend-fill" style={{ width: `${Math.round((radar[a.key] ?? 0) * 100)}%` }} />
            </span>
            <span className="radar-legend-val mono">{Math.round((radar[a.key] ?? 0) * 100)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
