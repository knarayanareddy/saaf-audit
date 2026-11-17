// Same UI, with escaping / textContent / a restrictive sanitiser.
function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

async function showReview(resp) {
  const data = await resp.json();
  const out = document.getElementById("out");
  out.innerHTML = `<h3>${escapeHtml(data.title)}</h3><div class="verdict">${escapeHtml(data.verdict)}</div><p>${escapeHtml(data.rationale)}</p>`;
}

function renderFinding(finding) {
  const row = document.createElement("tr");
  const a = document.createElement("td");
  a.textContent = finding.description;
  const b = document.createElement("td");
  b.textContent = finding.recommendation;
  row.append(a, b);
  return row;
}

function streamMarkdown(rawMarkdown) {
  const output = document.getElementById("output");
  output.innerHTML = DOMPurify.sanitize(marked.parse(rawMarkdown), {
    FORBID_TAGS: ["img", "style"],
    ALLOWED_URI_REGEXP: /^(?:https?:|mailto:)/i,
  });
}

function addNote(list, note) {
  const li = document.createElement("li");
  li.textContent = note.text;
  list.appendChild(li);
}

function Answer({ reply }) {
  return <div>{reply.content}</div>;
}

const LABELS = { a: "<b>static</b>" };
function staticOnly() {
  document.getElementById("x").innerHTML = "";
  document.getElementById("y").innerHTML = `<b>${LABELS.a}</b> <span>${items.length} items</span>`;
}
