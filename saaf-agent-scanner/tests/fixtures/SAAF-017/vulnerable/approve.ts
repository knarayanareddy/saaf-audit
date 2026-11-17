import { execSync, exec } from "child_process";

export function approve(ghUser: string) {
  const id = execSync(`gh api /users/${ghUser} --jq '.id'`, { encoding: "utf-8" });
  return id;
}

export function clone(url: string, dir: string) {
  exec("git clone " + url + " " + dir, () => {});
}

export async function findUser(db: any, email: string) {
  return db.query(`SELECT id FROM users WHERE email = '${email}'`);
}
