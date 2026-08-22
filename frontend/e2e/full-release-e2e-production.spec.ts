/**
 * Tranche H: one coherent headed release journey.
 * Login → Project → multi-root Developer → Companion → WorkItem →
 * Coding Agent (tests/review) → Present → Voice → Process/status.
 * Live Presenton Generate / Voicebox / Jira / Camunda / PowerPoint COM
 * are recorded, never converted from skip to PASS.
 */
import { test, expect } from "@playwright/test";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { gotoAuthed } from "./helpers/login";
import {
  api,
  apiRetry,
  hideImportPanel,
  makeGitRepo,
  openCodingAgentMission,
  openWorkspace,
  sidebarOpen,
} from "./helpers/releaseJourney";

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const ART = path.join(REPO, "test-results", "full-release-e2e-production");

test.describe("full release E2E production", () => {
  test.setTimeout(300_000);

  test("coherent journey Login through Process status", async ({ page }) => {
    fs.mkdirSync(ART, { recursive: true });
    const evidence: Record<string, unknown> = {
      live_generate_clicked: false,
      live_ingest_clicked: false,
      voicebox_online: null,
      powerpoint_com: "not_run",
    };

    await gotoAuthed(page, "/projects", "projects-page");
    await expect(page.getByTestId("login-username")).toHaveCount(0);

    const stamp = Date.now();
    const keepName = `H Auth ${stamp}`;
    const dropName = `H Fixture ${stamp}`;
    const created = await api(page, "POST", "/api/projects", {
      name: keepName,
      description: "full-release coherent journey",
      team: "E2E",
      provenance: "user",
    });
    expect(created.status).toBe(201);
    const projectId = Number(created.data.id);
    const fixture = await api(page, "POST", "/api/projects", {
      name: dropName,
      description: "test fixture",
      team: "E2E",
      provenance: "test",
      test_run_id: `h-e2e-${stamp}`,
    });
    expect(fixture.status).toBe(201);

    const explorer = makeGitRepo("alpha", { "README.md": "# alpha\n" });
    const coding = makeGitRepo("backend", {
      "calc.py": "def add(a, b):\n    return a - b\n",
      "tests/test_calc.py": "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
    });
    const regA = await apiRetry(page, "POST", "/api/repos/register-local", {
      local_path: explorer.repo,
      project_id: projectId,
    });
    const regB = await apiRetry(page, "POST", "/api/repos/register-local", {
      local_path: coding.repo,
      project_id: projectId,
    });
    expect(regA.status).toBeLessThan(300);
    expect(regB.status).toBeLessThan(300);
    const idA = Number(regA.data.repo_id);
    const idB = Number(regB.data.repo_id);
    await openWorkspace(page, projectId, idB);

    await expect(page.getByTestId("workspace-roots-rail")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId(`workspace-root-${idA}`)).toBeVisible();
    await expect(page.getByTestId(`workspace-root-${idB}`)).toBeVisible();
    const readme = page.getByTestId(`workspace-file-${idA}-README.md`);
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
    await page.screenshot({ path: path.join(ART, "01-developer-multi-root.png") });

    await sidebarOpen(page, "Mentrix Companion", "mentrix-companion-page");
    await expect(page.getByTestId("mentrix-companion-input")).toBeVisible();
    await expect(page.getByTestId("mentrix-companion-send")).toBeVisible();
    await expect(page.getByTestId(`mentrix-companion-root-${idA}`)).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId(`mentrix-companion-root-${idB}`)).toBeVisible({ timeout: 20_000 });
    await page.screenshot({ path: path.join(ART, "02-companion.png") });

    await sidebarOpen(page, "Projects", "projects-page");
    await expect(page.getByTestId("projects-page").getByRole("heading", { name: keepName, exact: true })).toBeVisible();
    await expect(page.getByTestId("projects-page").getByRole("heading", { name: dropName, exact: true })).toHaveCount(0);

    await sidebarOpen(page, "Work Items", "work-items-page");
    await page.getByTestId("work-items-sample").click();
    const sampleBtn = page.getByRole("button", { name: /Fix Failed Order Validation/ });
    await expect(sampleBtn).toBeVisible({ timeout: 20_000 });
    await sampleBtn.click();
    await expect(page.getByTestId("work-item-detail")).toBeVisible();
    await expect(page.getByTestId("work-item-status")).toBeVisible();
    await page.screenshot({ path: path.join(ART, "03-work-item.png") });

    await sidebarOpen(page, "Developer", "developer-workspace");
    await hideImportPanel(page);
    await openCodingAgentMission(page);
    await page.getByTestId("mentrix-coding-agent-mission-goal").fill("Fix add() so 2+3 is 5");
    await page.getByTestId("mentrix-coding-agent-patches-toggle").click();
    await page.getByTestId("mentrix-coding-agent-patches").fill(
      JSON.stringify({
        [String(idB)]: [{ path: "calc.py", old: "return a - b", new: "return a + b" }],
      }),
    );
    await page.getByTestId("mentrix-coding-agent-start-mission").click();
    await expect(page.getByTestId("mentrix-coding-agent-phase")).toContainText("awaiting_plan_approval", {
      timeout: 30_000,
    });
    await page.getByTestId("mentrix-coding-agent-approve-plan").click();
    await expect(page.getByTestId("mentrix-coding-agent-phase")).toContainText("awaiting_git_approval", {
      timeout: 120_000,
    });
    await expect(page.getByTestId("mentrix-coding-agent-tests")).toContainText("pass");
    await page.getByTestId("mentrix-coding-agent-open-diff").click();
    await expect(page.getByTestId("mentrix-coding-agent-diff")).toBeVisible();
    evidence.coding_phase = await page.getByTestId("mentrix-coding-agent-phase").innerText();
    await page.screenshot({ path: path.join(ART, "04-coding-tests-review.png") });

    await sidebarOpen(page, "Present", "zect-present-page");
    await expect(page.getByTestId("present-dashboard")).toBeVisible();
    await expect(page.getByTestId("zect-present-template-zinnia-executive-v1")).toBeVisible();
    await page.getByTestId("present-create-with-ai").click();
    await expect(page.getByTestId("zect-present-workspace")).toBeVisible({ timeout: 20_000 });
    await page.getByTestId("zect-present-template-zinnia-executive-v1").click();
    await page.getByTestId("zect-present-continue-generate").click();
    await expect(page.getByTestId("present-deck-generate")).toBeVisible();
    const genEnabled = await page.getByTestId("present-deck-generate").isEnabled();
    evidence.presenton_generate_enabled = genEnabled;
    if (!genEnabled) evidence.present_generate = "BLOCKED_EXTERNAL";
    await page.getByTestId("present-nav-dashboard").click();
    await page.getByTestId("present-blank").click();
    await expect(page.getByTestId("present-studio")).toBeVisible({ timeout: 25_000 });
    await page.getByTestId("present-editor-notes-toggle").click();
    await page.getByTestId("present-editor-notes").fill("Full-release E2E note.");
    await page.getByTestId("present-editor-save").click();
    await page.getByTestId("present-open-export").click();
    await expect(page.getByTestId("present-export")).toBeVisible({ timeout: 15_000 });
    const hard = await page.getByTestId("present-export-hard-block").isVisible().catch(() => false);
    expect(hard, "blank deck must export").toBeFalsy();
    const warn = page.getByTestId("present-export-accept-warnings");
    if (await warn.isVisible().catch(() => false)) {
      await warn.locator("input").check();
    }
    const exportBtn = page.getByTestId("present-export-pptx");
    if (await exportBtn.isEnabled()) {
      const downloadPromise = page.waitForEvent("download", { timeout: 20_000 });
      await exportBtn.click();
      const download = await downloadPromise;
      const outFile = path.join(ART, download.suggestedFilename() || "full-release-blank.pptx");
      await download.saveAs(outFile);
      evidence.blank_export_bytes = fs.statSync(outFile).size;
      expect(fs.statSync(outFile).size).toBeGreaterThan(100);
    }
    evidence.powerpoint_com = "BLOCKED_EXTERNAL";
    await page.screenshot({ path: path.join(ART, "05-present-export.png") });

    await sidebarOpen(page, "Mentrix Companion", "mentrix-companion-page");
    await page.getByTestId("mentrix-mode-voice").click();
    await expect(page.getByTestId("clone-voice-panel")).toBeVisible({ timeout: 20_000 });
    const engine = page.getByTestId("clone-voice-engine-status");
    if (await engine.isVisible().catch(() => false)) {
      await engine.waitFor({ state: "visible", timeout: 5_000 }).catch(() => {});
      await page.waitForTimeout(3_000);
      const txt = (await engine.innerText()).toLowerCase();
      evidence.voicebox_status_text = txt;
      evidence.voicebox_online = /\bonline\b|\bready\b/.test(txt) && !/offline|start |checking/.test(txt);
      if (!evidence.voicebox_online) evidence.voice = "BLOCKED_EXTERNAL";
    } else {
      evidence.voice = "BLOCKED_EXTERNAL";
    }
    await page.screenshot({ path: path.join(ART, "06-voice.png") });

    await sidebarOpen(page, "Processes", "mentrix-fabric-page");
    await expect(page.getByTestId("process-sample-card")).toBeVisible();
    await expect(page.getByTestId("process-connector-status")).toBeVisible();
    evidence.jira_status = await page.getByTestId("process-connector-jira").getAttribute("data-status");
    evidence.camunda_status = await page.getByTestId("process-connector-camunda").getAttribute("data-status");
    evidence.live_ingest_clicked = false;
    await page.screenshot({ path: path.join(ART, "07-processes.png") });

    fs.writeFileSync(path.join(ART, "evidence.json"), JSON.stringify(evidence, null, 2));
  });
});
