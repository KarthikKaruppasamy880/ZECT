/**
 * Electron restore of authorized Developer Workspace roots.
 * Uses a dedicated userData dir. Not in test:e2e:core (needs Electron binary).
 */
import { test, expect, _electron as electron, type ElectronApplication, type Page } from "@playwright/test";
import fs from "fs";
import os from "os";
import path from "path";
import { execSync } from "child_process";
import { fileURLToPath } from "url";
import { loadEnvCreds } from "./helpers/env";

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const ART = path.join(REPO, "test-results", "workspace-electron-restore");
const ELECTRON_MAIN = path.join(REPO, "electron", "main.js");
const ELECTRON_EXE = path.join(REPO, "electron", "node_modules", "electron", "dist", "electron.exe");
const API = process.env.VITE_API_URL || process.env.ZECT_API_URL || "http://127.0.0.1:8000";

function git(cwd: string, args: string) {
  execSync(`git ${args}`, { cwd, stdio: "pipe" });
}

function makeRepo(label: string) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), `zect-el-${label}-`));
  const repo = path.join(root, label);
  fs.mkdirSync(repo, { recursive: true });
  git(repo, "init -b main");
  git(repo, 'config user.email "zect-e2e@example.com"');
  git(repo, 'config user.name "ZECT E2E"');
  fs.writeFileSync(path.join(repo, `${label}.txt`), `${label}-content\n`);
  git(repo, "add .");
  git(repo, `commit -m "init ${label}"`);
  return repo;
}

test.describe("workspace electron restore", () => {
  test.setTimeout(300_000);

  test("restores three authorized roots after Electron restart", async () => {
    test.skip(!fs.existsSync(ELECTRON_EXE), "Electron binary is not installed in electron/node_modules");
    fs.mkdirSync(ART, { recursive: true });
    const userData = fs.mkdtempSync(path.join(os.tmpdir(), "zect-electron-ws-"));
    const a = makeRepo("zect");
    const b = makeRepo("zoas");
    const c = makeRepo("other");
    const { username, password } = loadEnvCreds();

    const launch = async (): Promise<{ app: ElectronApplication; page: Page }> => {
      const app = await electron.launch({
        executablePath: ELECTRON_EXE,
        args: [`--user-data-dir=${userData}`, ELECTRON_MAIN],
        cwd: path.join(REPO, "electron"),
        env: {
          ...process.env,
          ZECT_DEV: "true",
          ZECT_DEV_URL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173",
          ELECTRON_USER_DATA: userData,
          ZECT_ALLOW_MULTI_INSTANCE: "1",
        },
      });
      const page = await app.firstWindow({ timeout: 60_000 });
      return { app, page };
    };

    const loginIfNeeded = async (page: Page) => {
      await page.waitForLoadState("domcontentloaded");
      if (await page.getByTestId("login-username").isVisible({ timeout: 15_000 }).catch(() => false)) {
        await page.getByTestId("login-username").fill(username);
        await page.getByTestId("login-password").fill(password);
        await page.getByTestId("login-submit").click();
        await expect(page.getByTestId("login-submit")).toBeHidden({ timeout: 30_000 });
      }
    };

    const first = await launch();
    let page = first.page;
    await loginIfNeeded(page);
    const token = await page.evaluate(() => localStorage.getItem("zect_token"));
    const created = await page.request.post(`${API}/api/projects`, {
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      data: { name: `WS Electron ${Date.now()}`, description: "electron restore", team: "E2E", current_stage: "ask" },
    });
    const project = await created.json();
    const projectId = Number(project.id);
    const ids: number[] = [];
    for (const localPath of [a, b, c]) {
      const reg = await page.request.post(`${API}/api/repos/register-local`, {
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        data: { local_path: localPath, project_id: projectId },
      });
      const body = await reg.json();
      ids.push(Number(body.repo_id));
    }
    await page.evaluate(
      ({ projectId: pid, repoId }) => {
        localStorage.setItem("zect_active_project", JSON.stringify({ projectId: pid, repoId, branch: "main" }));
        localStorage.setItem(
          "zect_ws_session",
          JSON.stringify({
            openEditors: [],
            terminals: [],
            activeTerminalId: null,
            workItemId: null,
            projectId: pid,
            activeRepoId: repoId,
          }),
        );
        window.location.assign("/workspace");
      },
      { projectId, repoId: ids[0] },
    );
    await page.waitForURL(/\/workspace/, { timeout: 20_000 });
    await expect(page.getByTestId("workspace-roots-rail")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId(`workspace-root-${ids[2]}`)).toBeVisible({ timeout: 30_000 });
    await page.screenshot({ path: path.join(ART, "01-before-restart.png") });
    await first.app.close();
    await new Promise((r) => setTimeout(r, 2000));

    const second = await launch();
    page = second.page;
    await loginIfNeeded(page);
    await page.evaluate(
      ({ projectId: pid, repoId }) => {
        const existing = localStorage.getItem("zect_active_project");
        if (!existing) {
          localStorage.setItem("zect_active_project", JSON.stringify({ projectId: pid, repoId, branch: "main" }));
        }
        const sessRaw = localStorage.getItem("zect_ws_session");
        if (!sessRaw || !sessRaw.includes(String(pid))) {
          localStorage.setItem(
            "zect_ws_session",
            JSON.stringify({
              openEditors: [],
              terminals: [],
              activeTerminalId: null,
              workItemId: null,
              projectId: pid,
              activeRepoId: repoId,
            }),
          );
        }
      },
      { projectId, repoId: ids[0] },
    );
    await page.evaluate(() => window.location.assign("/workspace"));
    await page.waitForURL(/\/workspace/, { timeout: 20_000 });
    await expect(page.getByTestId("workspace-roots-rail")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId(`workspace-root-${ids[0]}`)).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId(`workspace-root-${ids[1]}`)).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId(`workspace-root-${ids[2]}`)).toBeVisible({ timeout: 30_000 });
    await page.screenshot({ path: path.join(ART, "02-after-restart.png") });
    await second.app.close();
  });
});
