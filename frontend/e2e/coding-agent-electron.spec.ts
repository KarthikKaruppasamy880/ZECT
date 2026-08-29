/**
 * Electron Coding Agent pane. Skip if electron.exe is missing — skip ≠ core PASS.
 */
import { test, expect, _electron as electron, type ElectronApplication, type Page } from "@playwright/test";
import fs from "fs";
import os from "os";
import path from "path";
import { execSync } from "child_process";
import { fileURLToPath } from "url";
import { loadEnvCreds } from "./helpers/env";
import { openCodingAgentMission } from "./helpers/releaseJourney";

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const ART = path.join(REPO, "test-results", "coding-agent-electron");
const ELECTRON_MAIN = path.join(REPO, "electron", "main.js");
const ELECTRON_EXE = path.join(REPO, "electron", "node_modules", "electron", "dist", "electron.exe");
const API = process.env.VITE_API_URL || process.env.ZECT_API_URL || "http://127.0.0.1:8000";
const BASE = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173";

function git(cwd: string, args: string) {
  execSync(`git ${args}`, { cwd, stdio: "pipe" });
}

function makeRepo() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "zect-el-ca-"));
  const repo = path.join(root, "backend");
  fs.mkdirSync(repo, { recursive: true });
  git(repo, "init -b main");
  git(repo, 'config user.email "zect-e2e@example.com"');
  git(repo, 'config user.name "ZECT E2E"');
  fs.writeFileSync(path.join(repo, "README.md"), "electron coding agent\n");
  git(repo, "add .");
  git(repo, 'commit -m "init"');
  return repo;
}

test.describe("coding agent electron", () => {
  test.setTimeout(240_000);

  test("Developer Agent pane mission controls in Electron", async () => {
    test.skip(!fs.existsSync(ELECTRON_EXE), "Electron binary is not installed in electron/node_modules");
    fs.mkdirSync(ART, { recursive: true });
    const userData = fs.mkdtempSync(path.join(os.tmpdir(), "zect-electron-ca-"));
    const repo = makeRepo();
    const { username, password } = loadEnvCreds();

    const app = await electron.launch({
      executablePath: ELECTRON_EXE,
      args: [`--user-data-dir=${userData}`, ELECTRON_MAIN],
      cwd: path.join(REPO, "electron"),
      env: {
        ...process.env,
        ZECT_DEV: "true",
        ZECT_DEV_URL: BASE,
        ZECT_API_URL: API,
        ZECT_MANAGE_SERVICES: "0",
        ZECT_DEVTOOLS: "0",
        ELECTRON_USER_DATA: userData,
        ZECT_ALLOW_MULTI_INSTANCE: "1",
      },
    });
    const page: Page = await app.firstWindow({ timeout: 60_000 });
    try {
      await page.waitForLoadState("domcontentloaded").catch(() => {});
      if (await page.getByTestId("login-username").isVisible({ timeout: 15_000 }).catch(() => false)) {
        await page.getByTestId("login-username").fill(username);
        await page.getByTestId("login-password").fill(password);
        await page.getByTestId("login-submit").click();
        await expect(page.getByTestId("login-submit")).toBeHidden({ timeout: 30_000 });
      }
      const token = await page.evaluate(() => localStorage.getItem("zect_token"));
      const created = await page.request.post(`${API}/api/projects`, {
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        data: {
          name: `CA Electron ${Date.now()}`,
          description: "electron coding agent",
          team: "E2E",
          current_stage: "ask",
        },
      });
      const project = await created.json();
      const projectId = Number(project.id);
      const reg = await page.request.post(`${API}/api/repos/register-local`, {
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        data: { local_path: repo, project_id: projectId },
      });
      const row = await reg.json();
      const repoId = Number(row.repo_id);
      await page.evaluate(
        ({ projectId: pid, repoId: rid }) => {
          localStorage.setItem(
            "zect_active_project",
            JSON.stringify({ projectId: pid, repoId: rid, branch: "main" }),
          );
        },
        { projectId, repoId },
      );
      await page.goto(`${BASE}/workspace`, { waitUntil: "domcontentloaded", timeout: 30_000 });
      await expect(page.getByTestId("developer-workspace")).toBeVisible({ timeout: 30_000 });
      await openCodingAgentMission(page);
      await expect(page.getByTestId("mentrix-coding-agent-start-mission")).toBeVisible();
      await expect(page.getByTestId("workspace-maximize-agent")).toBeVisible();
      await page.screenshot({ path: path.join(ART, "01-electron-agent.png") });
    } finally {
      await app.close();
    }
  });
});
