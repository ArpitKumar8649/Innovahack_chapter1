import { useEffect, useState } from "react";

const R = 52;
const CIRC = 2 * Math.PI * R;

/** Animated trust-score ring. */
export function TrustGauge({ score }: { score: number }) {
  const [shown, setShown] = useState(0);

  useEffect(() => {
    let v = 0;
    const step = Math.max(1, Math.round(score / 30));
    const t = setInterval(() => {
      v = Math.min(score, v + step);
      setShown(v);
      if (v >= score) clearInterval(t);
    }, 25);
    return () => clearInterval(t);
  }, [score]);

  const band = score >= 75 ? "g-high" : score >= 50 ? "g-mid" : "g-low";

  return (
    <div className="trust-gauge">
      <svg viewBox="0 0 120 120">
        <circle className="gauge-bg" cx="60" cy="60" r={R} />
        <circle
          className={`gauge-fg ${band}`}
          cx="60" cy="60" r={R}
          strokeDasharray={CIRC}
          strokeDashoffset={CIRC * (1 - shown / 100)}
        />
      </svg>
      <div className="gauge-label">
        <strong>{shown}</strong>
        <span>trust</span>
      </div>
    </div>
  );
}
