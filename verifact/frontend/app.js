/* VeriFact frontend — SSE live pipeline + report rendering. No dependencies. */
(() => {
  const $ = (id) => document.getElementById(id);
  const els = {
    form: $("topicForm"), input: $("topicInput"), runBtn: $("runBtn"),
    hero: $("heroSection"), pipelineSection: $("pipelineSection"),
    pipeline: $("pipeline"), liveFeed: $("liveFeed"), liveClaims: $("liveClaims"),
    reportSection: $("reportSection"), reportTopic: $("reportTopic"),
    reportStats: $("reportStats"), summaryCard: $("summaryCard"),
    contradictionsBlock: $("contradictionsBlock"), claimsList: $("claimsList"),
    claimCount: $("claimCount"), sourcesList: $("sourcesList"),
    sourceCount: $("sourceCount"), gaugeFg: $("gaugeFg"), trustValue: $("trustValue"),
    historyList: $("historyList"), historySection: $("historySection"),
    errorBanner: $("errorBanner"),
  };

  const STAGE_AGENT = {
    plan: "planner", research: "researcher", extract: "extractor",
    verify: null, contradictions: "contradiction", report: "writer",
  };
  const CIRC = 2 * Math.PI * 52;
  let es = null;
  let runState = null; // {sources: Map(id→source), claims: Map(id→el)}

  // ---------- helpers ----------
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const time = () => new Date().toLocaleTimeString([], { hour12: false });

  function feed(html, cls = "") {
    const d = document.createElement("div");
    d.className = "feed-item " + cls;
    d.innerHTML = `<span class="feed-time">${time()}</span>${html}`;
    els.liveFeed.appendChild(d);
    els.liveFeed.scrollTop = els.liveFeed.scrollHeight;
  }

  function setAgent(name, state) {
    const el = document.querySelector(`.ab[data-agent="${name}"]`);
    if (el) el.className = `ab ${state}`;
  }

  function setStage(stage, state) {
    const el = els.pipeline.querySelector(`[data-stage="${stage}"]`);
    if (el) el.className = `pstage ${state}`;
  }

  function statusClass(status) {
    return { verified: "st-verified", disputed: "st-disputed",
             unverified: "st-unverified", contradicted: "st-contradicted" }[status] || "st-pending";
  }

  function citeLinks(text, sources) {
    return esc(text).replace(/\[(\d+)\]/g, (m, n) => {
      const s = sources.get(Number(n));
      return s ? `<a class="cite" href="${esc(s.url)}" target="_blank" rel="noopener" title="${esc(s.title)}">[${n}]</a>` : m;
    });
  }

  // ---------- live claim chips ----------
  function renderLiveClaim(claim) {
    const el = document.createElement("div");
    el.className = "live-claim";
    el.id = `lc-${claim.id}`;
    el.innerHTML = `
      <div class="lc-text">${esc(claim.text)}</div>
      <div class="lc-badges">
        <span class="vb vb-A" title="Verifier A — Evidentialist">A ·</span>
        <span class="vb vb-B" title="Verifier B — Skeptic">B ·</span>
        <span class="vb vb-C" title="Verifier C — Contextualist">C ·</span>
        <span class="lc-conf"></span>
      </div>`;
    els.liveClaims.appendChild(el);
  }

  function updateVerdict(claimId, verifier, stance) {
    const badge = document.querySelector(`#lc-${claimId} .vb-${verifier}`);
    if (!badge) return;
    badge.textContent = `${verifier} ${stance === "support" ? "✓" : stance === "refute" ? "✗" : "–"}`;
    badge.classList.add(`v-${stance}`);
    if (stance === "refute") {
      const card = document.getElementById(`lc-${claimId}`);
      if (card) card.classList.add("has-refute");
    }
  }

  function updateScore(claimId, confidence, status) {
    const conf = document.querySelector(`#lc-${claimId} .lc-conf`);
    if (!conf) return;
    // "contradicted" means high confidence the claim is FALSE — phrase it clearly
    const label = status === "contradicted" ? `✗ refuted ${confidence}%`
                : status === "verified" ? `✓ ${confidence}%`
                : `${confidence}% ${status}`;
    conf.innerHTML = `<span class="conf-pill ${statusClass(status)}">${label}</span>`;
  }

  // ---------- report rendering ----------
  function renderReport(report) {
    const sources = new Map(report.sources.map((s) => [s.id, s]));

    els.reportTopic.textContent = report.topic;
    els.reportStats.textContent =
      `${report.claims.length} claims · ${report.sources.length} sources · ` +
      `${report.contradictions.length} contradiction${report.contradictions.length === 1 ? "" : "s"} found`;

    // trust gauge
    els.gaugeFg.style.strokeDasharray = CIRC;
    els.gaugeFg.style.strokeDashoffset = CIRC * (1 - report.trust_score / 100);
    els.gaugeFg.classList.remove("g-low", "g-mid", "g-high");
    els.gaugeFg.classList.add(report.trust_score >= 75 ? "g-high" : report.trust_score >= 50 ? "g-mid" : "g-low");
    animateNumber(els.trustValue, report.trust_score);

    // summary
    els.summaryCard.innerHTML =
      `<h4 class="section-h">Executive summary</h4><p>${citeLinks(report.summary, sources)}</p>`;

    // contradictions
    if (report.contradictions.length) {
      const claimById = new Map(report.claims.map((c) => [c.id, c]));
      els.contradictionsBlock.innerHTML = `<h4 class="section-h contra-h">⚠️ Contradictions &amp; corrections</h4>` +
        report.contradictions.map((cd) => {
          const c = claimById.get(cd.claim_id);
          return `<div class="contra-card">
            <div class="contra-kind">${esc(cd.kind.replace(/_/g, " "))}</div>
            <div class="contra-claim">${esc(c ? c.text : `Claim ${cd.claim_id}`)}</div>
            <p>${citeLinks(cd.description, sources)}</p>
          </div>`;
        }).join("");
    } else {
      els.contradictionsBlock.innerHTML =
        `<div class="no-contra">✅ No contradictions detected — the verifier panel reached consensus on all claims.</div>`;
    }

    // claims
    els.claimCount.textContent = `(${report.claims.length})`;
    els.claimsList.innerHTML = report.claims.map((c) => {
      const verdicts = (c.verdicts || []).map((v) =>
        `<span class="vb v-${v.stance}" title="${esc(v.reasoning)}">${v.verifier} ${v.stance === "support" ? "✓" : v.stance === "refute" ? "✗" : "–"}</span>`
      ).join("");
      const cites = (c.source_ids || []).map((n) => {
        const s = sources.get(n);
        return s ? `<a class="cite" href="${esc(s.url)}" target="_blank" rel="noopener">[${n}]</a>` : "";
      }).join("");
      return `<div class="claim-card ${statusClass(c.status)}">
        <div class="claim-head">
          <span class="claim-status ${statusClass(c.status)}">${c.status}</span>
          <span class="claim-type">${esc(c.claim_type)}</span>
          <div class="conf-bar"><div class="conf-fill ${statusClass(c.status)}" style="width:${c.confidence}%"></div>
            <span class="conf-num">${c.confidence}%</span></div>
        </div>
        <p class="claim-text">${esc(c.text)} ${cites}</p>
        <div class="claim-foot">
          <div class="claim-verdicts">${verdicts}</div>
          ${c.verification_note ? `<div class="claim-note">${esc(c.verification_note)}</div>` : ""}
        </div>
      </div>`;
    }).join("");

    // sources
    els.sourceCount.textContent = `(${report.sources.length})`;
    els.sourcesList.innerHTML = report.sources.map((s) => {
      let host = s.url;
      try { host = new URL(s.url).hostname; } catch { /* keep raw url */ }
      return `<a class="source-card" href="${esc(s.url)}" target="_blank" rel="noopener">
        <span class="src-id">[${s.id}]</span>
        <span class="src-title">${esc(s.title)}</span>
        <span class="src-url">${esc(host)}</span>
      </a>`;
    }).join("");

    els.reportSection.classList.remove("hidden");
  }

  function animateNumber(el, target) {
    let v = 0;
    const step = Math.max(1, Math.round(target / 30));
    const t = setInterval(() => {
      v = Math.min(target, v + step);
      el.textContent = v;
      if (v >= target) clearInterval(t);
    }, 25);
  }

  // ---------- SSE run ----------
  function startRun(runId) {
    runState = { sources: new Map(), claims: new Map() };
    els.liveFeed.innerHTML = "";
    els.liveClaims.innerHTML = "";
    els.reportSection.classList.add("hidden");
    els.contradictionsBlock.innerHTML = "";
    els.pipelineSection.classList.remove("hidden");
    els.hero.classList.add("dimmed");
    els.errorBanner.classList.add("hidden");
    document.querySelectorAll(".ab").forEach((a) => a.className = "ab");
    document.querySelectorAll(".pstage").forEach((p) => p.className = "pstage");

    if (es) es.close();
    es = new EventSource(`/api/research/${runId}/stream`);

    const on = (name, fn) => es.addEventListener(name, (e) => fn(JSON.parse(e.data)));

    on("stage", (d) => {
      setStage(d.stage, d.status);
      const agent = STAGE_AGENT[d.stage];
      if (agent) setAgent(agent, d.status === "started" ? "active" : "done");
      if (d.stage === "verify" && d.status === "started") {
        ["verifier-a", "verifier-b", "verifier-c"].forEach((a) => setAgent(a, "active"));
        feed("⚖️ <b>3 adversarial verifiers</b> engaged in parallel — evidentialist, skeptic, contextualist");
      }
      if (d.stage === "verify" && d.status === "done") {
        ["verifier-a", "verifier-b", "verifier-c"].forEach((a) => setAgent(a, "done"));
      }
      feed(`▶ stage <b>${d.stage}</b> ${d.status}`);
    });

    on("plan", (d) => feed(`📋 plan: ${(d.subtopics || []).map(esc).join(" · ")}`));
    on("log", (d) => feed(`· ${esc(d.message)}`, "feed-log"));

    on("sources", (d) => {
      d.sources.forEach((s) => runState.sources.set(s.id, s));
      feed(`🔍 <b>${d.sources.length} sources</b> retrieved from web search`);
    });

    on("claims", (d) => {
      d.claims.forEach((c) => { runState.claims.set(c.id, c); renderLiveClaim(c); });
      feed(`🧩 decomposed into <b>${d.claims.length} atomic claims</b>`);
    });

    on("verdict", (d) => updateVerdict(d.claim_id, d.verifier, d.stance));

    on("score", (d) => {
      updateScore(d.claim_id, d.confidence, d.status);
      if (d.status === "contradicted")
        feed(`✗ claim ${d.claim_id} <b>REFUTED</b> (${d.confidence}%)`, "feed-refute");
    });

    on("contradiction", (d) =>
      feed(`⚠️ <b>contradiction</b> on claim ${d.claim_id}: ${esc(d.description.slice(0, 120))}…`, "feed-refute"));

    on("report", (d) => renderReport(d));

    on("done", (d) => {
      feed(`✅ done in <b>${d.elapsed_s}s</b> — ${d.claims} claims, ${d.sources} sources, ${d.contradictions} contradictions`);
      els.runBtn.disabled = false;
      els.runBtn.textContent = "Verify →";
      loadHistory();
    });

    on("error", (d) => {
      els.errorBanner.textContent = "⚠ " + d.message;
      els.errorBanner.classList.remove("hidden");
      els.runBtn.disabled = false;
      els.runBtn.textContent = "Verify →";
    });

    on("end", () => es.close());
    es.onerror = () => { /* EventSource retries; end event closes cleanly */ };
  }

  // ---------- events ----------
  els.form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const topic = els.input.value.trim();
    if (!topic) return;
    els.runBtn.disabled = true;
    els.runBtn.textContent = "Running…";
    try {
      const r = await fetch("/api/research", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ topic }),
      });
      const d = await r.json();
      startRun(d.run_id);
    } catch (err) {
      els.errorBanner.textContent = "⚠ Could not start run: " + err;
      els.errorBanner.classList.remove("hidden");
      els.runBtn.disabled = false;
      els.runBtn.textContent = "Verify →";
    }
  });

  document.querySelectorAll(".chip").forEach((chip) =>
    chip.addEventListener("click", () => {
      els.input.value = chip.textContent;
      els.form.requestSubmit();
    }));

  // ---------- history ----------
  async function loadHistory() {
    try {
      const r = await fetch("/api/runs");
      const d = await r.json();
      const runs = (d.runs || []).filter((x) => !x.error);
      if (!runs.length) { els.historySection.classList.add("hidden"); return; }
      els.historySection.classList.remove("hidden");
      els.historyList.innerHTML = runs.map((x) =>
        `<button class="hist-item" data-id="${esc(x.run_id)}">
          <span class="hist-topic">${esc(x.topic)}</span>
          <span class="hist-score ${x.trust_score >= 75 ? "g-high" : x.trust_score >= 50 ? "g-mid" : "g-low"}">${x.trust_score ?? "–"}</span>
        </button>`).join("");
      els.historyList.querySelectorAll(".hist-item").forEach((btn) =>
        btn.addEventListener("click", async () => {
          const r2 = await fetch(`/api/research/${btn.dataset.id}`);
          const d2 = await r2.json();
          if (d2.report) {
            els.pipelineSection.classList.add("hidden");
            els.hero.classList.remove("dimmed");
            els.input.value = d2.topic;
            renderReport(d2.report);
            window.scrollTo({ top: 0, behavior: "smooth" });
          }
        }));
    } catch { /* history is best-effort */ }
  }

  loadHistory();
})();
