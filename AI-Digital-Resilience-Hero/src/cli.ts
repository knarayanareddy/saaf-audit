#!/usr/bin/env node
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { parseArgs } from "node:util";
import { listRepos, shallowClone, type RepoInfo } from "./github.js";
import { DEFAULT_MODEL, LlmReviewer } from "./llm.js";
import { formatJson, formatText } from "./report.js";
import { readContext, scanDirectory } from "./scanner.js";
import { SEVERITY_ORDER, type Finding, type Severity } from "./types.js";

const HELP = `AI Digital Resilience Hero - scan repositories for prompt-injection payloads

Usage:
  drh --org <name>  [options]   Scan all repos of a GitHub organization
  drh --user <name> [options]   Scan all repos of a GitHub user
  drh --path <dir>  [options]   Scan a local directory

Options:
  --token <t>          GitHub token (default: $GITHUB_TOKEN). Needed for private repos and higher rate limits.
  --include-forks      Also scan forked repositories
  --include-archived   Also scan archived repositories
  --repo-filter <re>   Only scan repos whose full name matches this regex
  --llm                Let Claude review each file with findings (needs ANTHROPIC_API_KEY or 'ant auth login')
  --model <id>         Claude model for --llm (default: ${DEFAULT_MODEL})
  --hide-benign        With --llm: hide findings Claude judged benign
  --min-severity <s>   Only report findings at or above low|medium|high|critical (default: low)
  --fail-on <s>        Exit with code 1 if a finding at or above this severity exists (default: high)
  --format <f>         text | json (default: text)
  --output <file>      Write the report to a file instead of stdout
  --max-file-kb <n>    Skip files larger than this (default: 1024)
  --concurrency <n>    Repositories cloned/scanned in parallel (default: 4)
  -h, --help           Show this help
`;

function parseSeverity(v: string | undefined, fallback: Severity): Severity {
  if (!v) return fallback;
  if (!(v in SEVERITY_ORDER)) throw new Error(`Invalid severity "${v}". Use low, medium, high or critical.`);
  return v as Severity;
}

async function mapLimit<T, R>(items: T[], limit: number, fn: (item: T) => Promise<R>): Promise<R[]> {
  const results: R[] = new Array(items.length);
  let next = 0;
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (next < items.length) {
      const i = next++;
      results[i] = await fn(items[i]);
    }
  });
  await Promise.all(workers);
  return results;
}

async function main(): Promise<number> {
  const { values: a } = parseArgs({
    options: {
      org: { type: "string" },
      user: { type: "string" },
      path: { type: "string" },
      token: { type: "string" },
      "include-forks": { type: "boolean", default: false },
      "include-archived": { type: "boolean", default: false },
      "repo-filter": { type: "string" },
      llm: { type: "boolean", default: false },
      model: { type: "string", default: DEFAULT_MODEL },
      "hide-benign": { type: "boolean", default: false },
      "min-severity": { type: "string" },
      "fail-on": { type: "string" },
      format: { type: "string", default: "text" },
      output: { type: "string" },
      "max-file-kb": { type: "string", default: "1024" },
      concurrency: { type: "string", default: "4" },
      help: { type: "boolean", short: "h", default: false },
    },
  });

  const sources = [a.org, a.user, a.path].filter(Boolean).length;
  if (a.help || sources !== 1) {
    console.log(HELP);
    return a.help ? 0 : 2;
  }

  const minSeverity = parseSeverity(a["min-severity"], "low");
  const failOn = parseSeverity(a["fail-on"], "high");
  const maxFileBytes = Number(a["max-file-kb"]) * 1024;
  const concurrency = Math.max(1, Number(a.concurrency));
  const token = a.token ?? process.env.GITHUB_TOKEN;
  const log = (msg: string) => process.stderr.write(msg + "\n");

  // Map repo name -> local directory, so the LLM step can read file context afterwards.
  const roots = new Map<string, string>();
  let findings: Finding[] = [];
  let tmpRoot: string | undefined;

  try {
    if (a.path) {
      const root = path.resolve(a.path);
      const name = path.basename(root);
      roots.set(name, root);
      log(`Scanning ${root} ...`);
      findings = await scanDirectory(name, root, { maxFileBytes });
    } else {
      const owner = (a.org ?? a.user)!;
      let repos: RepoInfo[] = await listRepos(owner, { token, isUser: Boolean(a.user) });
      if (!a["include-forks"]) repos = repos.filter((r) => !r.fork);
      if (!a["include-archived"]) repos = repos.filter((r) => !r.archived);
      if (a["repo-filter"]) {
        const re = new RegExp(a["repo-filter"]);
        repos = repos.filter((r) => re.test(r.fullName));
      }
      log(`Found ${repos.length} repositor${repos.length === 1 ? "y" : "ies"} for ${owner}.`);

      tmpRoot = await fs.mkdtemp(path.join(os.tmpdir(), "drh-"));
      const perRepo = await mapLimit(repos, concurrency, async (repo) => {
        const dest = path.join(tmpRoot!, repo.fullName.replace("/", "__"));
        try {
          await shallowClone(repo, dest, token);
          roots.set(repo.fullName, dest);
          const f = await scanDirectory(repo.fullName, dest, { maxFileBytes });
          log(`  ${repo.fullName}: ${f.length} finding(s)`);
          return f;
        } catch (err) {
          log(`  ${repo.fullName}: skipped (${(err as Error).message.split("\n")[0]})`);
          return [];
        }
      });
      findings = perRepo.flat();
    }

    findings = findings.filter((f) => SEVERITY_ORDER[f.severity] >= SEVERITY_ORDER[minSeverity]);

    if (a.llm && findings.length > 0) {
      const reviewer = new LlmReviewer(a.model);
      const byFile = new Map<string, Finding[]>();
      for (const f of findings) {
        const key = `${f.repo}\u0000${f.file}`;
        byFile.set(key, [...(byFile.get(key) ?? []), f]);
      }
      log(`Asking ${a.model} to review ${byFile.size} file(s) ...`);
      await mapLimit([...byFile.values()], concurrency, async (group) => {
        const root = roots.get(group[0].repo)!;
        try {
          const excerpts = await Promise.all(
            [...new Set(group.map((f) => f.line))].map((l) => readContext(root, group[0].file, l)),
          );
          await reviewer.reviewFile(group, excerpts.join("\n...\n"));
        } catch (err) {
          log(`  LLM review failed for ${group[0].repo}/${group[0].file}: ${(err as Error).message}`);
        }
      });
      if (a["hide-benign"]) findings = findings.filter((f) => f.llmReview?.verdict !== "benign");
    }

    const report = a.format === "json" ? formatJson(findings) : formatText(findings, !a.output && process.stdout.isTTY);
    if (a.output) {
      await fs.writeFile(a.output, report, "utf8");
      log(`Report written to ${a.output}`);
    } else {
      console.log(report);
    }

    const failing = findings.some(
      (f) => SEVERITY_ORDER[f.severity] >= SEVERITY_ORDER[failOn] && f.llmReview?.verdict !== "benign",
    );
    return failing ? 1 : 0;
  } finally {
    if (tmpRoot) await fs.rm(tmpRoot, { recursive: true, force: true }).catch(() => {});
  }
}

main().then(
  (code) => process.exit(code),
  (err) => {
    console.error(`Error: ${(err as Error).message}`);
    process.exit(2);
  },
);
