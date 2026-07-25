/* VeritasAI frontend — Debate Theater + Evidence Inspector.
   Client-side Merkle verification mirrors backend/evidence.py exactly. */
(() => {
  const $ = (id) => document.getElementById(id);
  const els = {
    form: $("topicForm"), input: $("topicInput"), runBtn: $("runBtn"),
    hero: $("heroSection"), pipelineSection: $("pipelineSection"),
    pipeline: $("pipeline"), liveFeed: $("liveFeed"), liveClaims: $("liveClaims"),
    hypothesisCards: $("hypothesisCards"),
    reportSection: $("reportSection"), reportTopic: $("reportTopic"),
    reportStats: $("reportStats"), summaryCard: $("summaryCard"),
    contradictionsBlock: $("contradictionsBlock"), claimsList: $("claimsList"),
    claimCount: $("claimCount"), sourcesList: $("sourcesList"),
    sourceCount: $("sourceCount"), gaugeFg: $("gaugeFg"), trustValue: $("trustValue"),
    verifyBadge: $("verifyBadge"), verifyText: $("verifyText"),
    historyList: $("historyList"), historySection: $("historySection"),
    errorBanner: $("errorBanner"),
    modal: $("inspectorModal"), modalClose: $("modalClose"), inspectorBody: $("inspectorBody"),
  };

  const STAGE_AGENT = {
    hypothesize: "murli", research: "researcher", extract: "extractor",
    verify: null, hallucinations: "hallucination",
    contradictions: "contradiction", report: "writer",
  };
  const TIER_LABEL = { 1: "primary / peer-reviewed", 2: "established reference",
    3: "reputable media", 4: "blog / aggregator", 5: "social / UGC" };
  const CIRC = 2 * Math.PI * 52;
  let es = null;
  let currentReport = null;   // full report for the inspector
  let currentRunId = null;

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
  const setAgent = (name, state) => {
    const el = document.querySelector(`.ab[data-agent="${name}"]`);
    if (el) el.className = `ab ${state}`;
  };
  const setStage = (stage, state) => {
    const el = els.pipeline.querySelector(`[data-stage="${stage}"]`);
    if (el) el.className = `pstage ${state}`;
  };
  const stCls = (s) => `st-${String(s || "pending").toLowerCase()}`;

  function citeLinks(text, sources) {
    return esc(text).replace(/\[(\d+)\]/g, (m, n) => {
      const s = sources.get(Number(n));
      return s ? `<a class="cite" href="${esc(s.url)}" target="_blank" rel="noopener" title="${esc(s.title)}">[${n}]</a>` : m;
    });
  }

  // ---------- client-side crypto (mirrors evidence.py) ----------
  async function sha256Hex(text) {
    const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
    return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
  }
  async function verifyMerkle(leafHash, proof, root) {
    let cur = leafHash;
    for (const p of proof || []) {
      cur = await sha256Hex(p.side === "right" ? cur + p.hash : p.hash + cur);
    }
    return cur === root;
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
  function updateVerdict(claimId, v) {
    const badge = document.querySelector(`#lc-${claimId} .vb-${v.verifier}`);
    if (!badge) return;
    const mark = v.stance === "support" ? "✓" : v.stance === "refute" ? "✗" : "–";
    badge.textContent = `${v.verifier} ${mark}${v.span_valid ? "" : "∅"}`;
    badge.classList.add(`v-${v.stance}`);
    if (!v.span_valid && v.quote) badge.classList.add("v-void");
    if (v.stance === "refute")
      document.getElementById(`lc-${claimId}`)?.classList.add("has-refute");
  }
  function updateScore(claimId, confidence, status) {
    const conf = document.querySelector(`#lc-${claimId} .lc-conf`);
    if (!conf) return;
    const label = status === "REFUTED" ? `✗ refuted ${confidence}%`
                : status === "ESTABLISHED" ? `✓✓ ${confidence}%`
                : `${confidence}% ${String(status).toLowerCase()}`;
    conf.innerHTML = `<span class="conf-pill ${stCls(status)}">${label}</span>`;
  }

  // ---------- report rendering ----------
  function renderReport(report) {
    currentReport = report;
    const sources = new Map(report.sources.map((s) => [s.id, s]));

    els.reportTopic.textContent = report.topic;
    const refuted = report.claims.filter((c) => c.status === "REFUTED").length;
    els.reportStats.textContent =
      `${report.claims.length} claims · ${report.sources.length} sources · ` +
      `${report.contradictions.length} contradictions` +
      (refuted ? ` · ${refuted} refuted` : "") +
      ` · Merkle ${report.merkle_root.slice(0, 10)}…`;

    els.gaugeFg.style.strokeDasharray = CIRC;
    els.gaugeFg.style.strokeDashoffset = CIRC * (1 - report.trust_score / 100);
    els.gaugeFg.classList.remove("g-low", "g-mid", "g-high");
    els.gaugeFg.classList.add(report.trust_score >= 75 ? "g-high" : report.trust_score >= 50 ? "g-mid" : "g-low");
    animateNumber(els.trustValue, report.trust_score);

    els.summaryCard.innerHTML =
      `<h4 class="section-h">The court's summary</h4><p>${citeLinks(report.summary, sources)}</p>`;

    // contradictions
    if (report.contradictions.length) {
      const byId = new Map(report.claims.map((c) => [c.id, c]));
      els.contradictionsBlock.innerHTML =
        `<h4 class="section-h contra-h">⚠️ Contradictions &amp; corrections</h4>` +
        report.contradictions.map((cd) => {
          const c = byId.get(cd.claim_id);
          return `<div class="contra-card">
            <div class="contra-kind">${esc(cd.kind.replace(/_/g, " "))}</div>
            <div class="contra-claim">${esc(c ? c.text : `Claim ${cd.claim_id}`)}</div>
            <p>${citeLinks(cd.description, sources)}</p></div>`;
        }).join("");
    } else {
      els.contradictionsBlock.innerHTML =
        `<div class="no-contra">✅ No contradictions detected — the panel reached consensus.</div>`;
    }

    // claims
    els.claimCount.textContent = `(${report.claims.length})`;
    els.claimsList.innerHTML = report.claims.map((c) => renderClaimCard(c, sources)).join("");
    bindEvidenceChips();

    // sources
    els.sourceCount.textContent = `(${report.sources.length})`;
    els.sourcesList.innerHTML = report.sources.map((s) => {
      let host = s.url; try { host = new URL(s.url).hostname; } catch {}
      return `<a class="source-card" href="${esc(s.url)}" target="_blank" rel="noopener">
        <span class="src-id">[${s.id}]</span>
        <span class="src-title">${esc(s.title)}</span>
        <span class="src-meta"><span class="tier tier-${s.authority_tier}">T${s.authority_tier}</span> ${esc(host)}</span>
      </a>`;
    }).join("");

    els.reportSection.classList.remove("hidden");
    verifyAttestation(currentRunId);
  }

  function renderClaimCard(c, sources) {
    const verdicts = (c.verdicts || []).map((v) =>
      `<span class="vb v-${v.stance}${v.span_valid ? "" : " v-void"}"
             title="${esc(v.reasoning)}&#10;${v.span_valid ? "quote verified in corpus" : "quote NOT found in corpus — verdict voided"}">
        ${v.verifier} ${v.stance === "support" ? "✓" : v.stance === "refute" ? "✗" : "–"}${v.span_valid ? "" : "∅"}</span>`
    ).join("");
    const hallu = (c.hallucinations || []).map((h) =>
      `<div class="hallu-flag hallu-${h.severity}">🕳 ${esc(h.type)} — ${esc(h.evidence)}
        ${h.correction ? `<br><b>Correction:</b> ${esc(h.correction)}` : ""}</div>`).join("");
    const evidence = (c.chunk_ids || []).map((cid) =>
      `<button class="ev-chip" data-claim="${c.id}" data-chunk="${esc(cid)}">🔎 ${esc(cid)}</button>`).join("");
    const cites = (c.source_ids || []).map((n) => {
      const s = sources.get(n);
      return s ? `<a class="cite" href="${esc(s.url)}" target="_blank" rel="noopener">[${n}]</a>` : "";
    }).join("");
    return `<div class="claim-card ${stCls(c.status)}">
      <div class="claim-head">
        <span class="claim-status ${stCls(c.status)}">${esc(c.status)}</span>
        <span class="claim-type">${esc(c.claim_type)}${c.hypothesis_id ? " · " + esc(c.hypothesis_id) : ""}</span>
        <div class="conf-bar"><div class="conf-fill ${stCls(c.status)}" style="width:${c.confidence}%"></div>
          <span class="conf-num">${c.confidence}%</span></div>
      </div>
      <p class="claim-text">${esc(c.text)} ${cites}</p>
      ${hallu}
      <div class="claim-foot">
        <div class="claim-verdicts">${verdicts}</div>
        <div class="claim-evidence">${evidence}</div>
      </div>
      ${c.verification_note ? `<div class="claim-note">${esc(c.verification_note)}</div>` : ""}
    </div>`;
  }

  function bindEvidenceChips() {
    document.querySelectorAll(".ev-chip").forEach((btn) =>
      btn.addEventListener("click", () =>
        openInspector(Number(btn.dataset.claim), btn.dataset.chunk)));
  }

  // ---------- Evidence Inspector (with client-side Merkle proof) ----------
  async function openInspector(claimId, focusChunk) {
    const r = currentReport;
    if (!r) return;
    const claim = r.claims.find((c) => c.id === claimId);
    const chunkMap = new Map();
    const srcByChunk = new Map();
    for (const s of r.sources)
      for (const ch of s.chunks || []) { chunkMap.set(ch.chunk_id, ch); srcByChunk.set(ch.chunk_id, s); }

    const order = focusChunk
      ? [focusChunk, ...claim.chunk_ids.filter((x) => x !== focusChunk)]
      : claim.chunk_ids;

    let html = `<div class="insp-claim">${esc(claim.text)}</div>
      <div class="insp-status ${stCls(claim.status)}">${esc(claim.status)} · ${claim.confidence}%</div>
      <h5>Anchored evidence — verified in your browser, no server trust</h5>`;

    for (const cid of order) {
      const ch = chunkMap.get(cid);
      const s = srcByChunk.get(cid);
      if (!ch) continue;
      const proof = claim.merkle_proofs?.[cid] || [];
      const quote = (claim.verdicts.find((v) => v.chunk_id === cid)?.quote) || "";
      const highlighted = highlightQuote(ch.text, quote);
      html += `<div class="insp-chunk" id="insp-${esc(cid)}">
        <div class="insp-chunk-head">
          <b>${esc(cid)}</b>
          <span class="tier tier-${s.authority_tier}">T${s.authority_tier} · ${esc(s.authority_label || TIER_LABEL[s.authority_tier] || "")}</span>
          <a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.publisher)}</a>
          <span class="insp-proof" data-cid="${esc(cid)}">⏳ verifying Merkle proof…</span>
        </div>
        <div class="insp-text">${highlighted}</div>
        <div class="insp-hash">SHA-256: <code>${esc(ch.hash.slice(0, 24))}…</code></div>
      </div>`;
    }

    // verdicts
    html += `<h5>Verifier verdicts (HMAC-signed)</h5><div class="insp-verdicts">` +
      claim.verdicts.map((v) =>
        `<div class="insp-v v-${v.stance}">
          <b>${v.verifier} — ${v.stance}</b>${v.span_valid ? "" : " <span class='v-void-tag'>quote voided</span>"}
          <p>${esc(v.reasoning)}</p>
          ${v.quote ? `<blockquote>“${esc(v.quote.slice(0, 280))}”</blockquote>` : ""}
          <code class="insp-sig">sig ${esc(v.signature)}</code>
        </div>`).join("") + `</div>`;

    els.inspectorBody.innerHTML = html;
    els.modal.classList.remove("hidden");

    // client-side Merkle verification per chunk
    for (const cid of order) {
      const ch = chunkMap.get(cid);
      const proof = claim.merkle_proofs?.[cid] || [];
      const el = document.querySelector(`#insp-${CSS.escape(cid)} .insp-proof`);
      if (!ch || !el) continue;
      try {
        const leaf = await sha256Hex(ch.text);
        const hashOk = leaf === ch.hash;
        const proofOk = await verifyMerkle(ch.hash, proof, r.merkle_root);
        el.textContent = hashOk && proofOk
          ? "✓ Merkle-verified in browser" : "✗ verification failed";
        el.classList.add(hashOk && proofOk ? "ok" : "bad");
      } catch {
        el.textContent = "✗ verification error"; el.classList.add("bad");
      }
    }
  }

  function highlightQuote(chunkText, quote) {
    const text = esc(chunkText);
    if (!quote) return text.slice(0, 900);
    const q = esc(quote);
    const idx = text.toLowerCase().indexOf(q.toLowerCase());
    if (idx === -1) return text.slice(0, 900);
    return text.slice(0, idx) + "<mark>" + text.slice(idx, idx + q.length) + "</mark>"
         + text.slice(idx + q.length, idx + q.length + 600);
  }

  els.modalClose.addEventListener("click", () => els.modal.classList.add("hidden"));
  els.modal.addEventListener("click", (e) => {
    if (e.target === els.modal) els.modal.classList.add("hidden");
  });

  // ---------- server-side attestation badge ----------
  async function verifyAttestation(runId) {
    els.verifyBadge.className = "verify-badge pending";
    els.verifyText.textContent = "Checking cryptographic anchors…";
    try {
      const r = await fetch(`/api/reports/${runId}/verify`);
      const d = await r.json();
      if (d.verified) {
        els.verifyBadge.className = "verify-badge ok";
        els.verifyText.textContent =
          `✓ Cryptographically verified — Merkle root matched, ${d.signatures_valid}/${d.signatures_checked} verdict signatures valid`;
      } else {
        els.verifyBadge.className = "verify-badge bad";
        els.verifyText.textContent = "✗ Attestation failed: " + (d.issues || []).join(", ");
      }
    } catch {
      els.verifyBadge.className = "verify-badge bad";
      els.verifyText.textContent = "✗ Could not reach verification endpoint";
    }
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
    currentRunId = runId;
    currentReport = null;
    els.liveFeed.innerHTML = "";
    els.liveClaims.innerHTML = "";
    els.hypothesisCards.innerHTML = "";
    els.reportSection.classList.add("hidden");
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
        feed("⚖️ <b>the court convenes</b> — evidentialist, skeptic, contextualist in parallel");
      }
      if (d.stage === "verify" && d.status === "done")
        ["verifier-a", "verifier-b", "verifier-c"].forEach((a) => setAgent(a, "done"));
      feed(`▶ stage <b>${d.stage}</b> ${d.status}`);
    });

    on("hypotheses", (d) => {
      els.hypothesisCards.innerHTML = d.hypotheses.map((h) =>
        `<div class="hyp-card">
          <div class="hyp-id">${esc(h.id)}</div>
          <div class="hyp-text">${esc(h.statement)}</div>
          <div class="hyp-bar"><div class="hyp-fill" style="width:${Math.round(h.plausibility * 100)}%"></div>
            <span>prior plausibility ${Math.round(h.plausibility * 100)}%</span></div>
          ${h.counter_queries.length ? `<div class="hyp-counter">⚔ self-challenge: ${h.counter_queries.map(esc).join(" · ")}</div>` : ""}
          ${h.weaknesses.length ? `<div class="hyp-weak">⚠ self-identified weakness: ${h.weaknesses.map(esc).join(" · ")}</div>` : ""}
        </div>`).join("");
      feed(`🧠 Murli formed <b>${d.hypotheses.length} competing hypotheses</b> + ${d.queries.length} search angles`);
    });

    on("log", (d) => feed(`· ${esc(d.message)}`, "feed-log"));

    on("sources", (d) => {
      const tiers = d.sources.map((s) => s.authority_tier);
      const best = Math.min(...tiers);
      feed(`🔍 <b>${d.sources.length} full-text sources</b> extracted (best authority: T${best})`);
    });

    on("claims", (d) => {
      d.claims.forEach((c) => renderLiveClaim(c));
      feed(`🧩 decomposed into <b>${d.claims.length} atomic claims</b>, anchored to evidence chunks`);
    });

    on("verdict", (d) => {
      updateVerdict(d.claim_id, d);
      if (d.quote && !d.span_valid)
        feed(`∅ verifier ${d.verifier}'s quote on C${d.claim_id} <b>not found in corpus — verdict voided</b>`, "feed-refute");
    });

    on("hallucination", (d) =>
      feed(`🕳 hallucination flag C${d.claim_id} (<b>${d.type}</b>, ${d.severity})`, "feed-refute"));

    on("score", (d) => {
      updateScore(d.claim_id, d.confidence, d.status);
      if (d.status === "REFUTED")
        feed(`✗ claim ${d.claim_id} <b>REFUTED</b> (${d.confidence}%)`, "feed-refute");
    });

    on("contradiction", (d) =>
      feed(`⚠️ <b>contradiction</b> C${d.claim_id}: ${esc(d.description.slice(0, 110))}…`, "feed-refute"));

    on("report", (d) => renderReport(d));

    on("done", (d) => {
      feed(`✅ verdict delivered in <b>${d.elapsed_s}s</b> — Merkle root <code>${d.merkle_root}</code>`);
      els.runBtn.disabled = false;
      els.runBtn.textContent = "Put on trial →";
      loadHistory();
    });

    on("error", (d) => {
      els.errorBanner.textContent = "⚠ " + d.message;
      els.errorBanner.classList.remove("hidden");
      els.runBtn.disabled = false;
      els.runBtn.textContent = "Put on trial →";
    });

    on("end", () => es.close());
    es.onerror = () => {};
  }

  // ---------- events ----------
  els.form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const topic = els.input.value.trim();
    if (!topic) return;
    els.runBtn.disabled = true;
    els.runBtn.textContent = "Trial in session…";
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
      els.runBtn.textContent = "Put on trial →";
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
            currentRunId = d2.run_id;
            els.pipelineSection.classList.add("hidden");
            els.hero.classList.remove("dimmed");
            els.input.value = d2.topic;
            renderReport(d2.report);
            window.scrollTo({ top: 0, behavior: "smooth" });
          }
        }));
    } catch {}
  }

  loadHistory();
})();
