import { useEffect, useRef, useState } from "react";
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

interface Stat {
  label: string;
  value: string;
  note: string;
}

/* ---- ASCII code generation (the "revealed" layer) ---- */
const ASCII_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789(){}[]<>;:,._-+=!@#$%^&*|\\/\"'`~?";
const CODE_COLS = 34;
const CODE_ROWS = 9;

function generateCode(): string {
  let out = "";
  for (let r = 0; r < CODE_ROWS; r++) {
    for (let c = 0; c < CODE_COLS; c++) {
      out += ASCII_CHARS[Math.floor(Math.random() * ASCII_CHARS.length)];
    }
    out += "\n";
  }
  return out;
}

/* scramble an ASCII block, then settle on its original text */
function scrambleAscii(el: HTMLElement, original: string) {
  if (el.dataset.scrambling === "true") return;
  el.dataset.scrambling = "true";
  let n = 0;
  const max = 10;
  const timer = setInterval(() => {
    n++;
    if (n >= max) {
      clearInterval(timer);
      el.textContent = original;
      delete el.dataset.scrambling;
      return;
    }
    el.textContent = generateCode();
  }, 30);
}

/* ---- one card: normal layer + ascii layer, split by the scanner beam ---- */
function ScannerCard({ stat, ascii }: { stat: Stat; ascii: string }) {
  return (
    <div className="scan-card glow-card">
      {/* ascii (code) layer — revealed to the left of the beam */}
      <div className="scan-layer scan-ascii">
        <pre className="scan-code">{ascii}</pre>
      </div>
      {/* normal layer — visible to the right of the beam */}
      <div className="scan-layer scan-normal">
        <div className="scan-value display">{stat.value}</div>
        <div className="scan-label">{stat.label}</div>
        <div className="scan-note mono">{stat.note}</div>
      </div>
    </div>
  );
}

/** Real numbers pulled from the live API — streamed past a scanner beam
    that converts each card to raw code as it passes. */
export function LiveNumbers() {
  const [live, setLive] = useState<Live>({});
  const trackRef = useRef<HTMLDivElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const paused = useRef(false);

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
  const stats: Stat[] = [
    { label: "claims learned", value: String(live.memory?.claims ?? "—"), note: "across all runs" },
    { label: "domains classified", value: String(live.memory?.domains ?? "—"), note: "authority registry" },
    { label: "evidence embedded", value: sem?.available ? String(sem.evidence_chunks) : "—", note: "semantic index" },
    { label: "recurring quotes", value: String(live.memory?.recurring_quotes ?? "—"), note: "circular-citation seed" },
    { label: "calibration (ECE)", value: live.calibration?.n ? String(live.calibration.ece) : "—", note: `${live.calibration?.n ?? 0} labeled claims` },
    {
      label: "mean report dwell",
      value: eng && eng.reports_viewed > 0 ? `${eng.mean_dwell_s}s` : "—",
      note: eng ? `target >${eng.dwell_target_s}s` : "no views yet",
    },
  ];

  // stable ASCII block per card (regenerated only when the stat set changes)
  const asciiBlocks = useRef<string[]>([]);
  if (asciiBlocks.current.length !== stats.length) {
    asciiBlocks.current = stats.map(() => generateCode());
  }

  /* auto-scroll + clip-path split + ascii scramble at the beam */
  useEffect(() => {
    const track = trackRef.current;
    const viewport = viewportRef.current;
    if (!track || !viewport) return;

    let offset = 0;
    let last = performance.now();
    let raf = 0;
    const speed = 46; // px/s

    const step = (now: number) => {
      const dt = (now - last) / 1000;
      last = now;

      if (!paused.current) {
        offset -= speed * dt;
        const half = track.scrollWidth / 2;
        if (half > 0 && Math.abs(offset) >= half) offset += half;
        track.style.transform = `translateX(${offset}px)`;
      }

      const vp = viewport.getBoundingClientRect();
      const scannerX = vp.left + vp.width / 2;
      const beamHalf = 5; // half the beam's effective width

      track.querySelectorAll<HTMLElement>(".scan-card").forEach((card, idx) => {
        const rect = card.getBoundingClientRect();
        const normal = card.querySelector<HTMLElement>(".scan-normal");
        const ascii = card.querySelector<HTMLElement>(".scan-ascii");
        const code = card.querySelector<HTMLElement>(".scan-code");
        if (!normal || !ascii) return;

        if (rect.left < scannerX + beamHalf && rect.right > scannerX - beamHalf) {
          // card is under the beam → split it
          const cutLeft = Math.max(scannerX - beamHalf - rect.left, 0);
          const cutRight = Math.min(scannerX + beamHalf - rect.left, rect.width);
          normal.style.setProperty("--clip-right", `${(cutLeft / rect.width) * 100}%`);
          ascii.style.setProperty("--clip-left", `${(cutRight / rect.width) * 100}%`);
          if (card.dataset.scanned !== "true" && code) {
            card.dataset.scanned = "true";
            scrambleAscii(code, asciiBlocks.current[idx % asciiBlocks.current.length] ?? "");
          }
        } else if (rect.right < scannerX - beamHalf) {
          // fully to the left of the beam → all code
          normal.style.setProperty("--clip-right", "100%");
          ascii.style.setProperty("--clip-left", "100%");
        } else {
          // fully to the right of the beam → all normal
          normal.style.setProperty("--clip-right", "0%");
          ascii.style.setProperty("--clip-left", "0%");
          delete card.dataset.scanned;
        }
      });

      raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [live]);

  return (
    <section className="numbers" id="numbers">
      <div className="wrap">
        <Reveal>
          <span className="eyebrow">the system, measured</span>
          <h2 className="display section-title">It publishes its own numbers.</h2>
          <p className="section-sub">
            A system that shows its calibration error is more trustworthy than one
            that hides it. These are live, from the running court.
          </p>
        </Reveal>
      </div>

      {/* scanner stream */}
      <Reveal>
        <div
          className="scan-viewport"
          ref={viewportRef}
          onMouseEnter={() => { paused.current = true; }}
          onMouseLeave={() => { paused.current = false; }}
        >
          <div className="scan-beam" aria-hidden />
          <div className="scan-track" ref={trackRef}>
            {[...stats, ...stats].map((s, i) => (
              <ScannerCard key={`${s.label}-${i}`} stat={s} ascii={asciiBlocks.current[i % asciiBlocks.current.length] ?? ""} />
            ))}
          </div>
          <div className="scan-fade scan-fade-l" aria-hidden />
          <div className="scan-fade scan-fade-r" aria-hidden />
        </div>
      </Reveal>

      {live.health && (
        <Reveal>
          <div className="wrap">
            <div className="numbers-model mono">
              model <b>{live.health.llm_model}</b>
              {live.health.llm_fallback && <> · fallback <b>{live.health.llm_fallback}</b></>}
              {" "}· {live.health.tavily_configured ? "evidence online" : "evidence offline"}
            </div>
          </div>
        </Reveal>
      )}
    </section>
  );
}
