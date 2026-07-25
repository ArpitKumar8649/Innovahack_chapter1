import { useEffect, useRef, useState } from "react";
import type { RunState } from "../../hooks/useRun";

const LEVEL_COLOR: Record<string, string> = {
  info: "var(--ink-2)",
  stage: "var(--gold)",
  warn: "var(--amber)",
  error: "var(--red)",
};

function fmt(ts: number): string {
  return new Date(ts).toLocaleTimeString([], { hour12: false });
}

/** A live console mirroring the backend's stage/agent logs. */
export function Terminal({ state }: { state: RunState }) {
  const endRef = useRef<HTMLDivElement>(null);
  const [follow, setFollow] = useState(true);

  useEffect(() => {
    if (follow) endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [state.logs.length, follow]);

  return (
    <section className="terminal">
      <div className="panel-head term-head">
        <span className="panel-title mono">~/veritasai — pipeline</span>
        <div className="term-controls">
          <button
            className="term-toggle mono"
            onClick={() => setFollow((f) => !f)}
            title="toggle auto-scroll"
          >
            {follow ? "● follow" : "○ follow"}
          </button>
          <span className="term-count mono">{state.logs.length} lines</span>
        </div>
      </div>

      <div className="term-scroll" onScroll={(e) => {
        const el = e.currentTarget;
        const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
        if (atBottom !== follow) setFollow(atBottom);
      }}>
        {state.logs.length === 0 && (
          <div className="term-line term-empty">
            <span className="term-prompt">$</span> veritasai --watch <span className="term-cursor">▊</span>
          </div>
        )}
        {state.logs.map((l) => (
          <div key={l.id} className="term-line">
            <span className="term-time">{fmt(l.ts)}</span>
            <span className="term-stage">[{l.stage}]</span>
            <span className="term-text" style={{ color: LEVEL_COLOR[l.level] }}>{l.text}</span>
          </div>
        ))}
        {state.status === "running" && (
          <div className="term-line">
            <span className="term-prompt">$</span> <span className="term-cursor">▊</span>
          </div>
        )}
        <div ref={endRef} />
      </div>
    </section>
  );
}
