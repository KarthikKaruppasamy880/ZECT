/**
 * Mentrix Coding Agent production surface (headed).
 * Proves PLAN approval, isolated worktree edit/test, cancel/resume, diff, git gate.
 */
import { test, expect, type Page } from "@playwright/test";
import fs from "fs";
import os from "os";
import path from "path";
import { execSync } from "child_process";
import { loadEnvCreds } from "./helpers/env";

const ART = path.join(process.cwd(), "test-results", "coding-agent-production");
const API = process.env.VITE_API_URL || process.env.ZECT_API_URL || "http://127.0.0.1:8000";

function git(cwd: string, args: string) {
  execSync(`git ${args}`, { cwd, stdio: "pipe" });
}

function makeBackendRepo() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "zect-ca-backend-"));
  const repo = path.join(root, "backend");
  fs.mkdirSync(path.join(repo, "tests"), { recursive: true });
  git(repo, "init -b main");
  git(repo, 'config user.email "zect-e2e@example.com"');
  git(repo, 'config user.name "ZECT E2E"');
  fs.writeFileSync(path.join(repo, "calc.py"), "def add(a, b):\n    return a - b\n");
  fs.writeFileSync(
    path.join(repo, "tests", "test_calc.py"),
    "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
  );
  git(repo, "add .");
  git(repo, 'commit -m "init backend defect"');
  return { root, repo };
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
    await expect(page.getByTestId("login-submit")).toHaveCount(0, { timeout: 30_000 });
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

test.describe("coding agent production", () => {
  test.setTimeout(240_000);

  test("headed mission A: PLAN, tests, cancel/resume, git gate", async ({ page }) => {
    fs.mkdirSync(ART, { recursive: true });
    const fixture = makeBackendRepo();
    await ensureLoggedIn(page);

    const created = await api(page, "POST", "/api/projects", {
      name: `CA Prod ${Date.now()}`,
      description: "Coding Agent production fixture",
      team: "E2E",
      current_stage: "ask",
    });
    expect(created.status).toBeLessThan(300);
    const projectId = Number(created.data.id);
    const reg = await api(page, "POST", "/api/repos/register-local", {
      local_path: fixture.repo,
      project_id: projectId,
    });
    expect(reg.status).toBeLessThan(300);
    const repoId = Number(reg.data.repo_id);
    expect(repoId).toBeTruthy();

    await page.evaluate(
      ({ projectId: pid, repoId: rid }) => {
        localStorage.setItem(
          "zect_active_project",
          JSON.stringify({ projectId: pid, repoId: rid, branch: "main" }),
        );
        window.location.assign("/workspace");
      },
      { projectId, repoId },
    );
    await page.waitForURL(/\/workspace/, { timeout: 20_000 });
    if (await page.getByTestId("login-username").isVisible().catch(() => false)) {
      await ensureLoggedIn(page);
      await page.goto("/workspace");
    }
    await expect(page.getByTestId("developer-workspace")).toBeVisible({ timeout: 30_000 });
    if (await page.getByTestId("workspace-import-panel").isVisible().catch(() => false)) {
      await page.getByTestId("workspace-import-local").click();
      await expect(page.getByTestId("workspace-import-panel")).toHaveCount(0);
    }
    await expect(page.getByTestId("workspace-agent-pane")).toBeVisible({ timeout: 20_000 });
    await page.getByTestId("workspace-maximize-agent").click();
    await expect(page.getByTestId("mentrix-coding-agent-panel")).toBeVisible();
    await expect(page.getByTestId("mentrix-coding-agent-mission-tab")).toBeVisible();
    await expect(page.getByTestId("mentrix-coding-agent-phase")).toContainText("idle");

    await page.getByTestId("mentrix-coding-agent-mission-goal").fill("Fix add() so 2+3 is 5");
    await page.getByTestId("mentrix-coding-agent-patches-toggle").click();
    await page.getByTestId("mentrix-coding-agent-patches").fill(
      JSON.stringify({
        [String(repoId)]: [{ path: "calc.py", old: "return a - b", new: "return a + b" }],
      }),
    );
    await page.getByTestId("mentrix-coding-agent-start-mission").click();
    await expect(page.getByTestId("mentrix-coding-agent-phase")).toContainText("awaiting_plan_approval", {
      timeout: 30_000,
    });
    await expect(page.getByTestId("mentrix-coding-agent-plan")).toContainText("PLAN");
    await expect(page.getByTestId("mentrix-coding-agent-repos")).toContainText(/backend|http|repo/i);
    await page.screenshot({ path: path.join(ART, "01-plan.png") });

    await page.getByTestId("mentrix-coding-agent-approve-plan").click();
    await expect(page.getByTestId("mentrix-coding-agent-phase")).toContainText("awaiting_git_approval", {
      timeout: 120_000,
    });
    await expect(page.getByTestId("mentrix-coding-agent-tests")).toContainText("pass");
    await expect(page.getByTestId("mentrix-coding-agent-files")).toContainText("calc.py");
    await expect(page.getByTestId("mentrix-coding-agent-blockers")).toContainText("none");
    await page.screenshot({ path: path.join(ART, "02-tests.png") });

    await page.getByTestId("mentrix-coding-agent-cancel-mission").click();
    await expect(page.getByTestId("mentrix-coding-agent-phase")).toContainText("cancelled", { timeout: 20_000 });
    await page.getByTestId("mentrix-coding-agent-resume").click();
    await expect(page.getByTestId("mentrix-coding-agent-phase")).toContainText("awaiting_git_approval", {
      timeout: 120_000,
    });

    await page.getByTestId("mentrix-coding-agent-open-diff").click();
    await expect(page.getByTestId("mentrix-coding-agent-diff")).toBeVisible();
    await expect(page.getByTestId("mentrix-coding-agent-evidence")).toBeVisible();
    await page.getByTestId("mentrix-coding-agent-approve-git").click();
    await expect(page.getByTestId("mentrix-coding-agent-phase")).toContainText("ready_to_merge", {
      timeout: 60_000,
    });
    await expect(page.getByTestId("mentrix-coding-agent-ci")).not.toContainText("auto-merge", { timeout: 5_000 });
    const original = fs.readFileSync(path.join(fixture.repo, "calc.py"), "utf8");
    expect(original).toContain("return a - b");
    await page.screenshot({ path: path.join(ART, "03-ready.png") });
  });

  test("headed mission F: sibling PASS+FAIL blocks git until repair", async ({ page }) => {
    fs.mkdirSync(ART, { recursive: true });
    const alphaRoot = fs.mkdtempSync(path.join(os.tmpdir(), "zect-ca-alpha-"));
    const betaRoot = fs.mkdtempSync(path.join(os.tmpdir(), "zect-ca-beta-"));
    const alpha = path.join(alphaRoot, "alpha");
    const beta = path.join(betaRoot, "beta");
    for (const repo of [alpha, beta]) {
      fs.mkdirSync(path.join(repo, "tests"), { recursive: true });
      git(repo, "init -b main");
      git(repo, 'config user.email "zect-e2e@example.com"');
      git(repo, 'config user.name "ZECT E2E"');
      fs.writeFileSync(path.join(repo, "protocol.py"), "PROTOCOL = 1\n");
      fs.writeFileSync(
        path.join(repo, "tests", "test_p.py"),
        "import protocol\n\ndef test_p():\n    assert protocol.PROTOCOL == 2\n",
      );
      git(repo, "add .");
      git(repo, 'commit -m "init"');
    }
    await ensureLoggedIn(page);
    const created = await api(page, "POST", "/api/projects", {
      name: `CA Sibling ${Date.now()}`,
      description: "sibling block fixture",
      team: "E2E",
      current_stage: "ask",
    });
    const projectId = Number(created.data.id);
    const regA = await api(page, "POST", "/api/repos/register-local", {
      local_path: alpha,
      project_id: projectId,
    });
    const regB = await api(page, "POST", "/api/repos/register-local", {
      local_path: beta,
      project_id: projectId,
    });
    const idA = Number(regA.data.repo_id);
    const idB = Number(regB.data.repo_id);
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
    await expect(page.getByTestId("developer-workspace")).toBeVisible({ timeout: 30_000 });
    if (await page.getByTestId("workspace-import-panel").isVisible().catch(() => false)) {
      await page.getByTestId("workspace-import-local").click();
    }
    await expect(page.getByTestId(`workspace-root-${idA}`)).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId(`workspace-root-${idB}`)).toBeVisible();
    await expect(page.getByTestId("mentrix-coding-agent-panel")).toBeVisible({ timeout: 20_000 });
    await page.getByTestId("mentrix-coding-agent-mission-goal").fill("Bump protocol to 2 in both roots");
    await page.getByTestId("mentrix-coding-agent-patches-toggle").click();
    await page.getByTestId("mentrix-coding-agent-patches").fill(
      JSON.stringify({
        [String(idA)]: [{ path: "protocol.py", old: "PROTOCOL = 1", new: "PROTOCOL = 2" }],
        [String(idB)]: [],
      }),
    );
    await page.getByTestId("mentrix-coding-agent-start-mission").click();
    await expect(page.getByTestId("mentrix-coding-agent-phase")).toContainText("awaiting_plan_approval", {
      timeout: 30_000,
    });
    await page.getByTestId("mentrix-coding-agent-approve-plan").click();
    await expect(page.getByTestId("mentrix-coding-agent-phase")).toContainText("blocked", { timeout: 120_000 });
    await expect(page.getByTestId("mentrix-coding-agent-blockers")).not.toContainText("none");
    await expect(page.getByTestId("mentrix-coding-agent-approve-git")).toBeDisabled();
    await page.screenshot({ path: path.join(ART, "04-sibling-blocked.png") });
  });
});
