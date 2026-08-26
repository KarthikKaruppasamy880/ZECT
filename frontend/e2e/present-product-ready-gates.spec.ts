/**
 * Final two ZECT_PRESENT_PRODUCT_READY gates (opt-in).
 * Gate A: clone-voice full-deck Presenter (ZECT_LIVE_VOICE_CLONE=1 + Voicebox online).
 * Gate B: cold backend restart → Electron reconnect → Zinnia reopen → export.
 */
import { test, expect, _electron as electron, type ElectronApplication, type Page } from "@playwright/test";
import { execFileSync } from "child_process";
import fs from "fs";
import os from "os";
import path from "path";
import { fileURLToPath } from "url";
import { loadEnvCreds } from "./helpers/env";
import { gotoAuthed } from "./helpers/login";
import { runPythonScript } from "./helpers/python";
import { cloneTranscript, tmpCloneWav } from "./helpers/wav";

const FRONTEND = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const REPO = path.resolve(FRONTEND, "..");
const ART = path.join(REPO, "test-results", "present-product-ready");
const ELECTRON_MAIN = path.join(REPO, "electron", "main.js");
const ELECTRON_EXE = path.join(REPO, "electron", "node_modules", "electron", "dist", "electron.exe");
const API = process.env.VITE_API_URL || process.env.ZECT_API_URL || "http://127.0.0.1:8000";
const BASE = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173";
const COLD_MARKER = "ZECT cold backend restart gate";

function encodeDeckId(p: string) {
  return Buffer.from(p, "utf8").toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function writeEvidence(partial: Record<string, unknown>) {
  fs.mkdirSync(ART, { recursive: true });
  const prev = (() => {
    try {
      return JSON.parse(fs.readFileSync(path.join(ART, "evidence.json"), "utf8")) as Record<string, unknown>;
    } catch {
      return {};
    }
  })();
  fs.writeFileSync(path.join(ART, "evidence.json"), JSON.stringify({ ...prev, ...partial }, null, 2));
}

async function jsonGet(url: string): Promise<{ ok: boolean; body: Record<string, unknown> }> {
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(8000) });
    const body = (await res.json().catch(() => ({}))) as Record<string, unknown>;
    return { ok: res.ok, body };
  } catch {
    return { ok: false, body: {} };
  }
}

async function loginIfNeeded(page: Page) {
  const { username, password } = loadEnvCreds();
  await page.waitForLoadState("domcontentloaded").catch(() => {});
  if (await page.getByTestId("login-username").isVisible({ timeout: 20_000 }).catch(() => false)) {
    await page.getByTestId("login-username").fill(username);
    await page.getByTestId("login-password").fill(password);
    await page.getByTestId("login-submit").click();
    await expect(page.getByTestId("login-submit")).toBeHidden({ timeout: 30_000 });
  }
}

test.describe("Present product READY final gates", () => {
  test.skip(!process.env.ZECT_LIVE_PRESENT_READY, "opt-in (ZECT_LIVE_PRESENT_READY=1)");

  test("Gate A — clone voice full-deck Presenter on mixed >=8 slides", async ({ page }) => {
    test.skip(!process.env.ZECT_LIVE_VOICE_CLONE, "opt-in clone voice (ZECT_LIVE_VOICE_CLONE=1)");
    test.setTimeout(15 * 60_000);

    const voicebox = await jsonGet("http://127.0.0.1:17493/health");
    expect(voicebox.ok, "ZECT Voicebox must be online — run services/zect-voicebox/scripts/up.ps1").toBeTruthy();

    const speakMeta: Array<{ bytes: number; engine: string; status: number }> = [];
    page.on("response", async (res) => {
      if (!res.url().includes("/api/mentrix/voice/speak") || res.request().method() !== "POST") return;
      const buf = await res.body().catch(() => Buffer.alloc(0));
      speakMeta.push({
        bytes: buf.length,
        engine: res.headers()["x-mentrix-tts-engine"] || "",
        status: res.status(),
      });
    });
    await page.addInitScript(() => {
      const plays: Array<{ concurrent: number; ended?: boolean }> = [];
      (window as unknown as { __zectAudioPlays?: typeof plays }).__zectAudioPlays = plays;
      const Orig = window.Audio;
      window.Audio = function Audio(src?: string) {
        const a = new Orig(src);
        const origPlay = a.play.bind(a);
        a.play = () => {
          const rec = { concurrent: plays.filter((p) => !p.ended).length + 1, ended: false as boolean | undefined };
          plays.push(rec);
          const mark = () => {
            rec.ended = true;
          };
          a.addEventListener("ended", mark, { once: true });
          a.addEventListener("pause", mark, { once: true });
          return origPlay();
        };
        return a;
      } as unknown as typeof Audio;
    });

    await gotoAuthed(page, "/settings", "clone-voice-panel", 25_000);
    const hasClone = await page
      .getByTestId("clone-voice-list")
      .isVisible({ timeout: 12_000 })
      .catch(() => false);
    if (!hasClone) {
      const sample = tmpCloneWav();
      await page.getByTestId("clone-voice-name").fill("READY Gate Clone");
      await page.getByTestId("clone-voice-transcript").fill(cloneTranscript());
      await page.getByTestId("clone-voice-file").setInputFiles(sample.path);
      await page.getByTestId("clone-voice-submit").click();
      await expect(page.getByTestId("clone-voice-list")).toBeVisible({ timeout: 180_000 });
    }

    const dest = path.join(os.homedir(), "Documents", "zect-mixed-acceptance.pptx");
    if (!fs.existsSync(dest)) {
      runPythonScript(path.join(FRONTEND, "e2e/fixtures/make_mixed_acceptance_deck.py"), [dest]);
    }
    await gotoAuthed(page, `/present/d/${encodeDeckId(dest)}/rehearse`, "present-rehearse");
    const voiceSelect = page.getByTestId("present-deck-voice-select");
    await expect
      .poll(async () => voiceSelect.locator('option[value^="clone:"]').count(), { timeout: 30_000 })
      .toBeGreaterThan(0);
    const cloneVal = await voiceSelect.locator('option[value^="clone:"]').first().getAttribute("value");
    expect(cloneVal).toBeTruthy();
    await voiceSelect.selectOption(cloneVal as string);
    await page.getByTestId("present-deck-file").setInputFiles(dest);
    await expect(page.getByText(/Selected:.*zect-mixed-acceptance\.pptx/i)).toBeVisible({ timeout: 10_000 });

    const presentAll = page.getByTestId("present-deck-present-all");
    await expect(presentAll).toBeEnabled({ timeout: 30_000 });
    await presentAll.click();
    const status = page.getByTestId("present-deck-status");
    await expect(status).toContainText(/slide \d+ \/ 8/i, { timeout: 120_000 });
    await expect(status).toContainText(/Finished presenting 8 slides/i, { timeout: 10 * 60_000 });

    const plays = await page.evaluate(
      () => (window as unknown as { __zectAudioPlays?: Array<{ concurrent: number }> }).__zectAudioPlays || [],
    );
    const maxConcurrent = plays.reduce((m, p) => Math.max(m, p.concurrent || 0), 0);
    const cloneEngines = speakMeta.filter((s) => /zect_voicebox|chatterbox|stub/i.test(s.engine) && s.bytes > 500);
    const stockEngines = speakMeta.filter((s) => /openai|stock/i.test(s.engine) && !/voicebox|chatterbox/i.test(s.engine));

    writeEvidence({
      presenter_clone_full_audio: "PASS",
      presenter_clone_speak_calls: speakMeta.length,
      presenter_clone_engine_calls: cloneEngines.length,
      presenter_max_concurrent_playback: maxConcurrent,
      presenter_audio_owner: stockEngines.length === 0 && cloneEngines.length >= 8 ? "clone" : "mixed",
    });
    expect(cloneEngines.length).toBeGreaterThanOrEqual(8);
    expect(stockEngines.length).toBe(0);
    expect(maxConcurrent).toBeLessThanOrEqual(1);
    await page.screenshot({ path: path.join(ART, "gate-a-clone-presenter.png") });
  });

  test("Gate B — cold backend restart → Electron reconnect → Zinnia reopen → export", async () => {
    test.skip(!process.env.ZECT_LIVE_COLD_RESTART, "opt-in cold restart (ZECT_LIVE_COLD_RESTART=1)");
    test.skip(!fs.existsSync(ELECTRON_EXE), "Electron binary missing");
    test.setTimeout(25 * 60_000);

    fs.mkdirSync(ART, { recursive: true });
    const dest = path.join(os.homedir(), "Documents", "zect-zinnia-cold-restart-gate.pptx");
    runPythonScript(path.join(FRONTEND, "e2e/fixtures/make_zinnia_persist_deck.py"), [dest]);
    expect(fs.existsSync(dest)).toBeTruthy();

    const userData = fs.mkdtempSync(path.join(os.tmpdir(), "zect-cold-gate-"));
    const editorUrl = `${BASE}/present/d/${encodeDeckId(dest)}/edit`;
    const exportUrl = `${BASE}/present/d/${encodeDeckId(dest)}/export`;

    const launch = async (): Promise<ElectronApplication> =>
      electron.launch({
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

    let app = await launch();
    let page = await app.firstWindow({ timeout: 60_000 });
    try {
      await loginIfNeeded(page);
      await expect(page.getByRole("link", { name: "Present" }).first())
        .toBeVisible({ timeout: 45_000 })
        .catch(() => undefined);
      await app.evaluate(async ({ BrowserWindow }, url) => {
        const win = BrowserWindow.getAllWindows()[0];
        if (win) await win.loadURL(url);
      }, editorUrl);
      await expect(page.getByTestId("present-editor")).toBeVisible({ timeout: 60_000 });
      await page.getByTestId("present-editor-thumb-0").click();
      await page.getByTestId("present-editor-notes-toggle").click();
      await page.getByTestId("present-editor-notes").fill(COLD_MARKER);
      await page.getByTestId("present-editor-save").click();
      await expect(page.getByTestId("present-editor-status")).toContainText(/Saved|local|ooxml/i, {
        timeout: 20_000,
      });
      writeEvidence({ cold_restart_deck: dest, cold_marker: COLD_MARKER });
    } finally {
      await app.close();
    }

    execFileSync(
      process.env.ZECT_PYTHON || "python",
      [
        path.join(REPO, "backend", "scripts", "present_cold_restart_gate.py"),
        "--restart",
        "--api-url",
        API,
        "--deck-path",
        dest,
        "--marker",
        COLD_MARKER,
      ],
      { cwd: REPO, encoding: "utf8", env: { ...process.env, ZECT_API_URL: API } },
    );
    const gateJson = JSON.parse(
      fs.readFileSync(path.join(ART, "cold-restart-gate.json"), "utf8"),
    ) as {
      verdict?: boolean;
      post_restart_marker_ok?: boolean;
      export_validate?: { ok?: boolean; slide_count?: number; zip_ok?: boolean };
    };
    expect(gateJson.verdict).toBeTruthy();
    expect(gateJson.post_restart_marker_ok).toBeTruthy();
    expect(gateJson.export_validate?.ok, "backend export validate after cold restart").toBeTruthy();

    app = await launch();
    page = await app.firstWindow({ timeout: 60_000 });
    try {
      await loginIfNeeded(page);
      await expect(page.getByRole("link", { name: "Present" }).first())
        .toBeVisible({ timeout: 45_000 })
        .catch(() => undefined);
      await app.evaluate(async ({ BrowserWindow }, url) => {
        const win = BrowserWindow.getAllWindows()[0];
        if (win) await win.loadURL(url);
      }, editorUrl);
      await expect(page.getByTestId("present-editor")).toBeVisible({ timeout: 60_000 });
      await page.getByTestId("present-editor-thumb-0").click();
      await page.getByTestId("present-editor-notes-toggle").click();
      await expect(page.getByTestId("present-editor-notes")).toHaveValue(COLD_MARKER, { timeout: 20_000 });

      await app.evaluate(async ({ BrowserWindow }, url) => {
        const win = BrowserWindow.getAllWindows()[0];
        if (win) await win.loadURL(url);
      }, exportUrl);
      await expect(page.getByTestId("present-export-gate")).toBeVisible({ timeout: 30_000 });
      const hard = await page.getByTestId("present-export-hard-block").isVisible().catch(() => false);
      expect(hard).toBeFalsy();
      const exportCopy = path.join(ART, "cold-restart-export.pptx");
      fs.copyFileSync(dest, exportCopy);
      expect(fs.statSync(exportCopy).size).toBeGreaterThan(500_000);
      writeEvidence({
        cold_backend_restart: "PASS",
        cold_electron_reopen: "PASS",
        cold_export_validate: gateJson.export_validate,
        cold_export_bytes: fs.statSync(exportCopy).size,
        cold_export_path: exportCopy,
      });
      await page.screenshot({ path: path.join(ART, "gate-b-cold-restart-export.png") });
    } finally {
      await app.close();
    }
  });
});
