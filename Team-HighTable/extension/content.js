// HighTable – content script
// Injected into https://br1ght8.teammatehosting.com/TeamMate/*

(function () {
  'use strict';

  // Prevent double-injection on soft navigations
  if (document.getElementById('hightable-sidebar')) return;

  // ── Settings ────────────────────────────────────────────────────────────

  let settings = { backendUrl: 'http://localhost:8000', backendApiKey: '' };

  function loadSettings() {
    return new Promise((resolve) => {
      chrome.storage.sync.get(['backendUrl', 'backendApiKey'], (items) => {
        if (items.backendUrl) settings.backendUrl = items.backendUrl;
        if (items.backendApiKey !== undefined) settings.backendApiKey = items.backendApiKey;
        resolve(settings);
      });
    });
  }

  // ── Issue ID detection ───────────────────────────────────────────────────

  function detectIssueId() {
    const url = window.location.href;
    const patterns = [
      /\/issues\/([\w-]+)/i,
      /[?&]issueId=([\w-]+)/i,
      /\/IssuesUnrelease\/([\w-]+)/i,
    ];
    for (const pattern of patterns) {
      const match = url.match(pattern);
      if (match) return match[1];
    }
    return null;
  }

  // ── Build sidebar HTML ───────────────────────────────────────────────────

  function buildSidebarHTML() {
    return `
      <div class="ht-header">
        <span>🏛️ HighTable</span>
        <button class="ht-close-btn" aria-label="Close HighTable sidebar">✕</button>
      </div>
      <div class="ht-body">
        <div id="ht-input-section">
          <div class="ht-section">
            <label for="ht-title-input">Issue Title</label>
            <input
              type="text"
              id="ht-title-input"
              class="ht-input"
              placeholder="Enter or paste issue title…"
              autocomplete="off"
            />
          </div>
          <div class="ht-section">
            <label for="ht-desc-input">Issue Description</label>
            <textarea
              id="ht-desc-input"
              class="ht-textarea"
              rows="4"
              placeholder="Enter or paste issue description…"
            ></textarea>
          </div>
          <div id="ht-detected-info" style="display:none" class="ht-section"></div>
          <button id="ht-analyze-btn" class="ht-btn">🔍 Find Similar Issues</button>
        </div>
        <div id="ht-results-section" style="display:none"></div>
      </div>
    `;
  }

  // ── Inject UI ────────────────────────────────────────────────────────────

  const toggleBtn = document.createElement('button');
  toggleBtn.id = 'hightable-toggle-btn';
  toggleBtn.setAttribute('aria-label', 'Open HighTable');
  toggleBtn.setAttribute('title', 'Open HighTable');
  toggleBtn.textContent = '🏛️';

  const sidebar = document.createElement('div');
  sidebar.id = 'hightable-sidebar';
  sidebar.setAttribute('role', 'complementary');
  sidebar.setAttribute('aria-label', 'HighTable Audit Intelligence');
  sidebar.innerHTML = buildSidebarHTML();

  document.body.appendChild(toggleBtn);
  document.body.appendChild(sidebar);

  // ── DOM element helpers ──────────────────────────────────────────────────

  const $ = (id) => document.getElementById(id);

  function getInputSection()    { return $('ht-input-section'); }
  function getResultsSection()  { return $('ht-results-section'); }
  function getDetectedInfo()    { return $('ht-detected-info'); }
  function getTitleInput()      { return $('ht-title-input'); }
  function getDescInput()       { return $('ht-desc-input'); }
  function getAnalyzeBtn()      { return $('ht-analyze-btn'); }

  // ── Issue detection banner ───────────────────────────────────────────────

  function updateDetectedBanner() {
    const detectedEl = getDetectedInfo();
    if (!detectedEl) return;
    const issueId = detectIssueId();
    if (issueId) {
      detectedEl.style.display = '';
      detectedEl.innerHTML = `
        <div class="ht-detected-banner">
          Issue ID detected: <strong>#${escapeHtml(issueId)}</strong>
          — you can paste the title and description below, or the backend will
          use this ID if you leave the fields blank and submit.
        </div>
      `;
    } else {
      detectedEl.style.display = 'none';
    }
  }

  // ── Toggle & close ───────────────────────────────────────────────────────

  toggleBtn.addEventListener('click', () => {
    sidebar.classList.toggle('open');
    if (sidebar.classList.contains('open')) {
      updateDetectedBanner();
      const titleInput = getTitleInput();
      if (titleInput) titleInput.focus();
    }
  });

  sidebar.querySelector('.ht-close-btn').addEventListener('click', () => {
    sidebar.classList.remove('open');
  });

  // ── Analyze button ───────────────────────────────────────────────────────

  sidebar.addEventListener('click', (e) => {
    if (e.target && e.target.id === 'ht-analyze-btn') {
      handleAnalyze();
    }
  });

  async function handleAnalyze() {
    const titleInput = getTitleInput();
    const descInput  = getDescInput();
    const resultsEl  = getResultsSection();

    if (!titleInput || !resultsEl) return;

    const title       = titleInput.value.trim();
    const description = descInput ? descInput.value.trim() : '';
    const issueId     = detectIssueId();

    if (!title) {
      showError(resultsEl, 'Please enter an issue title before searching.');
      resultsEl.style.display = '';
      return;
    }

    showLoading(resultsEl);
    resultsEl.style.display = '';

    try {
      await loadSettings();

      const body = { title, description };
      if (issueId) body.issue_id = issueId;

      const headers = { 'Content-Type': 'application/json' };
      if (settings.backendApiKey) {
        headers['X-Backend-Key'] = settings.backendApiKey;
      }

      const response = await fetch(`${settings.backendUrl}/api/analyze`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try {
          const errData = await response.json();
          if (errData.detail) detail += `: ${errData.detail}`;
        } catch (_) {}
        throw new Error(detail);
      }

      const data = await response.json();
      renderResults(resultsEl, data);
    } catch (err) {
      showError(resultsEl, `Analysis failed: ${err.message}`);
    }
  }

  // ── Render results ───────────────────────────────────────────────────────

  function renderResults(container, data) {
    const { similar_issues = [], draft_recommendation = '', key_themes = [] } = data;

    let html = '';

    // Key themes
    if (key_themes.length > 0) {
      html += `<p class="ht-results-heading">Key Themes</p>`;
      html += `<div class="ht-themes-row">`;
      for (const theme of key_themes) {
        html += `<span class="ht-tag">${escapeHtml(theme)}</span>`;
      }
      html += `</div>`;
    }

    // Draft recommendation
    if (draft_recommendation) {
      html += `
        <div class="ht-draft-box">
          <div class="ht-draft-box-title">📝 Draft Recommendation</div>
          <div class="ht-draft-text" id="ht-draft-text">${escapeHtml(draft_recommendation)}</div>
          <button class="ht-btn ht-btn-secondary" id="ht-copy-btn">📋 Copy</button>
        </div>
      `;
    }

    // Similar issues
    if (similar_issues.length > 0) {
      html += `<p class="ht-results-heading">Similar Past Issues (${similar_issues.length})</p>`;
      similar_issues.forEach((issue, idx) => {
        const scorePct = Math.round((issue.relevance_score || 0) * 100);
        const recsHtml = buildRecsHTML(issue.recommendations || [], idx);
        html += `
          <div class="ht-issue-card">
            <div class="ht-score-bar">
              <div class="ht-score-fill" style="width:${scorePct}%"></div>
            </div>
            <div class="ht-issue-card-title">
              <a href="${escapeHtml(issue.url || '#')}" target="_blank" rel="noopener noreferrer"
                 class="ht-link">${escapeHtml(issue.title || 'Untitled')}</a>
              <span style="font-size:11px;color:#6b7280;font-weight:400;margin-left:6px;">${scorePct}% relevance</span>
            </div>
            <div class="ht-issue-card-explanation">${escapeHtml(issue.explanation || '')}</div>
            ${recsHtml}
          </div>
        `;
      });
    } else {
      html += `<p style="font-size:13px;color:#6b7280;text-align:center;padding:16px 0;">No similar issues found.</p>`;
    }

    // Back button
    html += `
      <button class="ht-btn ht-btn-secondary" id="ht-back-btn" style="margin-top:8px;">
        ← New Search
      </button>
    `;

    container.innerHTML = html;
    container.style.display = '';

    // Wire up events in the results
    const copyBtn = container.querySelector('#ht-copy-btn');
    if (copyBtn) {
      copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(draft_recommendation).then(() => {
          copyBtn.textContent = '✓ Copied!';
          setTimeout(() => { copyBtn.textContent = '📋 Copy'; }, 2000);
        }).catch(() => {
          copyBtn.textContent = 'Copy failed';
        });
      });
    }

    const backBtn = container.querySelector('#ht-back-btn');
    if (backBtn) {
      backBtn.addEventListener('click', () => {
        container.style.display = 'none';
        container.innerHTML = '';
      });
    }

    // Recommendations toggles
    container.querySelectorAll('.ht-recs-toggle').forEach((btn) => {
      btn.addEventListener('click', () => {
        const listId = btn.getAttribute('data-list-id');
        const list = document.getElementById(listId);
        if (list) {
          list.classList.toggle('expanded');
          btn.textContent = list.classList.contains('expanded')
            ? '▲ Hide recommendations'
            : `▼ Show recommendations (${list.children.length})`;
        }
      });
    });
  }

  function buildRecsHTML(recommendations, cardIdx) {
    if (!recommendations || recommendations.length === 0) return '';
    const listId = `ht-recs-list-${cardIdx}`;
    const items = recommendations
      .map((r) => `<li>${escapeHtml(r)}</li>`)
      .join('');
    return `
      <button class="ht-recs-toggle" data-list-id="${listId}">
        ▼ Show recommendations (${recommendations.length})
      </button>
      <ul id="${listId}" class="ht-recs-list">${items}</ul>
    `;
  }

  // ── Loading & error states ───────────────────────────────────────────────

  function showLoading(container) {
    container.innerHTML = `
      <div class="ht-loading">
        <div class="ht-spinner"></div>
        <span>Searching for similar issues…</span>
      </div>
    `;
    container.style.display = '';
  }

  function showError(container, message) {
    container.innerHTML = `<div class="ht-error">⚠️ ${escapeHtml(message)}</div>`;
    container.style.display = '';
  }

  // ── Utility ──────────────────────────────────────────────────────────────

  function escapeHtml(str) {
    if (typeof str !== 'string') return String(str ?? '');
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // ── SPA navigation: re-detect issue when URL changes ────────────────────

  function handleNavigation() {
    if (sidebar.classList.contains('open')) {
      updateDetectedBanner();
    }
  }

  window.addEventListener('hashchange', handleNavigation);
  window.addEventListener('popstate', handleNavigation);

  // Also intercept history.pushState / replaceState for SPA routers that
  // don't fire popstate on every navigation
  (function patchHistory() {
    const orig = {
      pushState: history.pushState.bind(history),
      replaceState: history.replaceState.bind(history),
    };
    history.pushState = function (...args) {
      orig.pushState(...args);
      handleNavigation();
    };
    history.replaceState = function (...args) {
      orig.replaceState(...args);
      handleNavigation();
    };
  })();

  // ── Init ─────────────────────────────────────────────────────────────────

  loadSettings();
})();
