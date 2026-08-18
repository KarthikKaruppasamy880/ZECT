/**
 * Work intelligence production (headed): Projects fixture isolation,
 * WorkItems sample + detail, Processes connectors, Lattice per-root.
 * Live Jira/Camunda create is never clicked when connectors are BLOCKED_EXTERNAL.
 */
import { test, expect, type Page } from "@playwright/test";
import fs from "fs";
import os from "os";
import path from "path";
import { execSync } from "child_process";
import { fileURLToPath } from "url";
import { gotoAuthed } from "./helpers/login";

const FRONTEND = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const REPO = path.resolve(FRONTEND, "..");
const ART = path.join(REPO, "test-results", "work-intelligence-production");
const API = process.env.VITE_API_URL || process.env.ZECT_API_URL || "http://127.0.0.1:8000";

function git(cwd: string, args: string) {
  execSync(`git ${args}`, { cwd, stdio: "pipe" });
}

function makeRepo(label: string) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), `zect-wi-${label}-`));
  const repo = path.join(root, label);
  fs.mkdirSync(repo, { recursive: true });
  git(repo, "init -b main");
  git(repo, 'config user.email "zect-e2e@example.com"');
  git(repo, 'config user.name "ZECT E2E"');
  fs.writeFileSync(path.join(repo, "README.md"), `# ${label}\n`);
  fs.writeFileSync(path.join(repo, `${label}.py`), `def ${label}():\n    return "${label}"\n`);
  git(repo, "add .");
  git(repo, `commit -m "init ${label}"`);
  return { root, repo, label };
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

async function apiRetry(page: Page, method: string, pathName: string, body?: unknown, tries = 4) {
  let last = { status: 0, data: {} as Record<string, unknown> };
  for (let i = 0; i < tries; i += 1) {
    last = await api(page, method, pathName, body);
    if (last.status < 300) return last;
    await page.waitForTimeout(1500);
  }
  return last;
}

test.describe("work intelligence production", () => {
  test.setTimeout(180_000);

  test("projects, work items, processes, lattice per-root", async ({ page }) => {
    fs.mkdirSync(ART, { recursive: true });
    const evidence: Record<string, unknown> = {
      jira_status: null,
      camunda_status: null,
      live_ingest_clicked: false,
    };
    await gotoAuthed(page, "/projects", "projects-page");

    const stamp = Date.now();
    const keepName = `WI Auth ${stamp}`;
    const dropName = `Phase6 Pollution ${stamp}`;
    const created = await api(page, "POST", "/api/projects", {
      name: keepName,
      description: "legitimate work-intelligence project",
      team: "E2E",
      provenance: "user",
    });
    expect(created.status).toBe(201);
    const keepProjectId = Number(created.data.id);
    const fixture = await api(page, "POST", "/api/projects", {
      name: dropName,
      description: "test fixture",
      team: "E2E",
      provenance: "test",
      test_run_id: `wi-e2e-${stamp}`,
    });
    expect(fixture.status).toBe(201);

    const a = makeRepo("alpha");
    const b = makeRepo("beta");
    const regA = await apiRetry(page, "POST", "/api/repos/register-local", {
      local_path: a.repo,
      project_id: keepProjectId,
    });
    const regB = await apiRetry(page, "POST", "/api/repos/register-local", {
      local_path: b.repo,
      project_id: keepProjectId,
    });
    expect(regA.status).toBeLessThan(300);
    expect(regB.status).toBeLessThan(300);
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
      { projectId: keepProjectId, repoId: idA },
    );
    await page.waitForURL(/\/workspace/, { timeout: 20_000 });
    if (await page.getByTestId("login-username").isVisible().catch(() => false)) {
      await gotoAuthed(page, "/workspace", "developer-workspace");
    }
    await expect(page.getByTestId("developer-workspace")).toBeVisible({ timeout: 30_000 });
    if (await page.getByTestId("workspace-import-panel").isVisible().catch(() => false)) {
      await page.getByTestId("workspace-import-local").click();
    }
    await expect(page.getByTestId("workspace-git-lattice")).toBeVisible();
    await expect(page.getByTestId("workspace-roots-rail")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId(`workspace-root-${idA}`)).toBeVisible();
    await expect(page.getByTestId(`workspace-root-${idB}`)).toBeVisible();
    const shaA = page.getByTestId(`workspace-root-sha-${idA}`);
    const shaB = page.getByTestId(`workspace-root-sha-${idB}`);
    await expect(shaA).toBeVisible();
    await expect(shaB).toBeVisible();
    const liveA = await shaA.getAttribute("data-live-sha");
    const liveB = await shaB.getAttribute("data-live-sha");
    if (liveA && liveB) {
      expect(liveA).not.toEqual(liveB);
    }
    await page.screenshot({ path: path.join(ART, "04-lattice.png") });

    await gotoAuthed(page, "/projects", "projects-page");
    const projectsPage = page.getByTestId("projects-page");
    await expect(projectsPage.locator("h3").filter({ hasText: keepName })).toBeVisible();
    await expect(projectsPage.locator("h3").filter({ hasText: dropName })).toHaveCount(0);
    await page.screenshot({ path: path.join(ART, "01-projects.png") });

    await gotoAuthed(page, "/work-items", "work-items-page");
    await page.getByTestId("work-items-sample").click();
    const sampleBtn = page.getByRole("button", { name: /Fix Failed Order Validation/ });
    await expect(sampleBtn).toBeVisible({ timeout: 20_000 });
    await sampleBtn.click();
    await expect(page.getByTestId("work-item-detail")).toBeVisible();
    await expect(page.getByTestId("work-item-source")).toHaveText(/camunda/i);
    await expect(page.getByTestId("work-item-external-id")).toHaveText("SAMPLE-ORDER-VALIDATION");
    await expect(page.getByTestId("work-item-status")).toBeVisible();
    await expect(page.getByTestId("work-item-plan-hash")).toBeVisible();
    await expect(page.getByTestId("work-item-aggregate")).toBeVisible();
    await page.getByTestId("work-items-filter-camunda").click();
    await expect(sampleBtn).toBeVisible();
    await page.screenshot({ path: path.join(ART, "02-work-items.png") });

    await gotoAuthed(page, "/fabric", "process-sample-card");
    await expect(page.getByTestId("process-connector-status")).toBeVisible();
    const jiraChip = page.getByTestId("process-connector-jira");
    const camundaChip = page.getByTestId("process-connector-camunda");
    await expect(jiraChip).toBeVisible();
    await expect(camundaChip).toBeVisible();
    evidence.jira_status = await jiraChip.getAttribute("data-status");
    evidence.camunda_status = await camundaChip.getAttribute("data-status");
    await expect(page.getByTestId("process-ingest-form")).toBeVisible();
    evidence.live_ingest_clicked = false;
    await page.screenshot({ path: path.join(ART, "03-processes.png") });
    fs.writeFileSync(path.join(ART, "evidence.json"), JSON.stringify(evidence, null, 2));
  });
});
