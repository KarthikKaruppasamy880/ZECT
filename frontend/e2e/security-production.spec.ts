/**
 * Security / governance production (headed).
 * Unauthed privileged routes bounce to login. Authed Permissions / Security /
 * Sandbox are visible. Live Jira/Camunda ingest is never clicked. Live SSRF /
 * OAuth pentest is not claimed PASS.
 */
import { test, expect } from "@playwright/test";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { gotoAuthed } from "./helpers/login";

const FRONTEND = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const REPO = path.resolve(FRONTEND, "..");
const ART = path.join(REPO, "test-results", "security-production");
const API = process.env.VITE_API_URL || process.env.ZECT_API_URL || "http://127.0.0.1:8000";

test.describe("security production — unauthenticated", () => {
  test.use({ storageState: { cookies: [], origins: [] } });
  test.setTimeout(60_000);

  test("privileged routes bounce to login", async ({ page }) => {
    fs.mkdirSync(ART, { recursive: true });
    await page.goto("/permissions");
    await expect(page.getByTestId("login-username")).toBeVisible({ timeout: 20_000 });
    await page.screenshot({ path: path.join(ART, "01-unauth-permissions.png") });

    await page.goto("/security-incidents");
    await expect(page.getByTestId("login-username")).toBeVisible({ timeout: 20_000 });

    const git = await page.request.post(`${API}/api/git/push`, {
      data: { repo_path: "/tmp/x", remote: "origin" },
      headers: { "Content-Type": "application/json" },
    });
    expect([401, 403]).toContain(git.status());

    const runner = await page.request.post(`${API}/api/runner/execute`, {
      data: { command: "echo hi", cwd: "/tmp" },
      headers: { "Content-Type": "application/json" },
    });
    expect([401, 403]).toContain(runner.status());

    const oidc = await page.request.get(`${API}/api/auth/oidc/login-url`);
    expect([400, 503]).toContain(oidc.status());
  });
});

test.describe("security production — authenticated", () => {
  test.setTimeout(120_000);

  test("permissions, security agent, sandbox, processes stay fail-closed", async ({ page }) => {
    fs.mkdirSync(ART, { recursive: true });
    const evidence: Record<string, unknown> = {
      live_jira_clicked: false,
      live_camunda_clicked: false,
      live_ssrf_pentest: false,
      live_oauth_pentest: false,
    };

    await gotoAuthed(page, "/permissions", "permissions-page");
    await expect(page.getByRole("heading", { name: /Permissions Protocol/i })).toBeVisible();
    await page.getByRole("button", { name: /Audit Log/i }).click();
    await page.screenshot({ path: path.join(ART, "02-permissions-audits.png") });

    await gotoAuthed(page, "/security-incidents", "security-incidents-page");
    await expect(page.getByTestId("security-malware-panel")).toBeVisible();
    await page.screenshot({ path: path.join(ART, "03-security-incidents.png") });

    await gotoAuthed(page, "/sandbox", "sandbox-page");
    await expect(page.getByTestId("sandbox-check")).toBeVisible();
    await page.screenshot({ path: path.join(ART, "04-sandbox.png") });

    await gotoAuthed(page, "/fabric", "mentrix-fabric-page");
    await expect(page.getByTestId("process-connector-status")).toBeVisible();
    const jira = page.getByTestId("process-connector-jira");
    const camunda = page.getByTestId("process-connector-camunda");
    const jiraLabel = ((await jira.innerText()) || "").toLowerCase();
    const camundaLabel = ((await camunda.innerText()) || "").toLowerCase();
    evidence.jira_chip = jiraLabel;
    evidence.camunda_chip = camundaLabel;
    await expect(page.getByTestId("process-ingest-submit")).toBeVisible();
    // Never click live Jira/Camunda ingest — unset connectors stay BLOCKED_EXTERNAL.
    await page.screenshot({ path: path.join(ART, "05-processes-connectors.png") });

    fs.writeFileSync(path.join(ART, "evidence.json"), JSON.stringify(evidence, null, 2));
  });
});
