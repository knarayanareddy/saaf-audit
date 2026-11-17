import { SEVERITY_ORDER, type Finding } from "./types.js";

const COLORS: Record<string, string> = {
  critical: "\x1b[41m\x1b[97m",
  high: "\x1b[31m",
  medium: "\x1b[33m",
  low: "\x1b[36m",
  reset: "\x1b[0m",
  dim: "\x1b[2m",
};

export function sortFindings(findings: Finding[]): Finding[] {
  return [...findings].sort(
    (a, b) =>
      SEVERITY_ORDER[b.severity] - SEVERITY_ORDER[a.severity] ||
      a.repo.localeCompare(b.repo) ||
      a.file.localeCompare(b.file) ||
      a.line - b.line,
  );
}

export function formatText(findings: Finding[], color = process.stdout.isTTY): string {
  const c = (k: string) => (color ? COLORS[k] : "");
  if (findings.length === 0) return "No prompt-injection indicators found.";
  const lines: string[] = [];
  for (const f of sortFindings(findings)) {
    lines.push(`${c(f.severity)}${f.severity.toUpperCase()}${c("reset")} ${f.ruleId} ${f.title}`);
    lines.push(`  ${f.repo}:${f.file}:${f.line}:${f.column}`);
    if (f.detail) lines.push(`  ${c("dim")}${f.detail}${c("reset")}`);
    lines.push(`  > ${f.snippet}`);
    if (f.llmReview) {
      const r = f.llmReview;
      lines.push(`  LLM: ${r.verdict} (${Math.round(r.confidence * 100)}%) - ${r.explanation}`);
    }
    lines.push("");
  }
  const counts = Object.keys(SEVERITY_ORDER)
    .reverse()
    .map((s) => `${findings.filter((f) => f.severity === s).length} ${s}`)
    .join(", ");
  lines.push(`${findings.length} finding(s): ${counts}`);
  return lines.join("\n");
}

export function formatJson(findings: Finding[]): string {
  return JSON.stringify({ generatedAt: new Date().toISOString(), findings: sortFindings(findings) }, null, 2);
}
