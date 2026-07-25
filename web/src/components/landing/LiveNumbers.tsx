import { useEffect, useState } from "react";
import { Reveal } from "../ui/Reveal";
import { api } from "../../lib/api";
import type { Calibration, Health, MemoryStats } from "../../types";

interface Live {
  memory?: MemoryStats;
  calibration?: Calibration;
  health?: Health;
}

/** Real numbers pulled from the live API — not marketing. */
export function LiveNumbers() {
  const [live, setLive] = useState<Live>({});

  useEffect(() => {
    Promise.allSettled([
      api.memory(), api.calibration(), api.health(),
    ]).then(([m, c, h]) => {
      setLive({
        memory: m.status === "fulfilled" ? m.value : undefined,
        calibration: c.status === "fulfilled" ? c.value : undefined,
        health: h.status === "fulfilled" ? h.value : undefined,
      });
    });
  }, []);

  const stats = [
    { label: "claims learned", value: live.memory?.claims ?? "—", note: "across all runs" },
    { label: "domains classified", value: live.memory?.domains ?? "—", note: "authority registry" },
    { label: "recurring quotes", value: live.memory?.recurring_quotes ?? "—", note: "circular-citation seed" },
    { label: "calibration (ECE)", value: live.calibration?.n ? live.calibration.ece : "—", note: `${live.calibration?.n ?? 0} labeled claims` },
  ];

  return (
    <section className="numbers wrap" id="numbers">
      <Reveal>
        <span className="eyebrow">the system, measured</span>
        <h2 className="display section-title">It publishes its own numbers.</h2>
        <p className="section-sub">
          A system that shows its calibration error is more trustworthy than one
          that hides it. These are live, from the running court.
        </p>
      </Reveal>
      <div className="numbers-grid">
        {stats.map((s, i) => (
          <Reveal key={s.label} delay={i * 80}>
            <div className="stat-tile">
              <div className="stat-value display">{s.value}</div>
              <div className="stat-label">{s.label}</div>
              <div className="stat-note mono">{s.note}</div>
            </div>
          </Reveal>
        ))}
      </div>
      {live.health && (
        <Reveal>
          <div className="numbers-model mono">
            model <b>{live.health.llm_model}</b>
            {live.health.llm_fallback && <> · fallback <b>{live.health.llm_fallback}</b></>}
            {" "}· {live.health.tavily_configured ? "evidence online" : "evidence offline"}
          </div>
        </Reveal>
      )}
    </section>
  );
}
