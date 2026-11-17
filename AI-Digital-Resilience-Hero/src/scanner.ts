import { promises as fs } from "node:fs";
import path from "node:path";
import { RULES } from "./rules.js";
import type { Finding, Rule } from "./types.js";

const SKIP_DIRS = new Set([".git", "node_modules", "dist", "build", "vendor", ".venv", "venv", "__pycache__", ".next", "target"]);
const BINARY_EXT = /\.(png|jpe?g|gif|webp|ico|bmp|pdf|zip|gz|tgz|7z|rar|jar|exe|dll|so|dylib|bin|woff2?|ttf|otf|eot|mp[34]|mov|avi|wasm|class|pyc|lock)$/i;

export interface ScanOptions {
  maxFileBytes: number;
  rules?: Rule[];
}

async function* walk(dir: string): AsyncGenerator<string> {
  let entries;
  try {
    entries = await fs.readdir(dir, { withFileTypes: true });
  } catch {
    return;
  }
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) {
      if (!SKIP_DIRS.has(e.name)) yield* walk(full);
    } else if (e.isFile() && !BINARY_EXT.test(e.name)) {
      yield full;
    }
  }
}

function lineCol(content: string, index: number): { line: number; column: number } {
  let line = 1;
  let lastNl = -1;
  for (let i = 0; i < index; i++) {
    if (content.charCodeAt(i) === 10) {
      line++;
      lastNl = i;
    }
  }
  return { line, column: index - lastNl };
}

/** Make a snippet safe to print: reveal invisible characters instead of letting them act on the terminal. */
export function sanitizeSnippet(s: string, max = 160): string {
  const visible = [...s]
    .map((ch) => {
      const cp = ch.codePointAt(0)!;
      if (cp === 0x0a || cp === 0x0d || cp === 0x09) return " ";
      if (cp < 0x20 || cp === 0x7f || (cp >= 0x200b && cp <= 0x200f) || (cp >= 0x202a && cp <= 0x202e) ||
          (cp >= 0x2060 && cp <= 0x2069) || cp === 0xfeff || (cp >= 0xe0000 && cp <= 0xe007f)) {
        return `<U+${cp.toString(16).toUpperCase()}>`;
      }
      return ch;
    })
    .join("")
    .replace(/\s+/g, " ")
    .trim();
  return visible.length > max ? visible.slice(0, max) + "…" : visible;
}

function looksBinary(buf: Buffer): boolean {
  const n = Math.min(buf.length, 8000);
  for (let i = 0; i < n; i++) if (buf[i] === 0) return true;
  return false;
}

export function scanContent(repo: string, relPath: string, content: string, rules: Rule[] = RULES): Finding[] {
  const findings: Finding[] = [];
  for (const rule of rules) {
    if (rule.appliesTo && !rule.appliesTo(relPath)) continue;
    for (const m of rule.match(content)) {
      const { line, column } = lineCol(content, m.index);
      // Show a bit of context around the match.
      const start = Math.max(0, m.index - 40);
      const end = Math.min(content.length, m.index + m.length + 40);
      findings.push({
        ruleId: rule.id,
        title: rule.title,
        severity: rule.severity,
        repo,
        file: relPath,
        line,
        column,
        snippet: sanitizeSnippet(content.slice(start, end)),
        detail: m.detail ? sanitizeSnippet(m.detail, 240) : undefined,
      });
    }
  }
  return findings;
}

export async function scanDirectory(repo: string, root: string, opts: ScanOptions): Promise<Finding[]> {
  const findings: Finding[] = [];
  for await (const file of walk(root)) {
    const stat = await fs.stat(file);
    if (stat.size > opts.maxFileBytes || stat.size === 0) continue;
    const buf = await fs.readFile(file);
    if (looksBinary(buf)) continue;
    const rel = path.relative(root, file).split(path.sep).join("/");
    findings.push(...scanContent(repo, rel, buf.toString("utf8"), opts.rules));
  }
  return findings;
}

/** Return the raw lines around a finding, for LLM review. */
export async function readContext(root: string, relPath: string, line: number, radius = 15): Promise<string> {
  const content = await fs.readFile(path.join(root, relPath), "utf8");
  const lines = content.split("\n");
  const from = Math.max(0, line - 1 - radius);
  const to = Math.min(lines.length, line + radius);
  return lines.slice(from, to).join("\n");
}
