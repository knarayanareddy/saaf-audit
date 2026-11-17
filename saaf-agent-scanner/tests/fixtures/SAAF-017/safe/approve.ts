import { execFileSync, exec } from "child_process";

export function approve(ghUser: string) {
  if (!/^[A-Za-z0-9-]{1,39}$/.test(ghUser)) throw new Error("bad handle");
  return execFileSync("gh", ["api", `/users/${ghUser}`, "--jq", ".id"], { encoding: "utf-8" });
}

export function status() {
  exec("git status --short", () => {});
}

export async function findUser(db: any, email: string) {
  return db.query("SELECT id FROM users WHERE email = $1", [email]);
}

export function regexOnly(s: string) {
  return /a(b)/.exec(s);
}
