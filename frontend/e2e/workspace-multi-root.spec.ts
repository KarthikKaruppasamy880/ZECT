/**
 * Developer Workspace multi-root rail — disposable git folders only.
 * Not in test:e2e:core (needs live API + temp dirs under allowed_roots).
 */
import { test, expect, type Page } from "@playwright/test";
import fs from "fs";
import os from "os";
import path from "path";
import { execSync } from "child_process";
import { loadEnvCreds } from "./helpers/env";

const ART = path.join(process.cwd(), "test-results", "workspace-multi-root");
const API = process.env.VITE_API_URL || process.env.ZECT_API_URL || "http://127.0.0.1:8000";

function git(cwd: string, args: string) {
  execSync(`git ${args}`, { cwd, stdio: "pipe" });
}

function makeRepo(label: string) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), `zect-ws-${label}-`));
  const repo = path.join(root, label);
  fs.mkdirSync(repo, { recursive: true });
  git(repo, "init -b main");
  git(repo, 'config user.email "zect-e2e@example.com"');
  git(repo, 'config user.name "ZECT E2E"');
  fs.writeFileSync(path.join(repo, "README.md"), `# ${label}\n`);
  fs.writeFileSync(path.join(repo, `${label}.txt`), `${label}-content\n`);
  git(repo, "add .");
  git(repo, `commit -m "init ${label}"`);
  return { root, repo, label };
}

async function ensureLoggedIn(page: Page) {
  const { username, password } = loadEnvCreds();
  await page.goto("/");
  const loginVisible = await page.getByTestId("login-username").isVisible().catch(() => false);
  const token = await page.evaluate(() => localStorage.getItem("zect_token"));
  if (loginVisible || !token) {
    await expect(page.getByTestId("login-username")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("login-username").fill(username);
    await page.getByTestId("login-password").fill(password);
    await page.getByTestId("login-submit").click();
    await expect(page.getByTestId("login-submit")).toBeHidden({ timeout: 30_000 });
  }
}

async function headers(page: Page) {
  const token = await page.evaluate(() => localStorage.getItem("zect_token"));
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function api(page: Page, method: string, pathName: string, body?: unknown) {
  const h = await headers(page);
  const res = await page.request.fetch(`${API}${pathName}`, {
    method,
    headers: h,
    data: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  return { status: res.status(), data };
}

test.describe("workspace multi-root", () => {
  test.setTimeout(240_000);

  test("attach three disposable roots, switch, remove without deleting disk", async ({ page }) => {
    fs.mkdirSync(ART, { recursive: true });
    const a = makeRepo("zect");
    const b = makeRepo("zoas");
    const c = makeRepo("other");

    await ensureLoggedIn(page);

    const created = await api(page, "POST", "/api/projects", {
      name: `WS Rail ${Date.now()}`,
      description: "Disposable multi-root rail fixture",
      team: "E2E",
      current_stage: "ask",
    });
    expect(created.status).toBeLessThan(300);
    const projectId = Number(created.data.id);
    expect(projectId).toBeTruthy();

    const regA = await api(page, "POST", "/api/repos/register-local", {
      local_path: a.repo,
      project_id: projectId,
    });
    const regB = await api(page, "POST", "/api/repos/register-local", {
      local_path: b.repo,
      project_id: projectId,
    });
    const regC = await api(page, "POST", "/api/repos/register-local", {
      local_path: c.repo,
      project_id: projectId,
    });
    expect(regA.status).toBeLessThan(300);
    expect(regB.status).toBeLessThan(300);
    expect(regC.status).toBeLessThan(300);
    const idA = Number(regA.data.repo_id);
    const idB = Number(regB.data.repo_id);
    const idC = Number(regC.data.repo_id);
    expect(idA && idB && idC).toBeTruthy();

    await page.evaluate(
      ({ projectId: pid, repoId }) => {
        localStorage.setItem(
          "zect_active_project",
          JSON.stringify({ projectId: pid, repoId, branch: "main" }),
        );
        window.location.assign("/workspace");
      },
      { projectId, repoId: idA },
    );
    await page.waitForURL(/\/workspace/, { timeout: 20_000 });
    if (await page.getByTestId("login-username").isVisible().catch(() => false)) {
      await ensureLoggedIn(page);
      await page.goto("/workspace");
    }
    page.on("dialog", (d) => d.accept());
    await expect(page.getByTestId("developer-workspace")).toBeVisible({ timeout: 30_000 });
    if (await page.getByTestId("workspace-import-panel").isVisible().catch(() => false)) {
      await page.getByTestId("workspace-import-local").click();
      await expect(page.getByTestId("workspace-import-panel")).toHaveCount(0);
    }
    await expect(page.getByTestId("workspace-roots-rail")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId(`workspace-root-${idA}`)).toBeVisible();
    await expect(page.getByTestId(`workspace-root-${idB}`)).toBeVisible();
    await expect(page.getByTestId(`workspace-root-${idC}`)).toBeVisible();
    await expect(page.getByTestId(`workspace-root-${idA}`)).toHaveAttribute("data-active", "true");
    await expect(page.getByTestId("workspace-file-zect.txt")).toBeVisible({ timeout: 20_000 });
    await page.screenshot({ path: path.join(ART, "01-three-roots.png"), fullPage: false });

    await page.getByTestId(`workspace-root-select-${idC}`).evaluate((el) => (el as HTMLElement).click());
    await expect(page.getByTestId(`workspace-root-${idC}`)).toHaveAttribute("data-active", "true", {
      timeout: 15_000,
    });
    await expect(page.getByTestId("workspace-active-root-path")).toContainText(/other/i);
    await expect(page.getByTestId("workspace-file-other.txt")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("workspace-file-zect.txt")).toHaveCount(0);

    await page.getByTestId(`workspace-root-remove-${idB}`).click({ force: true });
    await expect(page.getByTestId(`workspace-root-${idB}`)).toHaveCount(0, { timeout: 10_000 });
    expect(fs.existsSync(b.repo)).toBeTruthy();
    await page.screenshot({ path: path.join(ART, "02-removed-zoas-disk-kept.png"), fullPage: false });
  });
});
