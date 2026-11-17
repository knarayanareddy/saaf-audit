/* Joiners-movers-leavers agent UI. Plain JavaScript, no build step, no external requests. */
(function () {
  "use strict";

  const I18N = window.I18N, APP = window.APP;
  const S = { lang: APP.lang, step: 1, maxStep: 1, load: null, review: null, filter: "all", selected: null,
              draft: null, signoff: null, busy: false };
  const $ = (sel, el) => (el || document).querySelector(sel);
  const $$ = (sel, el) => Array.from((el || document).querySelectorAll(sel));
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const wait = (ms) => new Promise((r) => setTimeout(r, reduced ? 0 : ms));
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function t(key, params) {
    let s = (I18N[S.lang] && I18N[S.lang][key]) || I18N.en[key] || key;
    if (params) s = s.replace(/\{(\w+)\}/g, (m, k) => (params[k] !== undefined && params[k] !== null ? params[k] : m));
    return s;
  }
  const icon = (name, size) => `<i class="ic" style="--u:url(/static/brand/icons/${name}.svg);width:${size}px;height:${size}px"></i>`;
  const risk = (r) => `<span class="risk ${esc(r)}"><i></i>${esc(t("risk." + r))}</span>`;

  async function api(path, body) {
    const res = await fetch(path, { method: body === undefined ? "GET" : "POST",
      headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || res.statusText);
    return data;
  }

  /* ---------- pixel loader ---------- */
  function pix(el, n) { el.innerHTML = "<i></i>".repeat(n); el.style.setProperty("--n", n); }
  function setPix(el, k) { $$("i", el).forEach((i, idx) => i.classList.toggle("on", idx < k)); }

  /* ---------- language ---------- */
  function applyI18n() {
    document.documentElement.lang = S.lang;
    $$("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
    $$("[data-lang]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === S.lang)));
    $("#s5-name").placeholder = t("s5.reviewer");
    renderScope();
    if (S.review) { renderTests(true); renderExceptions(); }
    if (S.draft) renderDraft();
    renderSignoff();
    renderClaude(S.claude);
  }
  function setLang(lang) {
    S.lang = lang;
    try { localStorage.setItem("jml.lang", lang); } catch (e) { /* storage may be blocked */ }
    const u = new URL(location.href); u.searchParams.set("lang", lang); history.replaceState(null, "", u);
    applyI18n();
  }

  /* ---------- steps ---------- */
  function go(n, noScroll) {
    if (n < 1 || n > S.maxStep) return;
    S.step = n;
    $$(".step").forEach((s) => s.classList.toggle("on", s.id === "step-" + n));
    $$("#stepper button").forEach((b) => {
      const k = Number(b.dataset.goto);
      b.disabled = k > S.maxStep;
      b.classList.toggle("active", k === n);
      b.classList.toggle("done", k < n || (k <= S.maxStep && k !== n));
    });
    if (!noScroll) window.scrollTo({ top: $("#stepper").offsetTop - 12, behavior: reduced ? "auto" : "smooth" });
    if (n === 2 && !S.review) runTests();
    if (n === 4 && !S.inputShown) showInput();
  }
  function unlock(n) { S.maxStep = Math.max(S.maxStep, n); }

  // Moving between steps is always allowed; only starting the same action twice is blocked
  // while it runs (for example going back to step 3 and forward again during the Claude draft).
  function primary() {
    if (S.step === 1) { if (S.load) { unlock(2); go(2); } else if (!S.busy) loadSources(); return; }
    if (S.step === 2) { if (S.review && !$("#s2-next").disabled) { unlock(3); go(3); } return; }
    if (S.step === 3) { unlock(4); go(4); return; }
    if (S.step === 4) { if (S.draft) { unlock(5); go(5); } else if (!S.busy) draft(); return; }
    if (S.step === 5) $("#s5-check").focus({ preventScroll: true });
  }

  /* ---------- Claude status ---------- */
  function renderClaude(st) {
    const chip = $("#claude-chip");
    if (!st) return;
    const ok = st.installed && st.logged_in;
    chip.className = "chip " + (ok ? "ok" : "warn");
    chip.title = st.version || st.message || "";
    chip.lastElementChild.textContent = t(ok ? "claude.ready" : "claude.notready");
  }
  async function checkClaude() {
    try { S.claude = await api("/api/status"); renderClaude(S.claude); } catch (e) { /* offline is fine */ }
  }

  /* ---------- 1 scope ---------- */
  const SOURCE_ICONS = { hr: "org-chart", accounts: "network", tickets: "document-search", policy: "book" };
  function srcIcon(s, i) { return SOURCE_ICONS[s.key] || (i % 2 ? "layers" : "checklist"); }
  function srcLabel(s) { const k = "source." + s.key; return t(k) === k ? s.label : t(k); }

  function renderScope() {
    const meta = S.load || APP.preview;
    $("#s1-lede").textContent = t("s1.lede", { org: meta.organisation, start: meta.audit_period.start,
      end: meta.audit_period.end, extraction: meta.extraction_date });
    const list = $("#sources");
    list.innerHTML = meta.sources.map((s, i) => `
      <div class="row src-row" data-key="${esc(s.key)}">
        <span class="tile-ic">${icon(srcIcon(s, i), 22)}</span>
        <span>${esc(srcLabel(s))}</span>
        <span class="mono">${esc(s.file)}</span>
        <span class="meta">${S.load ? `<span class="tn">${esc(t("s1.loaded", { rows: s.rows }))}</span>
          <span class="mono"> · ${esc(String(s.sha256).slice(0, 8))}</span>` : `<span class="pix mini"></span>`}</span>
      </div>`).join("");
    $$(".mini", list).forEach((el) => pix(el, 8));
    $("#s1-fp").textContent = S.load ? `${t("s1.fingerprint")}: ${S.load.fingerprint}` : "";
  }

  async function loadSources() {
    S.busy = true; $("#s1-load").disabled = true;
    try {
      const pending = api("/api/load", {});
      const rows = $$("#sources .src-row");
      for (const row of rows) {
        const m = $(".mini", row);
        for (let k = 1; k <= 8; k++) { setPix(m, k); await wait(45); }
      }
      S.load = await pending;
      renderScope();
      $("#s1-load").hidden = true; $("#s1-next").hidden = false; $("#s1-next").focus({ preventScroll: true });
      unlock(2); go(1, true);
    } catch (e) { alertError(e); $("#s1-load").disabled = false; }
    S.busy = false;
  }

  /* ---------- 2 controls ---------- */
  const LCS = ["joiner", "mover", "leaver", "baseline"];
  function testRow(tst, revealed) {
    const res = !revealed ? `<span class="pix mini"></span>`
      : tst.exceptions ? `<span class="res hit">${esc(t(tst.exceptions === 1 ? "s2.exception" : "s2.exceptions", { n: tst.exceptions }))}</span>`
      : `<span class="res pass">${esc(t("s2.pass"))}</span>`;
    return `<div class="row test-row" data-test="${esc(tst.id)}">
      <span class="mono">${esc(tst.id)}</span><span>${esc(t("test." + tst.id))}</span>
      <span class="mono tn">${esc(t("s2.tested", { n: tst.tested }))}</span><span class="res">${res}</span></div>`;
  }
  function renderTests(allRevealed) {
    const r = S.review;
    $("#tests").innerHTML = LCS.map((lc) => {
      const tests = r.tests.filter((x) => x.lifecycle === lc);
      return `<div class="group-h"><h3>${esc(t("lc." + lc))}</h3><span class="mono">${tests.length}</span></div>
        <div class="list">${tests.map((x) => testRow(x, allRevealed || S.revealed.has(x.id))).join("")}</div>`;
    }).join("");
    $$("#tests .mini").forEach((el) => pix(el, 8));
  }
  async function runTests() {
    S.busy = true;
    const p = $("#s2-pix"); pix(p, 17); $("#s2-count").textContent = "";
    try {
      S.review = await api("/api/run", {});
      S.revealed = new Set();
      renderTests(false);
      pix(p, S.review.tests.length);
      let k = 0;
      for (const tst of S.review.tests) {
        const row = $(`#tests [data-test="${tst.id}"]`);
        const m = $(".mini", row);
        for (let j = 1; j <= 8; j++) { setPix(m, j); await wait(28); }
        S.revealed.add(tst.id);
        row.outerHTML = testRow(tst, true);
        setPix(p, ++k); $("#s2-count").textContent = `${k}/${S.review.tests.length}`;
      }
      $("#s2-next").disabled = false; $("#s2-next").focus({ preventScroll: true });
      unlock(3); go(2, true);
      renderExceptions();
    } catch (e) { alertError(e); }
    S.busy = false;
  }

  /* ---------- 3 exceptions ---------- */
  const testById = (id) => S.review.tests.find((x) => x.id === id) || {};
  const lcOf = (e) => testById(e.test_id).lifecycle;
  function summary(e) { const k = "summary." + e.test_id; return t(k) === k ? e.summary : t(k, e.params); }

  function renderExceptions() {
    const r = S.review;
    $("#s3-title").textContent = t("s3.title", { n: r.exceptions.length });
    const counts = { all: r.exceptions.length };
    LCS.forEach((lc) => { counts[lc] = r.exceptions.filter((e) => lcOf(e) === lc).length; });
    $("#tiles").innerHTML = LCS.map((lc) => `<button class="tile" type="button" data-filter="${lc}"
        aria-pressed="${S.filter === lc}"><span class="num">${counts[lc]}</span><span class="t">${esc(t("lc." + lc))}</span></button>`).join("");
    const shown = r.exceptions.filter((e) => S.filter === "all" || lcOf(e) === S.filter);
    if (!S.selected || !shown.find((e) => e.id === S.selected)) S.selected = shown.length ? shown[0].id : null;
    $("#exc-list").innerHTML = shown.map((e) => `
      <button class="exc-row" type="button" role="option" data-exc="${e.id}" aria-selected="${e.id === S.selected}">
        <span class="mono">${e.id}</span>${risk(e.risk_rating)}
        <span><span class="who">${esc(e.full_name)}</span> · <span class="what">${esc(t("test." + e.test_id))}</span></span>
      </button>`).join("");
    renderDetail();
  }

  function renderDetail() {
    const e = S.review.exceptions.find((x) => x.id === S.selected);
    const el = $("#exc-detail");
    if (!e) { el.innerHTML = ""; return; }
    const refs = new Set(e.evidence.map((v) => v.ref));
    const tl = (S.review.timelines[e.username] || []).map((ev) => `
      <li class="${refs.has(ev.ref) ? "hit" : ""}"><i></i><span class="mono tn">${esc(ev.date)}</span>
        <span>${esc(t("tl." + ev.kind, { detail: ev.detail }))}</span><span class="cite">${esc(ev.ref)}</span></li>`).join("");
    const lc = e.user_lifecycle;
    const lcLabel = t("lc." + lc + ".one") !== "lc." + lc + ".one" ? t("lc." + lc + ".one") : t("lc." + lc);
    el.innerHTML = `
      <div class="head"><span class="tile-ic">${icon("mind-pixel", 24)}</span>
        <div><h3>${esc(e.full_name)}</h3><span class="mono">${esc(lcLabel)} · ${esc(e.user_ref)} · ${e.id}</span></div></div>
      <p class="sum">${risk(e.risk_rating)} · <strong>${esc(e.test_id)}</strong> ${esc(t("test." + e.test_id))}<br>${esc(summary(e))}</p>
      <span class="lab">${esc(t("s3.timeline"))}</span>
      <ul class="tl">${tl}</ul>
      <span class="lab">${esc(t("s3.evidence"))}</span>
      ${e.evidence.map((v, i) => `<div class="src-cite"><span class="cite">${i + 1}</span><span>${esc(v.source)}</span>
        <span class="ref">${esc(v.ref)}</span></div>`).join("")}`;
  }

  /* ---------- 4 findings ---------- */
  async function showInput() {
    S.inputShown = true;
    try { const p = await api("/api/model-input"); $("#s4-input").textContent = JSON.stringify(p, null, 1); }
    catch (e) { S.inputShown = false; }
  }

  async function draft() {
    S.busy = true;
    $("#s4-draft").disabled = true; $("#s4-result").hidden = true; $("#s4-progress").hidden = false;
    $("#s4-working").textContent = t("s4.working", { n: S.review.exceptions.length });
    const p = $("#s4-pix"); pix(p, 30);
    const started = Date.now(), expected = APP.expected_seconds * 1000;
    const timer = setInterval(() => {
      const ms = Date.now() - started;
      setPix(p, Math.min(29, Math.round(30 * (1 - Math.exp(-ms / expected)))));
      $("#s4-secs").textContent = Math.round(ms / 1000) + " s";
    }, 250);
    try {
      S.draft = await api("/api/draft", { lang: S.lang, mode: APP.mode });
      setPix(p, 30); await wait(300);
      $("#s4-progress").hidden = true;
      renderDraft();
      $("#s4-draft").hidden = true; $("#s4-next").hidden = false; $("#s4-next").focus({ preventScroll: true });
      unlock(5);
      $$("#stepper button").forEach((b) => { b.disabled = Number(b.dataset.goto) > S.maxStep; });
    } catch (e) { alertError(e); $("#s4-progress").hidden = true; $("#s4-draft").disabled = false; }
    clearInterval(timer);
    S.busy = false;
  }

  function renderDraft() {
    const d = S.draft, el = $("#s4-result");
    el.hidden = false;
    const modeTxt = d.mode === "live" ? t("s4.mode.live", { model: d.model || "Claude", seconds: d.duration_s })
      : t("s4.mode." + d.mode);
    const c = d.checks;
    const checks = [
      [t("s4.check.kept", { kept: c.findings_kept, received: c.findings_received }), c.findings_rejected === 0],
      [t("s4.check.assessed", { n: c.exceptions_assessed, total: c.exceptions_total }), c.exceptions_assessed === c.exceptions_total],
      [t("s4.check.covered", { n: c.exceptions_covered, total: c.exceptions_total }), c.exceptions_covered === c.exceptions_total],
    ];
    const findings = d.findings_display.map((f, i) => `
      <details class="f" ${i === 0 ? "open" : ""}>
        <summary><span class="mono">${esc(f.id)}</span>${risk(f.risk_rating)}<h3>${esc(f.title)}</h3><span class="chev" aria-hidden="true">›</span></summary>
        <dl class="f-body">
          ${["control_objective", "observation", "root_cause", "impact", "recommendation"].map((k) =>
            f[k] ? `<dt>${esc(t("s4.f." + k))}</dt><dd>${esc(f[k])}</dd>` : "").join("")}
          <dt>${esc(t("s4.f.sources"))}</dt><dd class="cites">${(f.evidence_references || []).map((r, n) =>
            `<button type="button" data-cite="${esc(r)}"><span class="cite">${n + 1} · ${esc(r)}</span></button>`).join("")}</dd>
        </dl>
      </details>`).join("");
    const assess = d.assessments_display.map((a) => `<tr><td class="mono">${esc(a.exception_id)}</td>
      <td class="concl ${a.conclusion === "Needs follow-up" ? "follow" : ""}">${esc(t("s4.conclusion." + a.conclusion))}</td>
      <td>${esc(a.rationale)}${a.follow_up ? `<br><span class="mono">${esc(a.follow_up)}</span>` : ""}</td></tr>`).join("");
    el.innerHTML = `
      <span class="mode ${esc(d.mode)}"><i></i>${esc(modeTxt)}</span>
      ${d.error ? `<p class="err">${esc(t("s4.fallback", { reason: d.error }))}</p>` : ""}
      <ul class="checks">${checks.map(([txt, ok]) => `<li class="${ok ? "" : "bad"}">${esc(txt)}</li>`).join("")}
        ${c.issues.map((x) => `<li class="bad">${esc(x)}</li>`).join("")}</ul>
      <div class="f-sum"><span class="lab">${esc(t("s4.summary"))}</span><p>${esc(d.summary_display)}</p></div>
      <div class="group-h"><h3>${esc(t("s4.findings"))}</h3><span class="mono">${d.findings.length}</span></div>
      <div class="list">${findings}</div>
      <div class="group-h" style="margin-top:var(--light-s5)"><h3>${esc(t("s4.assessments"))}</h3><span class="mono">${d.assessments.length}</span></div>
      <table class="assess"><thead><tr><th>ID</th><th></th><th></th></tr></thead><tbody>${assess}</tbody></table>
      <div class="actions"><button class="btn ghost" type="button" id="s4-retry">${esc(t("s4.retry"))}</button></div>`;
  }

  /* ---------- 5 sign-off ---------- */
  function renderSignoff() {
    const ok = $("#s5-check").checked && $("#s5-name").value.trim().length > 1;
    $("#s5-sign").disabled = !ok || !S.draft;
    if (S.signoff) {
      $("#s5-done").hidden = false;
      $("#s5-done").innerHTML = `${esc(t("s5.done", { name: S.signoff.reviewer, date: S.signoff.signed_at }))}
        <a href="/report?lang=${S.lang}" target="_blank" rel="noopener">${esc(t("s5.open"))} →</a>`;
    }
  }
  async function signoff() {
    try {
      S.signoff = await api("/api/signoff", { reviewer: $("#s5-name").value.trim(), statement: t("s5.statement") });
      renderSignoff();
      window.open("/report?lang=" + S.lang, "_blank", "noopener");
    } catch (e) { alertError(e); }
  }

  function alertError(e) {
    const p = document.createElement("p");
    p.className = "err"; p.textContent = t("error.generic", { message: e.message });
    $(".step.on .actions").before(p);
  }

  /* ---------- print ---------- */
  // Cmd/Ctrl+P on this page prints the report (A4 layout) instead of the screen UI.
  function printReport() {
    let f = $("#print-frame");
    if (!f) {
      f = document.createElement("iframe");
      f.id = "print-frame";
      f.setAttribute("aria-hidden", "true");
      f.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0;visibility:hidden";
      document.body.appendChild(f);
    }
    f.onload = () => {
      const w = f.contentWindow;
      const go = () => { w.focus(); w.print(); };
      (w.document.fonts && w.document.fonts.ready ? w.document.fonts.ready : Promise.resolve()).then(() => setTimeout(go, 150));
    };
    f.src = "/report?lang=" + S.lang + "&t=" + Date.now();
  }
  document.addEventListener("keydown", (ev) => {
    if ((ev.metaKey || ev.ctrlKey) && ev.key.toLowerCase() === "p" && S.review) { ev.preventDefault(); printReport(); }
  }, true);
  window.JML_printReport = printReport;

  /* ---------- wiring ---------- */
  document.addEventListener("click", (ev) => {
    const b = ev.target.closest("button, a");
    if (!b) return;
    if (b.dataset.lang) return setLang(b.dataset.lang);
    if (b.dataset.goto) return go(Number(b.dataset.goto));
    if (b.hasAttribute("data-back")) return go(S.step - 1);
    if (b.dataset.filter) { S.filter = S.filter === b.dataset.filter ? "all" : b.dataset.filter; return renderExceptions(); }
    if (b.dataset.exc) { S.selected = b.dataset.exc; return renderExceptions(); }
    if (b.dataset.cite) {
      const r = b.dataset.cite, e = S.review.exceptions.find((x) => x.id === r || x.tickets.includes(r));
      if (e) { S.filter = "all"; S.selected = e.id; renderExceptions(); go(3); }
      return;
    }
    if (b.id === "s4-retry") { if (S.busy) return; S.draft = null; $("#s4-draft").hidden = false; $("#s4-next").hidden = true; return draft(); }
    if (b.id === "s5-sign") return signoff();
    if (["s1-load", "s1-next", "s2-next", "s3-next", "s4-draft", "s4-next"].includes(b.id)) return primary();
  });
  $("#s5-check").addEventListener("change", renderSignoff);
  $("#s5-name").addEventListener("input", renderSignoff);
  document.addEventListener("keydown", (ev) => {
    if (ev.target.closest("input, textarea, select") || ev.metaKey || ev.ctrlKey || ev.altKey) return;
    if (["ArrowRight", "PageDown"].includes(ev.key)) { ev.preventDefault(); primary(); }
    if (["ArrowLeft", "PageUp"].includes(ev.key)) { ev.preventDefault(); go(S.step - 1); }
    if (S.step === 3 && ["ArrowDown", "ArrowUp"].includes(ev.key) && S.review) {
      ev.preventDefault();
      const ids = $$("#exc-list [data-exc]").map((x) => x.dataset.exc);
      const i = ids.indexOf(S.selected) + (ev.key === "ArrowDown" ? 1 : -1);
      if (ids[i]) { S.selected = ids[i]; renderExceptions(); }
    }
  });

  try { const saved = localStorage.getItem("jml.lang"); if (!APP.lang_from_url && saved && I18N[saved]) S.lang = saved; } catch (e) { /* ignore */ }
  applyI18n();
  go(1, true);
  checkClaude();
})();
