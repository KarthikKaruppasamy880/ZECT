import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const ENV_CANDIDATES = [
  path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../backend/.env"),
  path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../backend/.env"),
];

/** Load selected backend/.env keys. Never log values. */
export function loadEnvKeys(names: string[]): Record<string, string> {
  const wanted = new Set(names);
  const out: Record<string, string> = {};
  for (const name of names) {
    const fromProc = process.env[name];
    if (fromProc) out[name] = fromProc;
  }
  for (const p of ENV_CANDIDATES) {
    try {
      for (const line of fs.readFileSync(p, "utf8").split(/\r?\n/)) {
        const m = line.match(/^([A-Z0-9_]+)=(.*)$/);
        if (!m || !wanted.has(m[1])) continue;
        if (out[m[1]]) continue;
        out[m[1]] = m[2].replace(/^["']|["']$/g, "");
      }
      break;
    } catch {
      /* next */
    }
  }
  return out;
}

export function loadEnvCreds() {
  const env = loadEnvKeys(["ZECT_USERNAME", "ZECT_PASSWORD"]);
  return {
    username: env.ZECT_USERNAME || "admin@zect.local",
    password: env.ZECT_PASSWORD || "zect-dev-local",
  };
}
