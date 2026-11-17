import { execFile } from "node:child_process";
import { promisify } from "node:util";

const run = promisify(execFile);
const API = "https://api.github.com";

export interface RepoInfo {
  fullName: string; // owner/name
  cloneUrl: string;
  defaultBranch: string;
  archived: boolean;
  fork: boolean;
  private: boolean;
}

async function gh<T>(url: string, token?: string): Promise<{ data: T; next?: string }> {
  const res = await fetch(url, {
    headers: {
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "ai-digital-resilience-hero",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`GitHub API ${res.status} for ${url}: ${body.slice(0, 300)}`);
  }
  const link = res.headers.get("link") ?? "";
  const next = /<([^>]+)>;\s*rel="next"/.exec(link)?.[1];
  return { data: (await res.json()) as T, next };
}

interface ApiRepo {
  full_name: string;
  clone_url: string;
  default_branch: string;
  archived: boolean;
  fork: boolean;
  private: boolean;
}

/**
 * List all repositories of a GitHub organization (or, with `isUser`, a user account).
 * Private repos are included when the token has access.
 */
export async function listRepos(owner: string, opts: { token?: string; isUser?: boolean }): Promise<RepoInfo[]> {
  const kind = opts.isUser ? "users" : "orgs";
  let url: string | undefined = `${API}/${kind}/${encodeURIComponent(owner)}/repos?per_page=100&type=all`;
  const repos: RepoInfo[] = [];
  while (url) {
    const page: { data: ApiRepo[]; next?: string } = await gh<ApiRepo[]>(url, opts.token);
    for (const r of page.data) {
      repos.push({
        fullName: r.full_name,
        cloneUrl: r.clone_url,
        defaultBranch: r.default_branch,
        archived: r.archived,
        fork: r.fork,
        private: r.private,
      });
    }
    url = page.next;
  }
  return repos;
}

/**
 * Shallow-clone a repository into `dest`. The token is passed as an HTTP header via
 * git config so it does not end up in the remote URL or in .git/config.
 */
export async function shallowClone(repo: RepoInfo, dest: string, token?: string): Promise<void> {
  // Disable credential helpers so no GUI login prompt pops up during unattended scans.
  const args: string[] = ["-c", "credential.helper="];
  if (token) {
    const basic = Buffer.from(`x-access-token:${token}`).toString("base64");
    args.push("-c", `http.extraHeader=Authorization: Basic ${basic}`);
  }
  args.push("clone", "--depth", "1", "--single-branch", "--no-tags", "--quiet", repo.cloneUrl, dest);
  await run("git", args, {
    maxBuffer: 10 * 1024 * 1024,
    env: { ...process.env, GIT_TERMINAL_PROMPT: "0" },
  });
}
