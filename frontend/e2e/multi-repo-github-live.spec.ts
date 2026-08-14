/**
 * R3.6 live GitHub PR proof on disposable private repos.
 * local_branch_only is NOT a PASS. Token is never logged or written to evidence.
 */
import { test, expect, type Page } from "@playwright/test";
import fs from "fs";
import os from "os";
import path from "path";
import { fileURLToPath } from "url";
import { loadEnvCreds, loadEnvKeys } from "./helpers/env";

const ART = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../test-results/multi-repo-r36");
const API = process.env.VITE_API_URL || "http://127.0.0.1:8000";

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
    timeout: 180_000,
  });
  const data = await res.json().catch(() => ({}));
  return { status: res.status(), data };
}

async function gh(token: string, method: string, urlPath: string, body?: unknown) {
  const res = await fetch(`https://api.github.com${urlPath}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "zect-r36-e2e",
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  return { status: res.status, data };
}

test.describe("R3.6 live GitHub multi-repo PR", () => {
  test.skip(!process.env.ZECT_LIVE_R36, "opt-in live GitHub PR proof (ZECT_LIVE_R36=1)");
  test.setTimeout(12 * 60_000);

  test("ASK PLAN approve AGENT creates real GitHub PRs on two disposable repos", async ({ page }) => {
    fs.mkdirSync(ART, { recursive: true });
    const { GITHUB_TOKEN } = loadEnvKeys(["GITHUB_TOKEN"]);
    const evidence: Record<string, unknown> = { github_pr: "unproven" };
    if (!GITHUB_TOKEN) {
      evidence.github_pr = "BLOCKED_EXTERNAL";
      evidence.reason = "GITHUB_TOKEN missing";
      fs.writeFileSync(path.join(ART, "evidence.json"), JSON.stringify(evidence, null, 2));
      test.info().annotations.push({ type: "blocked_external", description: "GITHUB_TOKEN missing" });
      return;
    }

    await ensureLoggedIn(page);
    const me = await gh(GITHUB_TOKEN, "GET", "/user");
    if (me.status >= 400 || !me.data?.login) {
      evidence.github_pr = "BLOCKED_EXTERNAL";
      evidence.reason = `github /user ${me.status}`;
      fs.writeFileSync(path.join(ART, "evidence.json"), JSON.stringify(evidence, null, 2));
      return;
    }
    const owner = String(me.data.login);
    evidence.owner = owner;
    const stamp = Date.now().toString(36);
    const names = [`zect-r36-${stamp}-a`, `zect-r36-${stamp}-b`];
    const created: string[] = [];

    try {
      for (const name of names) {
        const cr = await gh(GITHUB_TOKEN, "POST", "/user/repos", {
          name,
          private: true,
          auto_init: true,
          description: "ZECT R3.6 disposable fixture — delete after proof",
        });
        if (cr.status >= 400) {
          evidence.github_pr = "BLOCKED_EXTERNAL";
          evidence.reason = `repo create ${name} HTTP ${cr.status}`;
          fs.writeFileSync(path.join(ART, "evidence.json"), JSON.stringify(evidence, null, 2));
          return;
        }
        created.push(name);
      }

      const blockFile = await gh(GITHUB_TOKEN, "PUT", `/repos/${owner}/${names[1]}/contents/tests/test_block.py`, {
        message: "R3.6 negative: failing mandatory test",
        content: Buffer.from("def test_block():\n    assert False\n").toString("base64"),
      });
      evidence.negative_file_status = blockFile.status;

      const destRoot = path.join(os.homedir(), "zect-r36-live", stamp);
      fs.mkdirSync(destRoot, { recursive: true });

      const proj = await api(page, "POST", "/api/projects", {
        name: `r36-live-${stamp}`,
        description: "disposable R3.6 GitHub proof",
        repos: [],
      });
      expect(proj.status).toBeLessThan(300);
      const projectId = proj.data?.id;
      expect(projectId).toBeTruthy();
      evidence.project_id = projectId;

      const repoIds: number[] = [];
      for (let i = 0; i < names.length; i++) {
        const dest = path.join(destRoot, names[i]);
        const clone = await api(page, "POST", "/api/repos/clone-url", {
          project_id: projectId,
          git_url: `https://github.com/${owner}/${names[i]}.git`,
          destination: destRoot,
        });
        expect(clone.status, `clone ${names[i]}`).toBeLessThan(300);
        const id = clone.data?.repo_id || clone.data?.id;
        expect(id).toBeTruthy();
        repoIds.push(Number(id));
        void dest;
      }
      evidence.repository_ids = repoIds;
      expect(repoIds.length).toBe(2);

      const ask = await api(page, "POST", "/api/mentrix/developer/ask", {
        question: "R3.6 live GitHub multi-repo scope?",
        project_id: projectId,
        repository_ids: repoIds,
      });
      expect(ask.status).toBeLessThan(300);

      const plan = await api(page, "POST", "/api/mentrix/developer/plan", {
        goal: "R3.6 isolated worktrees + live GitHub PRs",
        project_id: projectId,
        repository_ids: repoIds,
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
      const prs = agent.data?.pull_requests || [];
      const urls = prs
        .map((p: { pr_url?: string; pr_status?: string }) => p.pr_url)
        .filter((u: string | undefined) => Boolean(u));
      const createdPrs = prs.filter(
        (p: { pr_status?: string; pr_url?: string }) =>
          p.pr_status === "created" && String(p.pr_url || "").includes("github.com"),
      );
      evidence.work_item_id = workItemId;
      evidence.pull_requests = prs.map((p: { repository_id?: number; pr_status?: string; pr_url?: string; branch?: string }) => ({
        repository_id: p.repository_id,
        pr_status: p.pr_status,
        pr_url: p.pr_url || null,
        has_github_url: String(p.pr_url || "").includes("github.com"),
        branch: p.branch,
      }));
      evidence.ready_to_ship = agent.data?.ready_to_ship;
      evidence.aggregate_status = agent.data?.aggregate_status;
      evidence.created_pr_count = createdPrs.length;
      evidence.github_pr = createdPrs.length >= 2 ? "CREATED" : "BLOCKED_EXTERNAL";

      await page.goto(`/workspace?work_item_id=${workItemId}`);
      await expect(page.getByTestId("developer-workspace")).toBeVisible({ timeout: 30_000 });
      await page.screenshot({ path: path.join(ART, "01-multi-repo-github.png") });

      if (createdPrs.length < 2) {
        evidence.pr_errors = prs.map((p: { pr_error?: string; pr_status?: string }) => ({
          pr_status: p.pr_status,
          pr_error: String(p.pr_error || "").slice(0, 200),
        }));
      }
      expect(
        createdPrs.length,
        "local_branch_only is not PASS — need >=2 github.com PRs with pr_status created",
      ).toBeGreaterThanOrEqual(2);
      expect(agent.data?.ready_to_ship, "failing mandatory test on repo-b must keep WorkItem not READY").toBe(false);

      const trees = agent.data?.worktrees || [];
      const failTree = trees.find(
        (w: { repository_id?: number }) => Number(w.repository_id) === repoIds[1],
      );
      const wtPath = String(failTree?.worktree_path || path.join(destRoot, names[1]));
      const blockPath = path.join(wtPath, "tests", "test_block.py");
      fs.mkdirSync(path.dirname(blockPath), { recursive: true });
      fs.writeFileSync(blockPath, "def test_block():\n    assert True\n");
      const agent2 = await api(page, "POST", "/api/mentrix/developer/agent/start", {
        work_item_id: workItemId,
        deterministic: true,
      });
      evidence.ready_after_fix = agent2.data?.ready_to_ship;
      evidence.aggregate_after_fix = agent2.data?.aggregate_status;
      expect(agent2.data?.ready_to_ship, "fixing repo-b mandatory test should allow READY_TO_SHIP").toBe(true);
      void urls;
    } finally {
      evidence.cleanup = [];
      for (const name of created) {
        const del = await gh(GITHUB_TOKEN, "DELETE", `/repos/${owner}/${name}`);
        (evidence.cleanup as Array<{ repo: string; status: number }>).push({
          repo: name,
          status: del.status,
        });
      }
      fs.writeFileSync(path.join(ART, "evidence.json"), JSON.stringify(evidence, null, 2));
    }
  });
});
