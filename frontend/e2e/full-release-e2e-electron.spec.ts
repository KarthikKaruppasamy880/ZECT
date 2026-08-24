/**
 * Tranche H Electron full-release journey. Shell load is not PASS.
 * Skip if electron.exe is missing — skip ≠ PASS.
 * Live Presenton Generate / Voicebox / PowerPoint COM remain BLOCKED_EXTERNAL.
 */
import { test, expect, _electron as electron, type ElectronApplication, type Page } from "@playwright/test";
import fs from "fs";
import os from "os";
import path from "path";
import { fileURLToPath } from "url";
import { loadEnvCreds } from "./helpers/env";
import { API, makeGitRepo, openCodingAgentMission, openCompanionVoice, openWorkspace } from "./helpers/releaseJourney";

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const ART = path.join(REPO, "test-results", "full-release-e2e-electron");
const ELECTRON_MAIN = path.join(REPO, "electron", "main.js");
const ELECTRON_EXE = path.join(REPO, "electron", "node_modules", "electron", "dist", "electron.exe");
const BASE = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173";

test.describe("full release E2E electron", () => {
  test.setTimeout(300_000);

  test("login, Companion, multi-root restore, Developer, Present, Voice, recovery", async () => {
    const electronPresent = fs.existsSync(ELECTRON_EXE);
    if (!electronPresent && process.env.ZECT_REQUIRE_ELECTRON === "1") {
      throw new Error("ZECT_REQUIRE_ELECTRON=1 but electron.exe is missing — skip ≠ PASS");
    }
    test.skip(!electronPresent, "Electron binary is not installed in electron/node_modules");
    fs.mkdirSync(ART, { recursive: true });
    const userData = fs.mkdtempSync(path.join(os.tmpdir(), "zect-electron-h-"));
    const { username, password } = loadEnvCreds();
    const evidence: Record<string, unknown> = {
      shell_only: false,
      live_generate_clicked: false,
      powerpoint_com: "BLOCKED_EXTERNAL",
      voicebox_online: null,
    };

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
      if (await page.getByTestId("login-username").isVisible({ timeout: 15_000 }).catch(() => false)) {
        await page.getByTestId("login-username").fill(username);
        await page.getByTestId("login-password").fill(password);
        await page.getByTestId("login-submit").click();
        await expect(page.getByTestId("login-submit")).toBeHidden({ timeout: 30_000 });
      }
      await page.getByTestId("auth-checking").waitFor({ state: "hidden", timeout: 12_000 }).catch(() => {});
      await expect(page.getByTestId("app-sidebar")).toBeVisible({ timeout: 30_000 });
    };

    const sessionToken = async (page: Page) => {
      const handle = await page.waitForFunction(() => localStorage.getItem("zect_token"), null, {
        timeout: 20_000,
      });
      return handle.jsonValue();
    };

    const first = await launch();
    let page = first.page;
    try {
      await loginIfNeeded(page);
      evidence.session_after_login = true;

      const token = await sessionToken(page);
      const created = await page.request.post(`${API}/api/projects`, {
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        data: {
          name: `H Electron ${Date.now()}`,
          description: "full-release electron",
          team: "E2E",
          current_stage: "ask",
        },
      });
      const project = await created.json();
      const projectId = Number(project.id);
      const explorer = makeGitRepo("alpha", { "README.md": "# alpha\n" });
      const coding = makeGitRepo("backend", {
        "calc.py": "def add(a, b):\n    return a - b\n",
        "tests/test_calc.py": "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
      });
      const ids: number[] = [];
      for (const localPath of [explorer.repo, coding.repo]) {
        const reg = await page.request.post(`${API}/api/repos/register-local`, {
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          data: { local_path: localPath, project_id: projectId },
        });
        const body = await reg.json();
        ids.push(Number(body.repo_id));
      }

      const nav = page.getByTestId("app-sidebar");
      await nav.getByRole("link", { name: "Mentrix Companion" }).click();
      await expect(page.getByTestId("mentrix-companion-page")).toBeVisible({ timeout: 30_000 });
      await expect(page.getByTestId("mentrix-companion-input")).toBeVisible();
      await page.screenshot({ path: path.join(ART, "01-companion.png") });

      await openWorkspace(page, projectId, ids[1]);
      await expect(page.getByTestId("workspace-roots-rail")).toBeVisible({ timeout: 20_000 });
      await expect(page.getByTestId(`workspace-root-${ids[0]}`)).toBeVisible();
      await expect(page.getByTestId(`workspace-root-${ids[1]}`)).toBeVisible();
      const readme = page.getByTestId(`workspace-file-${ids[0]}-README.md`);
      if (await readme.isVisible().catch(() => false)) {
        await readme.click();
        await expect(page.getByTestId("workspace-open-path")).toContainText(/README/i);
      }
      const showTools = page.getByTestId("workspace-toggle-bottom");
      if (await showTools.isVisible().catch(() => false)) {
        const pressed = await showTools.getAttribute("aria-pressed");
        if (pressed === "false") await showTools.click();
      }
      await expect(page.getByTestId("workspace-terminal")).toBeVisible({ timeout: 15_000 });
      await openCodingAgentMission(page);
      await page.getByTestId("mentrix-coding-agent-mission-goal").fill("Fix add() so 2+3 is 5");
      await page.getByTestId("mentrix-coding-agent-patches-toggle").click();
      await page.getByTestId("mentrix-coding-agent-patches").fill(
        JSON.stringify({
          [String(ids[1])]: [{ path: "calc.py", old: "return a - b", new: "return a + b" }],
        }),
      );
      await page.getByTestId("mentrix-coding-agent-start-mission").click();
      await expect(page.getByTestId("mentrix-coding-agent-phase")).toContainText("awaiting_plan_approval", {
        timeout: 30_000,
      });
      evidence.coding_mission = "plan";
      await page.screenshot({ path: path.join(ART, "02-developer-mission.png") });

      await nav.getByRole("link", { name: "Present" }).click();
      await expect(page.getByTestId("zect-present-page")).toBeVisible({ timeout: 30_000 });
      await expect(page.getByTestId("present-dashboard")).toBeVisible();
      await expect(page.getByTestId("present-import")).toBeVisible();
      await page.getByTestId("present-create-with-ai").click();
      await expect(page.getByTestId("zect-present-workspace")).toBeVisible({ timeout: 20_000 });
      await page.getByTestId("zect-present-template-zinnia-executive-v1").click();
      await page.getByTestId("zect-present-continue-generate").click();
      await expect(page.getByTestId("present-deck-generate")).toBeVisible();
      evidence.presenton_generate_enabled = await page.getByTestId("present-deck-generate").isEnabled();
      await page.getByTestId("present-nav-dashboard").click();
      await page.getByTestId("present-blank").click();
      await expect(page.getByTestId("present-studio")).toBeVisible({ timeout: 25_000 });
      await page.getByTestId("present-open-export").click();
      await expect(page.getByTestId("present-export")).toBeVisible({ timeout: 15_000 });
      await page.screenshot({ path: path.join(ART, "03-present.png") });

      await nav.getByRole("link", { name: "Mentrix Companion" }).click();
      await expect(page.getByTestId("mentrix-companion-page")).toBeVisible({ timeout: 30_000 });
      await openCompanionVoice(page);
      await page.screenshot({ path: path.join(ART, "04-voice.png") });

      await first.app.close();
      await new Promise((r) => setTimeout(r, 2000));

      const second = await launch();
      page = second.page;
      try {
        await loginIfNeeded(page);
        await openWorkspace(page, projectId, ids[1]);
        await expect(page.getByTestId(`workspace-root-${ids[0]}`)).toBeVisible({ timeout: 30_000 });
        await expect(page.getByTestId(`workspace-root-${ids[1]}`)).toBeVisible({ timeout: 30_000 });
        evidence.restore_after_restart = true;
        await page.screenshot({ path: path.join(ART, "05-restore.png") });
      } finally {
        await second.app.close();
      }
    } catch (err) {
      await first.app.close().catch(() => {});
      throw err;
    }

    fs.writeFileSync(path.join(ART, "evidence.json"), JSON.stringify(evidence, null, 2));
  });
});
