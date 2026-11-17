// Shared header, role/run state, and fetch helpers for every demo page.
// One place to edit the header (logo + "DEMO - Track 2 Fieldwork" label) so
// every page stays in sync — see webapp/README.md for the role-as-dropdown
// caveat (this is NOT authentication, it's a prototype convenience).

const ROLE_LABELS = {
  auditee: "Auditee",
  auditor: "Auditor",
  senior_auditor: "Final auditor",
};

function getRunId() {
  const fromUrl = new URLSearchParams(location.search).get("run");
  if (fromUrl) {
    localStorage.setItem("demo_run_id", fromUrl);
    return fromUrl;
  }
  return localStorage.getItem("demo_run_id") || "";
}

function getRole() {
  return localStorage.getItem("demo_role") || "auditor";
}

function setRole(role) {
  localStorage.setItem("demo_role", role);
}

function runLink(page) {
  const run = getRunId();
  return run ? `${page}.html?run=${encodeURIComponent(run)}` : `${page}.html`;
}

// "Which engagement am I looking at" — organisation, audit scope, and
// period, in that order, so this reads the same way on every page rather
// than each page picking its own subset/order of these three fields.
function engagementContextText(run) {
  const org = run.auditee_contact && run.auditee_contact.organization;
  return [org, run.audit_scope, run.audit_period].filter(Boolean).join(" · ");
}

function renderHeader(active) {
  const el = document.getElementById("demo-header");
  if (!el) return;
  const role = getRole();
  const pages = [
    ["index", "Engagements"],
    ["dashboard", "Dashboard"],
    ["auditee", "Auditee"],
    ["auditor", "Auditor"],
    ["senior", "Final auditor"],
    ["coverage", "Traceability"],
  ];
  const nav = pages
    .map(([slug, label]) => `<a href="${runLink(slug)}"${slug === active ? ' style="text-decoration:underline"' : ""}>${label}</a>`)
    .join("");
  const roleOptions = Object.entries(ROLE_LABELS)
    .map(([value, label]) => `<option value="${value}"${value === role ? " selected" : ""}>${label}</option>`)
    .join("");

  el.innerHTML = `
    <img src="/assets/saaf-logo-white.webp" alt="SAAF">
    <span>DEMO &mdash; Track 2 Fieldwork</span>
    <nav>${nav}</nav>
    <span class="role-picker">
      <button type="button" id="header-voice-btn" class="secondary" style="margin-top:0" hidden>🎤 Voice</button>
      <select id="header-role-select">${roleOptions}</select>
      <span id="header-role-name"></span>
    </span>
  `;

  document.getElementById("header-role-select").addEventListener("change", (e) => {
    setRole(e.target.value);
    // Reload so the whole page (its own role-dependent logic, action
    // buttons, etc.) re-initializes for the newly chosen role.
    location.reload();
  });

  document.getElementById("header-voice-btn").addEventListener("click", () => {
    // Defined in voice.js, loaded alongside common.js on every page.
    startVoiceAssistant();
  });

  renderHeaderRoleName();
}

// Resolves who "I" am for the header display: purely the engagement's own
// record of who's assigned to the current role (this is what the server
// also uses for /approve — see webapp/README.md's "usernames are part of
// the engagement"). No browser-local fallback any more — a name only ever
// comes from the selected engagement, set at creation or edited later on
// engagement.html.
async function renderHeaderRoleName() {
  const nameEl = document.getElementById("header-role-name");
  const voiceBtn = document.getElementById("header-voice-btn");
  if (!nameEl) return;
  const role = getRole();
  const runId = getRunId();

  if (!runId) {
    nameEl.innerHTML = `— <span class="muted">no engagement selected</span>`;
    if (voiceBtn) voiceBtn.hidden = true;
    return;
  }

  try {
    const run = await api(`/api/runs/${runId}`);
    const assigned = role === "auditee" ? run.auditee_contact && run.auditee_contact.name : (run.assigned || {})[role];
    nameEl.innerHTML = assigned
      ? `— ${escapeHtml(assigned)} <span class="muted">(assigned)</span>`
      : `— <a href="${runLink("engagement")}">set ${escapeHtml((ROLE_LABELS[role] || role).toLowerCase())} name</a>`;
    // The voice assistant itself is one server-wide agent (ELEVENLABS_AGENT_ID
    // in the environment); engagement.html's toggle only turns its widget
    // on or off for this specific engagement.
    if (voiceBtn) voiceBtn.hidden = !run.elevenlabs_enabled;
  } catch (e) {
    nameEl.innerHTML = `— <span class="muted">engagement not found</span>`;
    if (voiceBtn) voiceBtn.hidden = true;
  }
}

async function api(path, opts) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch (e) {
      /* ignore */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  const contentType = res.headers.get("content-type") || "";
  return contentType.includes("application/json") ? res.json() : res.text();
}

function apiPost(path, body) {
  return api(path, { method: "POST", body: JSON.stringify(body || {}) });
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s == null ? "" : String(s);
  return div.innerHTML;
}
