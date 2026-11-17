// ElevenLabs voice assistant — per-engagement (see engagement.html's
// on/off toggle and agent-id field). Loaded on every page like common.js,
// but does nothing until the header's mic button is visible (only when
// the loaded engagement has elevenlabs_enabled + elevenlabs_agent_id —
// see renderHeaderRoleName in common.js) and clicked. The ElevenLabs
// client SDK itself is only fetched then, not on every page load.
//
// Depends on common.js already being loaded (api(), getRunId(), setRole(),
// runLink()).

let _voiceConversation = null;

function _voicePanel() {
  let panel = document.getElementById("voice-panel");
  if (panel) return panel;
  panel = document.createElement("div");
  panel.id = "voice-panel";
  panel.hidden = true;
  panel.innerHTML = `
    <div id="voice-panel-status">Connecting…</div>
    <button type="button" id="voice-panel-end" class="danger">End</button>
  `;
  document.body.appendChild(panel);
  panel.querySelector("#voice-panel-end").addEventListener("click", stopVoiceAssistant);
  return panel;
}

function _setVoiceStatus(text) {
  const panel = _voicePanel();
  panel.hidden = false;
  panel.querySelector("#voice-panel-status").textContent = text;
}

async function stopVoiceAssistant() {
  const conversation = _voiceConversation;
  _voiceConversation = null;
  if (conversation) {
    try {
      await conversation.endSession();
    } catch (err) {
      /* connection may already be gone — nothing more to do */
    }
  }
  const panel = document.getElementById("voice-panel");
  if (panel) panel.hidden = true;
}

async function startVoiceAssistant() {
  if (_voiceConversation) return; // already connected — the panel's End button stops it
  const runId = getRunId();
  if (!runId) {
    alert("Select an engagement first.");
    return;
  }

  _setVoiceStatus("Connecting…");
  try {
    const { signed_url } = await api(`/api/runs/${runId}/elevenlabs/signed-url`);
    const { Conversation } = await import("https://cdn.jsdelivr.net/npm/@elevenlabs/client/+esm");

    _voiceConversation = await Conversation.startSession({
      signedUrl: signed_url,
      clientTools: {
        get_engagement_status: () => _toolGetEngagementStatus(runId),
        get_item_status: (params) => _toolGetItemStatus(runId, params),
        list_outstanding_items: () => _toolListOutstandingItems(runId),
        switch_role: (params) => _toolSwitchRole(params),
      },
      onConnect: () => _setVoiceStatus("Connected — say something"),
      onDisconnect: () => {
        _voiceConversation = null;
        _setVoiceStatus("Disconnected");
      },
      onError: (err) => _setVoiceStatus("Error: " + (err && err.message ? err.message : err)),
      onModeChange: (m) => {
        const mode = typeof m === "string" ? m : m && m.mode;
        _setVoiceStatus(mode === "speaking" ? "Speaking…" : "Listening…");
      },
    });
  } catch (err) {
    _voiceConversation = null;
    _setVoiceStatus("Could not start: " + err.message);
  }
}

// --- client tools — answered locally from data this page already has
// access to via the same REST endpoints every page uses, never a separate
// "voice API"; the agent has no more access to this engagement than the
// browser tab it's running in. Return plain objects — the SDK
// JSON-stringifies them for the agent automatically. ---

async function _toolGetEngagementStatus(runId) {
  const board = await api(`/api/runs/${runId}/board`);
  const total = board.length;
  const notDelivered = board.filter((r) => r.validation_status === "pending" || r.validation_status === "overdue").length;
  const awaiting = board.filter(
    (r) => r.validation_status !== "pending" && r.validation_status !== "overdue" && r.approval_status === "pending"
  ).length;
  const approved = board.filter((r) => r.approval_status === "approved").length;
  const rejected = board.filter((r) => r.approval_status === "rejected").length;
  return {
    total_items: total,
    not_yet_delivered: notDelivered,
    awaiting_auditor_review: awaiting,
    approved,
    rejected,
  };
}

async function _toolGetItemStatus(runId, params) {
  const pbcId = params && (params.pbc_id || params.pbcId);
  if (!pbcId) return { error: "No pbc_id given." };
  const board = await api(`/api/runs/${runId}/board`);
  const row = board.find((r) => r.pbc_id.toLowerCase() === String(pbcId).toLowerCase());
  if (!row) return { error: `No item ${pbcId} found on this engagement.` };
  const ctx = row.work_program_context || {};
  return {
    pbc_id: row.pbc_id,
    description: row.description,
    deadline: row.deadline,
    status: row.display_status,
    ai_notes: row.validation_notes || null,
    risk: ctx.risk || null,
    control: ctx.control || null,
  };
}

async function _toolListOutstandingItems(runId) {
  const board = await api(`/api/runs/${runId}/board`);
  const outstanding = board
    .filter((r) => r.validation_status === "pending" || r.validation_status === "overdue")
    .map((r) => ({ pbc_id: r.pbc_id, deadline: r.deadline, status: r.validation_status }));
  return { outstanding_items: outstanding };
}

async function _toolSwitchRole(params) {
  const role = params && params.role;
  const targetPage = { auditee: "auditee", auditor: "auditor", senior_auditor: "senior" }[role];
  if (!targetPage) return { error: `Unknown role ${role}` };
  setRole(role);
  // Every role-dependent part of the header/page (name shown, nav
  // underline, approve/reject attribution) is re-read on load, the same
  // way the header's own role dropdown already forces a reload on change
  // — a short delay lets the spoken confirmation finish before the page
  // navigates out from under the conversation.
  const target = runLink(targetPage);
  setTimeout(() => {
    location.href = target;
  }, 300);
  return { ok: true, role };
}
