import { expect, type Page } from "@playwright/test";
import { execSync } from "child_process";
import fs from "fs";
import os from "os";
import path from "path";

export const API = process.env.VITE_API_URL || process.env.ZECT_API_URL || "http://127.0.0.1:8000";

export function git(cwd: string, args: string) {
  execSync(`git ${args}`, { cwd, stdio: "pipe" });
}

export function makeGitRepo(label: string, files: Record<string, string>) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), `zect-h-${label}-`));
  const repo = path.join(root, label);
  fs.mkdirSync(path.join(repo, "tests"), { recursive: true });
  git(repo, "init -b main");
  git(repo, 'config user.email "zect-e2e@example.com"');
  git(repo, 'config user.name "ZECT E2E"');
  for (const [rel, body] of Object.entries(files)) {
    const dest = path.join(repo, rel);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.writeFileSync(dest, body);
  }
  git(repo, "add .");
  git(repo, `commit -m "init ${label}"`);
  return { root, repo, label };
}

export async function headers(page: Page) {
  const token = await page.evaluate(() => localStorage.getItem("zect_token"));
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export async function api(page: Page, method: string, pathName: string, body?: unknown) {
  const res = await page.request.fetch(`${API}${pathName}`, {
    method,
    headers: await headers(page),
    data: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  return { status: res.status(), data };
}

export async function apiRetry(page: Page, method: string, pathName: string, body?: unknown, tries = 4) {
  let last = { status: 0, data: {} as Record<string, unknown> };
  for (let i = 0; i < tries; i += 1) {
    last = await api(page, method, pathName, body);
    if (last.status < 300) return last;
    await page.waitForTimeout(1200);
  }
  return last;
}

/** AGENT tab owns mission goal / Start — ASK is a separate pane. */
export async function openCodingAgentMission(page: Page) {
  const showAgent = page.getByTestId("workspace-toggle-agent");
  if ((await showAgent.count()) && (await showAgent.getAttribute("aria-pressed")) === "false") {
    await showAgent.click();
  }
  await expect(page.getByTestId("mentrix-coding-agent-panel")).toBeVisible({ timeout: 20_000 });
  await page.getByTestId("mentrix-coding-agent-mission-tab").click();
  await expect(page.getByTestId("mentrix-coding-agent-mission-goal")).toBeVisible({ timeout: 15_000 });
}

export async function hideImportPanel(page: Page) {
  const panel = page.getByTestId("workspace-import-panel");
  if (!(await panel.isVisible().catch(() => false))) return;
  const btn = page.getByTestId("workspace-import-local");
  const label = ((await btn.textContent()) || "").toLowerCase();
  if (label.includes("hide")) {
    await btn.click();
  }
}

export async function sidebarOpen(page: Page, name: string, testId: string, timeout = 30_000) {
  await page.getByTestId("app-sidebar").getByRole("link", { name, exact: true }).click();
  await expect(page.getByTestId(testId)).toBeVisible({ timeout });
}

export async function bindActiveProject(page: Page, projectId: number, repoId: number) {
  await page.evaluate(
    ({ projectId: pid, repoId: rid }) => {
      localStorage.setItem(
        "zect_active_project",
        JSON.stringify({ projectId: pid, repoId: rid, branch: "main" }),
      );
    },
    { projectId, repoId },
  );
}

export async function openCompanionVoice(page: Page) {
  const close = page.getByTestId("mentrix-artifacts-close");
  if (await close.isVisible().catch(() => false)) {
    await close.click();
  }
  const exitDisplay = page.getByTestId("mentrix-present-narrate-display");
  if (await exitDisplay.isVisible().catch(() => false)) {
    await exitDisplay.click();
  }
  await page.getByTestId("mentrix-mode-voice").click({ force: true });
  await expect(page.getByTestId("mentrix-mode-voice")).toHaveAttribute("aria-selected", "true", {
    timeout: 10_000,
  });
  const section = page.getByTestId("mentrix-voice-section");
  await expect(section).toBeAttached({ timeout: 10_000 });
  await section.scrollIntoViewIfNeeded().catch(() => undefined);
  await expect(section).toBeVisible({ timeout: 20_000 });
}

export async function openWorkspace(page: Page, projectId: number, repoId: number) {
  await bindActiveProject(page, projectId, repoId);
  await page.evaluate(() => window.location.assign("/workspace"));
  await page.waitForURL(/\/workspace/, { timeout: 20_000 });
  await expect(page.getByTestId("developer-workspace")).toBeVisible({ timeout: 30_000 });
  await hideImportPanel(page);
}
