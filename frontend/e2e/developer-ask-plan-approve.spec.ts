/**
 * Developer Workspace ASK → PLAN → Approve & Build.
 * Uses a disposable git fixture + register-local (not live OneDrive ZOAS).
 */
import { test, expect, type Page } from "@playwright/test";
import fs from "fs";
import os from "os";
import path from "path";
import { execSync } from "child_process";
import { loadEnvCreds } from "./helpers/env";
import { hideImportPanel } from "./helpers/releaseJourney";

const ART = path.join(process.cwd(), "test-results", "developer-ask-plan-approve");
const API = process.env.VITE_API_URL || process.env.ZECT_API_URL || "http://127.0.0.1:8000";
const MARKER = "LATTICE_INGEST_TOKEN_ZXQ99";

function git(cwd: string, args: string) {
  execSync(`git ${args}`, { cwd, stdio: "pipe" });
}

function makeAskRepo() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "zect-ask-"));
  const repo = path.join(root, "zoas-fixture");
  fs.mkdirSync(repo, { recursive: true });
  git(repo, "init -b main");
  git(repo, 'config user.email "zect-e2e@example.com"');
  git(repo, 'config user.name "ZECT E2E"');
  fs.writeFileSync(
    path.join(repo, "lattice_ingest.py"),
    `"""${MARKER} documents how Lattice ingest maps OpenAPI paths into the graph."""\nINGEST_TOKEN = "${MARKER}"\n`,
  );
  git(repo, "add .");
  git(repo, 'commit -m "init lattice ingest fixture"');
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

async function api(page: Page, method: string, pathName: string, body?: unknown) {
  const token = await page.evaluate(() => localStorage.getItem("zect_token"));
  const res = await page.request.fetch(`${API}${pathName}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    data: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  return { status: res.status(), data };
}

async function openWorkspaceAgent(page: Page, projectId: number, repoId: number) {
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
  await hideImportPanel(page);
  await expect(page.getByTestId("workspace-agent-pane")).toBeVisible({ timeout: 20_000 });
  await page.getByTestId("workspace-maximize-agent").click();
  await expect(page.getByTestId("mentrix-coding-agent-panel")).toBeVisible({ timeout: 20_000 });
}

test.describe("developer ASK PLAN Approve & Build", () => {
  test.setTimeout(180_000);

  test("ASK cites fixture file; Approve & Build does not 500", async ({ page }) => {
    fs.mkdirSync(ART, { recursive: true });
    const fixture = makeAskRepo();
    await ensureLoggedIn(page);

    const created = await api(page, "POST", "/api/projects", {
      name: `ASK Plan ${Date.now()}`,
      description: "Developer ASK/PLAN fixture",
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

    const sessionPosts: string[] = [];
    page.on("request", (req) => {
      if (req.method() === "POST" && /\/api\/coding-agent\/sessions(?:\?|$)/.test(req.url())) {
        sessionPosts.push(req.url());
      }
    });

    await openWorkspaceAgent(page, projectId, repoId);

    await page.getByTestId("mentrix-coding-agent-ask-tab").click();
    await page.getByTestId("mentrix-coding-agent-ask-input").fill(
      `What is ${MARKER} and which file defines INGEST_TOKEN?`,
    );
    await page.getByTestId("mentrix-coding-agent-ask-send").click();
    await expect(page.getByTestId("mentrix-coding-agent-ask-send")).toBeEnabled({ timeout: 90_000 });
    const askErr = page.getByTestId("mentrix-coding-agent-ask-error");
    if (await askErr.isVisible().catch(() => false)) {
      throw new Error(`ASK failed: ${(await askErr.textContent()) || ""}`);
    }
    const answer = page.getByTestId("mentrix-coding-agent-ask-answer");
    await expect(answer).toBeVisible({ timeout: 15_000 });
    const text = (await answer.textContent()) || "";
    expect(text.length).toBeGreaterThan(8);
    expect(/500|TypeError|mission_start_contract/i.test(text)).toBeFalsy();
    expect(text).toMatch(new RegExp(`${MARKER}|lattice_ingest\\.py`));
    expect(sessionPosts).toHaveLength(0);
    await page.screenshot({ path: path.join(ART, "01-ask.png") });

    await page.getByTestId("mentrix-coding-agent-plan-tab").click();
    await page.getByTestId("mentrix-coding-agent-plan-goal").fill(`Document ${MARKER} in a comment only`);
    await page.getByTestId("mentrix-coding-agent-plan-md").fill(
      `# PLAN\n\n1. Open lattice_ingest.py\n2. Leave ${MARKER} unchanged\n3. Add a one-line comment.\n`,
    );
    await page.getByTestId("mentrix-coding-agent-approve-build").click();
    const planError = page.getByTestId("mentrix-coding-agent-plan-error");
    await expect(page.getByTestId("mentrix-coding-agent-mission-tab")).toBeVisible({ timeout: 30_000 });
    if (await planError.isVisible().catch(() => false)) {
      const err = (await planError.textContent()) || "";
      expect(err).not.toMatch(/internal server error|mission_start_contract|TypeError/i);
      expect(err.length).toBeGreaterThan(0);
    } else {
      await page.getByTestId("mentrix-coding-agent-mission-tab").click();
      await expect(page.getByTestId("mentrix-coding-agent-phase")).not.toContainText(/idle/i, { timeout: 30_000 });
    }
    await page.screenshot({ path: path.join(ART, "02-approve-build.png") });
  });

  test("live ZOAS ASK", async ({ page }) => {
    test.skip(!process.env.ZECT_LIVE_ZOAS, "opt-in ZECT_LIVE_ZOAS=1");
    const zoas = process.env.ZECT_LIVE_ZOAS_PATH || "C:\\Users\\karuppk\\OneDrive - Zinnia\\Desktop\\zoas";
    await ensureLoggedIn(page);
    const created = await api(page, "POST", "/api/projects", {
      name: `ZOAS live ${Date.now()}`,
      description: "Live ZOAS ASK",
      team: "E2E",
      current_stage: "ask",
    });
    const projectId = Number(created.data.id);
    const reg = await api(page, "POST", "/api/repos/register-local", {
      local_path: zoas,
      project_id: projectId,
    });
    expect(reg.status).toBeLessThan(300);
    await openWorkspaceAgent(page, projectId, Number(reg.data.repo_id));
    await page.getByTestId("mentrix-coding-agent-ask-tab").click();
    await page.getByTestId("mentrix-coding-agent-ask-input").fill(
      "Where is Feature Guide document_source handled in the ZOAS frontend?",
    );
    await page.getByTestId("mentrix-coding-agent-ask-send").click();
    await expect(page.getByTestId("mentrix-coding-agent-ask-answer")).toBeVisible({ timeout: 90_000 });
  });
});
