/**
 * R3.5 multi-repo AGENT headed E2E — disposable git fixtures (never mutates ZECT checkout).
 * ASK → PLAN → approve → deterministic start_agent → two worktrees, aggregate not READY if one blocked.
 */
import { test, expect, type Page } from "@playwright/test";
import fs from "fs";
import os from "os";
import path from "path";
import { execSync } from "child_process";
import { fileURLToPath } from "url";

const ART = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../test-results/multi-repo-r35");
const API = process.env.VITE_API_URL || process.env.ZECT_API_URL || "http://127.0.0.1:8000";

function loadEnvCreds() {
  const candidates = [
    path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../backend/.env"),
    path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../backend/.env"),
  ];
  let username = process.env.ZECT_USERNAME || "admin@zect.local";
  let password = process.env.ZECT_PASSWORD || "zect-dev-local";
  for (const p of candidates) {
    try {
      for (const line of fs.readFileSync(p, "utf8").split(/\r?\n/)) {
        const m = line.match(/^(ZECT_USERNAME|ZECT_PASSWORD)=(.*)$/);
        if (!m) continue;
        const v = m[2].replace(/^["']|["']$/g, "");
        if (m[1] === "ZECT_USERNAME") username = v;
        if (m[1] === "ZECT_PASSWORD") password = v;
      }
      break;
    } catch {
      /* next */
    }
  }
  return { username, password };
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
  expect(await page.evaluate(() => localStorage.getItem("zect_token"))).toBeTruthy();
}

function git(cwd: string, args: string) {
  execSync(`git ${args}`, { cwd, stdio: "pipe" });
}

function makeRepo(label: string, opts?: { failingTest?: boolean }) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), `zect-r35-${label}-`));
  const repo = path.join(root, label);
  fs.mkdirSync(repo, { recursive: true });
  git(repo, "init -b main");
  git(repo, 'config user.email "zect-e2e@example.com"');
  git(repo, 'config user.name "ZECT E2E"');
  fs.writeFileSync(path.join(repo, "README.md"), `# ${label}\n`);
  if (opts?.failingTest) {
    fs.mkdirSync(path.join(repo, "tests"), { recursive: true });
    fs.writeFileSync(path.join(repo, "tests", "test_block.py"), "def test_block():\n    assert False\n");
  }
  git(repo, "add .");
  git(repo, `commit -m "init ${label}"`);
  const sha = execSync("git rev-parse HEAD", { cwd: repo }).toString().trim();
  return { root, repo, sha, label };
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

test.describe("multi-repo R3.5 agent", () => {
  test.setTimeout(240_000);

  test("ASK PLAN approve start_agent isolated worktrees aggregate not READY", async ({ page }) => {
    fs.mkdirSync(ART, { recursive: true });
    await ensureLoggedIn(page);

    const a = makeRepo("repo-a");
    const b = makeRepo("repo-b", { failingTest: true });

    await page.goto("/projects");
    await expect(page.getByTestId("repo-onboarding-panel")).toBeVisible({ timeout: 60_000 });
    await page.getByTestId("repo-onboard-open").click();
    await page.getByTestId("repo-onboard-local-path").fill(a.repo);
    await page.getByTestId("repo-onboard-open-submit").click();
    await expect(page.getByTestId("project-detail-name")).toBeVisible({ timeout: 60_000 });

    const url = page.url();
    const projectId = Number((url.match(/\/projects\/(\d+)/) || [])[1]);
    expect(projectId).toBeTruthy();

    const listed0 = await api(page, "GET", `/api/projects/${projectId}`);
    const firstId =
      listed0.data?.repos?.[0]?.id || listed0.data?.project?.repos?.[0]?.id || listed0.data?.repo_id;
    const regB = await api(page, "POST", "/api/repos/register-local", {
      local_path: b.repo,
      project_id: projectId,
    });
    expect(regB.status).toBeLessThan(300);
    const repoB = regB.data?.repo_id || regB.data?.id;
    const listed = await api(page, "GET", `/api/projects/${projectId}`);
    const repos = listed.data?.repos || listed.data?.project?.repos || [];
    const repoIds = repos.map((r: { id?: number }) => r.id).filter(Boolean);
    if (firstId && !repoIds.includes(firstId)) repoIds.unshift(firstId);
    if (repoB && !repoIds.includes(repoB)) repoIds.push(repoB);
    expect(repoIds.length).toBeGreaterThanOrEqual(2);

    const ask = await api(page, "POST", "/api/mentrix/developer/ask", {
      question: "R3.5 multi-repo agent scope?",
      project_id: projectId,
      repository_ids: repoIds.slice(0, 2),
    });
    expect(ask.status).toBeLessThan(300);

    const plan = await api(page, "POST", "/api/mentrix/developer/plan", {
      goal: "R3.5 isolated worktrees + aggregate gate",
      project_id: projectId,
      repository_ids: repoIds.slice(0, 2),
    });
    expect(plan.status).toBeLessThan(300);
    const workItemId = plan.data?.work_item_id;
    expect(workItemId).toBeTruthy();

    const approve = await api(page, "POST", "/api/mentrix/developer/approve-plan", {
      work_item_id: workItemId,
    });
    expect(approve.status).toBeLessThan(300);

    const agent = await api(page, "POST", "/api/mentrix/developer/agent/start", {
      work_item_id: workItemId,
      deterministic: true,
    });
    expect(agent.status).toBeLessThan(300);
    const worktrees = agent.data?.worktrees || [];
    const ops = agent.data?.operations || [];
    const tests = agent.data?.tests || {};
    const prs = agent.data?.pull_requests || [];
    expect(worktrees.length + ops.length).toBeGreaterThanOrEqual(2);
    expect(agent.data?.ready_to_ship).toBeFalsy();
    const by = tests.by_repository || {};
    const repoResults = Object.values(by) as { ok?: boolean }[];
    if (repoResults.length >= 2) {
      expect(repoResults.some((r) => r.ok === true)).toBeTruthy();
      expect(repoResults.some((r) => r.ok === false)).toBeTruthy();
    }
    for (const pr of prs) {
      const row = pr as { pr_status?: string; pr_url?: string };
      if (!row.pr_url) {
        expect(row.pr_status || "local_branch_only").toBe("local_branch_only");
      }
    }

    await page.goto(`/workspace?work_item_id=${workItemId}`);
    await expect(page.getByTestId("developer-workspace")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("developer-multi-repo-status")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("developer-multi-repo-aggregate")).not.toHaveText(/ready_to_ship/i);
    await page.screenshot({ path: path.join(ART, "01-multi-repo-status.png"), fullPage: false });

    const status = await api(page, "GET", `/api/mentrix/developer/work-items/${workItemId}/multi-repo-status`);
    fs.writeFileSync(
      path.join(ART, "evidence.json"),
      JSON.stringify(
        {
          ok: true,
          project_id: projectId,
          work_item_id: workItemId,
          ask_status: ask.status,
          plan_status: plan.status,
          agent_status: agent.status,
          worktrees: (agent.data?.worktrees || []).map((w: { worktree_path?: string; repository_id?: number }) => ({
            repository_id: w.repository_id,
            worktree_path: w.worktree_path,
          })),
          tests: tests,
          pull_requests: prs,
          ready_to_ship: agent.data?.ready_to_ship,
          aggregate_status: status.data?.aggregate_status,
          github_pr: prs.some((p: { pr_url?: string }) => Boolean(p.pr_url)) ? "CREATED" : "local_branch_only",
          notes: {
            github_pr_live: "Not claimed PASS — fixtures have no GitHub remote/token",
            aggregate: "NOT READY because repo-b has a failing pytest",
          },
        },
        null,
        2,
      ),
    );
  });
});
