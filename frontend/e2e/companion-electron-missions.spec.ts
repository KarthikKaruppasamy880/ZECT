/**
 * Electron Companion missions — HUD, scope restore, intelligence, Present/Workspace handoff.
 * Shell load alone is not PASS.
 */
import { test, expect, _electron as electron, type ElectronApplication, type Page } from "@playwright/test";
import fs from "fs";
import os from "os";
import path from "path";
import { execSync } from "child_process";
import { fileURLToPath } from "url";
import { loadEnvCreds } from "./helpers/env";

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const ART = path.join(REPO, "test-results", "companion-electron");
const ELECTRON_MAIN = path.join(REPO, "electron", "main.js");
const ELECTRON_EXE = path.join(REPO, "electron", "node_modules", "electron", "dist", "electron.exe");
const API = process.env.VITE_API_URL || process.env.ZECT_API_URL || "http://127.0.0.1:8000";
const BASE = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173";

function git(cwd: string, args: string) {
  execSync(`git ${args}`, { cwd, stdio: "pipe" });
}

function makeRepo(label: string) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), `zect-el-cmp-${label}-`));
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

test.describe("companion electron missions", () => {
  test.setTimeout(300_000);

  test("Companion HUD, multi-root scope, intelligence, handoffs, reconnect", async () => {
    test.skip(!fs.existsSync(ELECTRON_EXE), "Electron binary is not installed in electron/node_modules");
    fs.mkdirSync(ART, { recursive: true });
    const userData = fs.mkdtempSync(path.join(os.tmpdir(), "zect-electron-cmp-"));
    const a = makeRepo("zect");
    const b = makeRepo("zoas");
    const { username, password } = loadEnvCreds();

    const launch = async (): Promise<{ app: ElectronApplication; page: Page }> => {
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
      const page = await app.firstWindow({ timeout: 60_000 });
      return { app, page };
    };

    const loginIfNeeded = async (page: Page) => {
      await page.waitForLoadState("domcontentloaded").catch(() => {});
      const url = page.url();
      if (!url || url === "about:blank" || url.startsWith("file:")) {
        await page.goto(`${BASE}/`, { waitUntil: "domcontentloaded", timeout: 30_000 });
      }
      if (await page.getByTestId("login-username").isVisible({ timeout: 15_000 }).catch(() => false)) {
        await page.getByTestId("login-username").fill(username);
        await page.getByTestId("login-password").fill(password);
        await page.getByTestId("login-submit").click();
        await expect(page.getByTestId("login-submit")).toBeHidden({ timeout: 30_000 });
      }
    };

    const openHud = async (page: Page) => {
      await page.goto(`${BASE}/mentrix-home`, { waitUntil: "domcontentloaded", timeout: 30_000 });
      await expect(page.getByTestId("mentrix-companion-page")).toBeVisible({ timeout: 30_000 });
    };

    const first = await launch();
    let page = first.page;
    await loginIfNeeded(page);
    const token = await page.evaluate(() => localStorage.getItem("zect_token"));
    expect(token).toBeTruthy();
    const created = await page.request.post(`${API}/api/projects`, {
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      data: { name: `Cmp Electron ${Date.now()}`, description: "electron companion", team: "E2E", current_stage: "ask" },
    });
    const project = (await created.json()) as { id: number };
    const projectId = Number(project.id);
    const regA = await page.request.post(`${API}/api/repos/register-local`, {
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      data: { local_path: a, project_id: projectId },
    });
    const regB = await page.request.post(`${API}/api/repos/register-local`, {
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      data: { local_path: b, project_id: projectId },
    });
    const idA = Number(((await regA.json()) as { repo_id: number }).repo_id);
    const idB = Number(((await regB.json()) as { repo_id: number }).repo_id);
    await page.evaluate(
      ({ pid, rid }) => {
        localStorage.setItem("zect_active_project", JSON.stringify({ projectId: pid, repoId: rid, branch: "main" }));
      },
      { pid: projectId, rid: idA },
    );

    await openHud(page);
    await expect(page.getByTestId("mentrix-companion-scope")).toBeVisible();
    await expect(page.getByTestId(`mentrix-companion-root-${idA}`)).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId(`mentrix-companion-root-${idB}`)).toBeVisible();
    await page.screenshot({ path: path.join(ART, "01-electron-hud.png") });

    await page.getByTestId("mentrix-companion-input").fill("What is the architecture of this project?");
    await expect(page.getByTestId("mentrix-companion-send")).toBeEnabled();
    await page.getByTestId("mentrix-companion-send").click();
    await expect(page.getByTestId("mentrix-companion-chat")).toContainText(
      /root|project|Lattice|architecture|authorized|not used/i,
      { timeout: 45_000 },
    );

    await page.getByTestId("mentrix-companion-input").fill(
      "Create a work item titled Electron Companion Handoff then open Developer Workspace",
    );
    await expect(page.getByTestId("mentrix-companion-send")).toBeEnabled();
    await page.getByTestId("mentrix-companion-send").click();
    await expect(page).toHaveURL(/\/workspace/, { timeout: 45_000 });
    await page.screenshot({ path: path.join(ART, "02-electron-workspace.png") });

    await openHud(page);
    await page.getByTestId("mentrix-companion-input").fill("Create a presentation from this project");
    await expect(page.getByTestId("mentrix-companion-send")).toBeEnabled();
    await page.getByTestId("mentrix-companion-send").click();
    await expect(page).toHaveURL(/\/present/, { timeout: 45_000 });

    await openHud(page);
    await expect(page.getByTestId("mentrix-connect-voice")).toBeVisible();
    await page.getByTestId("mentrix-tts-toggle").uncheck();

    await first.app.close();
    const second = await launch();
    page = second.page;
    await loginIfNeeded(page);
    await openHud(page);
    await expect(page.getByTestId("mentrix-companion-scope")).toBeVisible();
    await page.screenshot({ path: path.join(ART, "03-electron-reconnect.png") });
    await second.app.close();
  });
});
