/**
 * Headed demo runner for repo UX acceptance (visible Chromium).
 * Usage: node e2e/run-repo-ux-headed-demo.mjs
 */
import { spawn } from "child_process";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");
const outDir = path.join(root, "test-results", "repo-ux-headed");
fs.mkdirSync(outDir, { recursive: true });

const env = {
  ...process.env,
  PLAYWRIGHT_BASE_URL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173",
  VITE_API_URL: process.env.VITE_API_URL || "http://127.0.0.1:8000",
  ZECT_API_URL: process.env.ZECT_API_URL || "http://127.0.0.1:8000",
  HEADED: "1",
};

const args = [
  "exec",
  "playwright",
  "test",
  "e2e/repo-branch-pr-worktree-ux.spec.ts",
  "--headed",
  "--project=chromium",
  "--reporter=list",
  "--trace=on",
];

console.log("Running headed Playwright:", args.join(" "));
const child = spawn("npm", args, { cwd: root, env, stdio: "inherit", shell: true });
child.on("exit", (code) => {
  console.log(`Artifacts under ${outDir}`);
  process.exit(code ?? 1);
});
