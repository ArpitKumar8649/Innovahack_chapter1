import { useEffect, useState } from "react";
import { Reveal } from "../ui/Reveal";
import { api } from "../../lib/api";
import type { Calibration, Engagement, Health, MemoryStats, SemanticStats } from "../../types";

interface Live {
  memory?: MemoryStats;
  calibration?: Calibration;
  health?: Health;
  engagement?: Engagement;
  semantic?: SemanticStats;
}

/** Real numbers pulled from the live API — not marketing. */
export function LiveNumbers() {
  const [live, setLive] = useState<Live>({});

  useEffect(() => {
    Promise.allSettled([
      api.memory(), api.calibration(), api.health(), api.analytics(), api.semantic(),
    ]).then(([m, c, h, e, s]) => {
      setLive({
        memory: m.status === "fulfilled" ? m.value : undefined,
        calibration: c.status === "fulfilled" ? c.value : undefined,
        health: h.status === "fulfilled" ? h.value : undefined,
        engagement: e.status === "fulfilled" ? e.value : undefined,
        semantic: s.status === "fulfilled" ? s.value : undefined,
      });
    });
  }, []);

  const eng = live.engagement;
  const sem = live.semantic;
  const stats = [
    { label: "claims learned", value: live.memory?.claims ?? "—", note: "across all runs" },
    { label: "domains classified", value: live.memory?.domains ?? "—", note: "authority registry" },
    { label: "evidence embedded", value: sem?.available ? sem.evidence_chunks : "—", note: "semantic index (Phase 6)" },
    { label: "recurring quotes", value: live.memory?.recurring_quotes ?? "—", note: "circular-citation seed" },
    { label: "calibration (ECE)", value: live.calibration?.n ? live.calibration.ece : "—", note: `${live.calibration?.n ?? 0} labeled claims` },
    {
      label: "mean report dwell",
      value: eng && eng.reports_viewed > 0 ? `${eng.mean_dwell_s}s` : "—",
      note: eng ? `target >${eng.dwell_target_s}s · ${eng.reports_viewed} views` : "no views yet",
    },
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
