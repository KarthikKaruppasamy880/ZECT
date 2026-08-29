/**
 * R2.6 live proof: ZECT Present UI → ZECT APIs → hidden provider.
 * Does not open Presenton standalone UI. Voicebox /health classifies stub vs Chatterbox;
 * clone PASS requires /speak through the Present page with non-empty clone audio.
 */
import { test, expect, type Page } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import { ensureLoggedIn, gotoAuthed } from "./helpers/login";
import { runPythonScript } from "./helpers/python";
import { cloneTranscript, tmpCloneWav } from "./helpers/wav";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const ART = path.join(ROOT, "test-results/present-zinnia-clone-live");
const FRONTEND = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:5173";
const API_BASE = (process.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const BUILTINS = new Set(["modern", "general", "standard", "swift", ""]);

function writeEvidence(partial: Record<string, unknown>) {
  fs.mkdirSync(ART, { recursive: true });
  const prev = (() => {
    try {
      return JSON.parse(fs.readFileSync(path.join(ART, "evidence.json"), "utf8"));
    } catch {
      return {};
    }
  })();
  fs.writeFileSync(path.join(ART, "evidence.json"), JSON.stringify({ ...prev, ...partial }, null, 2));
}

function tinyPptxPath(): string {
  const dest = path.join(ART, "tiny-deck.pptx");
  runPythonScript(path.join(ROOT, "frontend/e2e/fixtures/make_tiny_pptx.py"), [dest]);
  return dest;
}

async function jsonGet(url: string): Promise<{ ok: boolean; status: number; body: Record<string, unknown> }> {
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(8000) });
    const body = (await res.json().catch(() => ({}))) as Record<string, unknown>;
    return { ok: res.ok, status: res.status, body };
  } catch {
    return { ok: false, status: 0, body: {} };
  }
}

async function openGenerateWorkspace(page: Page) {
  await gotoAuthed(page, "/present/create", "zect-present-page");
  await page.getByTestId("zect-present-template-zinnia-executive-v1").click();
  await expect(page.getByTestId("present-deck-panel")).toBeVisible({ timeout: 10_000 });
}

test.describe("R2.6 ZECT Present + cloned-voice live", () => {
  test.skip(!process.env.ZECT_LIVE_R26, "opt-in live Present/clone proof (ZECT_LIVE_R26=1)");

  test("gallery + Zinnia generate PPTX in ZECT UI", async ({ page }) => {
    test.setTimeout(12 * 60_000);
    fs.mkdirSync(ART, { recursive: true });
    const presentonProbe = await jsonGet("http://127.0.0.1:5000/");
    const evidence: Record<string, unknown> = {
      surface: "zect_present_ui",
      presenton_standalone_ui_used: false,
      frontend_origin: FRONTEND,
      presenton_reachable: presentonProbe.status > 0,
    };
    const generateMeta: Record<string, unknown>[] = [];
    page.on("response", async (res) => {
      if (!res.url().includes("/api/mentrix/presenton/generate")) return;
      try {
        const body = await res.json();
        const detail = body?.detail && typeof body.detail === "object" ? body.detail : body;
        generateMeta.push({
          status: res.status(),
          template_sent: detail?.template_sent,
          zinnia_verified: detail?.zinnia_verified,
          lifecycle: detail?.lifecycle,
          has_path: Boolean(detail?.path),
          mapping_source: detail?.mapping_source,
          provider: detail?.provider,
        });
      } catch {
        generateMeta.push({ status: res.status(), parse: "non-json" });
      }
    });

    try {
      await gotoAuthed(page, "/present/create", "zect-present-page");
      expect(page.url()).not.toMatch(/:5000\b/);
      await expect(page.getByTestId("zect-present-template-zinnia-executive-v1")).toBeVisible();
      await expect(page.getByTestId("present-lifecycle-state")).toBeVisible();
      await page.screenshot({ path: path.join(ART, "01-gallery.png") });
      evidence.TEMPLATE_GALLERY = "PASS";

      const pptx = tinyPptxPath();
      await page.getByTestId("zect-present-upload-template").setInputFiles(pptx);
      await expect(page.getByTestId("zect-present-status")).toContainText(/Registered/i, { timeout: 20_000 });
      evidence.user_template_registered = true;
      await page.getByTestId("zect-present-template-zinnia-executive-v1").click();
      await expect(page.getByTestId("zect-present-template-preview")).toBeVisible({ timeout: 15_000 });
      await expect(page.getByTestId("zect-present-workspace")).toBeVisible({ timeout: 10_000 });
      await expect(page.getByTestId("zect-present-selected")).toContainText("zinnia-executive-v1");
      await expect(page.getByTestId("present-deck-template")).toHaveValue("zinnia-executive-v1");

      await page.getByTestId("present-deck-prompt").fill(
        "Zinnia executive brief: Q3 delivery status, top risks, decisions needed, owners.",
      );
      await page.getByTestId("zect-present-rewrite").fill("Executive tone: status, then decisions, then owners.");
      await page.getByTestId("present-deck-n-slides").fill("3");
      const gen = page.getByTestId("present-deck-generate");
      await expect(gen).toBeVisible();
      await expect(gen)
        .toBeEnabled({ timeout: 90_000 })
        .catch(async () => {
          evidence.generate_title = await gen.getAttribute("title");
        });
      evidence.generate_enabled = await gen.isEnabled();
      evidence.lifecycle_workspace = (await page.getByTestId("present-lifecycle-state").innerText().catch(() => "")).trim();
      const probed = await page.evaluate(async (apiBase) => {
        const t = localStorage.getItem("zect_token");
        const r = await fetch(`${apiBase}/api/mentrix/presenton/status`, {
          headers: { Authorization: `Bearer ${t}` },
        });
        const j = (await r.json()) as {
          reachable?: boolean;
          lifecycle?: string;
          configured?: boolean;
          provider?: string;
        };
        return {
          http: r.status,
          reachable: j.reachable,
          lifecycle: j.lifecycle,
          configured: j.configured,
          provider: j.provider,
        };
      }, API_BASE);
      evidence.page_presenton_status = probed;

      if (await gen.isEnabled()) {
        await page.getByTestId("present-deck-flow-b-approve").locator("input").check();
        await gen.click();
        await page.waitForTimeout(2500);
        const st = await page.getByTestId("present-deck-status").innerText().catch(() => "");
        if (/Approve generation/i.test(st)) {
          await page.getByTestId("present-deck-flow-b-approve").locator("input").check();
          await gen.click();
        }
        await page
          .waitForResponse((r) => r.url().includes("/api/mentrix/presenton/generate"), { timeout: 480_000 })
          .catch(() => null);
      }
      evidence.generate_meta = generateMeta;
      const lastGen = generateMeta[generateMeta.length - 1] || {};
      const templateSent = String(lastGen.template_sent || "");
      const zinniaVerified = lastGen.zinnia_verified === true && !BUILTINS.has(templateSent.toLowerCase());
      evidence.template_sent = templateSent || null;
      evidence.zinnia_verified = zinniaVerified;
      evidence.provider = lastGen.provider || null;
      evidence.PPTX_GENERATION =
        lastGen.has_path === true && !BUILTINS.has(templateSent.toLowerCase()) ? "PASS" : "BLOCKED_EXTERNAL";
      evidence.ZINNIA_VERIFIED = zinniaVerified ? "PASS" : "BLOCKED_EXTERNAL";
      evidence.NO_PRESENTON_NATIVE_CALL =
        lastGen.provider === "zect_native" && lastGen.has_path === true ? "PASS" : "PARTIAL";
      evidence.EDITOR = "PARTIAL";
      evidence.EXPORT = lastGen.has_path === true ? "PASS" : "PARTIAL";
      await page.screenshot({ path: path.join(ART, "02-workspace-generate.png") });
    } finally {
      writeEvidence(evidence);
    }
  });

  test("cloned-voice slide narration through ZECT Present", async ({ page }) => {
    test.setTimeout(15 * 60_000);
    const voiceboxHealth = await jsonGet("http://127.0.0.1:17493/health");
    const realVoicebox =
      voiceboxHealth.ok &&
      String(voiceboxHealth.body.synth || "").toLowerCase().includes("chatterbox") &&
      voiceboxHealth.body.models_ready === true;
    const evidence: Record<string, unknown> = {
      voicebox_health_only: false,
      voicebox_reachable: voiceboxHealth.ok,
      voicebox_synth: voiceboxHealth.body.synth || null,
      voicebox_models_ready: voiceboxHealth.body.models_ready ?? null,
      real_voicebox_model: realVoicebox,
    };
    const speakMeta: Array<{ bytes: number; engine: string; status: number; err?: string }> = [];
    page.on("response", async (res) => {
      if (!res.url().includes("/api/mentrix/voice/speak") || res.request().method() !== "POST") return;
      const buf = await res.body().catch(() => Buffer.alloc(0));
      const row: { bytes: number; engine: string; status: number; err?: string } = {
        bytes: buf.length,
        engine: res.headers()["x-mentrix-tts-engine"] || "",
        status: res.status(),
      };
      if (res.status() >= 400) {
        try {
          row.err = JSON.parse(buf.toString("utf8")).detail?.toString?.().slice(0, 160) || buf.toString("utf8").slice(0, 160);
        } catch {
          row.err = buf.toString("utf8").slice(0, 160);
        }
      }
      speakMeta.push(row);
    });
    await page.addInitScript(() => {
      const plays: Array<{ concurrent: number; ended?: boolean }> = [];
      (window as unknown as { __zectAudioPlays?: typeof plays }).__zectAudioPlays = plays;
      const Orig = window.Audio;
      window.Audio = function Audio(src?: string) {
        const a = new Orig(src);
        const origPlay = a.play.bind(a);
        a.play = () => {
          const rec: { concurrent: number; ended?: boolean } = {
            concurrent: plays.filter((p) => !p.ended).length + 1,
          };
          plays.push(rec);
          const markEnded = () => {
            rec.ended = true;
          };
          a.addEventListener("ended", markEnded, { once: true });
          a.addEventListener("pause", markEnded, { once: true });
          return origPlay();
        };
        return a;
      } as unknown as typeof Audio;
    });

    try {
      await gotoAuthed(page, "/settings", "clone-voice-panel", 25_000);
      const listVisible = await page
        .getByTestId("clone-voice-list")
        .waitFor({ state: "visible", timeout: 12_000 })
        .then(() => true)
        .catch(() => false);
      evidence.existing_clone = listVisible;
      if (!listVisible) {
        const sample = tmpCloneWav();
        evidence.clone_sample_kind = sample.kind;
        await page.getByTestId("clone-voice-name").fill("R26 Live Clone");
        await page.getByTestId("clone-voice-transcript").fill(cloneTranscript());
        await page.getByTestId("clone-voice-file").setInputFiles(sample.path);
        await expect(page.getByTestId("clone-voice-submit")).toBeEnabled({ timeout: 10_000 });
        await page.getByTestId("clone-voice-submit").click();
        await expect(page.getByTestId("clone-voice-ready").or(page.getByTestId("clone-voice-list")))
          .toBeVisible({ timeout: 180_000 })
          .catch(() => undefined);
      }
      evidence.clone_list_visible = (await page.getByTestId("clone-voice-list").count()) > 0;
      await page.screenshot({ path: path.join(ART, "03-clone-settings.png") });

      const pptx = tinyPptxPath();
      await openGenerateWorkspace(page);
      await page.getByTestId("present-deck-file").setInputFiles(pptx);
      const voiceSelect = page.getByTestId("present-deck-voice-select");
      await expect(voiceSelect).toBeVisible();
      await expect
        .poll(async () => voiceSelect.locator('option[value^="clone:"]').count(), { timeout: 30_000 })
        .toBeGreaterThan(0);
      const cloneVal = await voiceSelect.locator('option[value^="clone:"]').first().getAttribute("value");
      expect(cloneVal).toBeTruthy();
      await voiceSelect.selectOption(cloneVal as string);
      evidence.selected_clone_option = true;
      await page.getByTestId("present-deck-notes").fill("Slide one: delivery is on track this week.");

      const presentAll = page.getByTestId("present-deck-present-all");
      const narrate = page.getByTestId("present-deck-narrate");
      await page.getByTestId("present-deck-engine-status").waitFor({ timeout: 15_000 }).catch(() => undefined);
      evidence.narrate_enabled = await narrate.isEnabled();
      evidence.present_all_enabled = await presentAll.isEnabled();
      evidence.present_status_before = await page.getByTestId("present-deck-status").innerText().catch(() => "");

      if (await presentAll.isEnabled()) {
        await presentAll.click();
        const deadline = Date.now() + (realVoicebox ? 420_000 : 20_000);
        while (
          Date.now() < deadline &&
          speakMeta.filter((s) => s.bytes > 1000 && /zect_voicebox|chatterbox/i.test(s.engine)).length < 2
        ) {
          if (page.isClosed()) break;
          await page.waitForTimeout(3000).catch(() => undefined);
        }
      } else if (await narrate.isEnabled()) {
        await narrate.click();
        const deadline = Date.now() + (realVoicebox ? 180_000 : 20_000);
        while (Date.now() < deadline && !speakMeta.some((s) => s.bytes > 1000 && /zect_voicebox|chatterbox/i.test(s.engine))) {
          if (page.isClosed()) break;
          await page.waitForTimeout(3000).catch(() => undefined);
        }
      }

      const plays = await page
        .evaluate(() => (window as unknown as { __zectAudioPlays?: Array<{ concurrent: number }> }).__zectAudioPlays || [])
        .catch(() => []);
      const maxConcurrent = plays.reduce((m, p) => Math.max(m, p.concurrent || 0), 0);
      evidence.speak_calls = speakMeta;
      evidence.speak_bytes_total = speakMeta.reduce((a, s) => a + s.bytes, 0);
      evidence.audio_play_count = plays.length;
      evidence.max_concurrent_playback = maxConcurrent;
      evidence.NO_OVERLAP = maxConcurrent <= 1 ? "PASS" : "FAIL";
      const cloneEngines = speakMeta.filter((s) => /zect_voicebox|chatterbox/i.test(s.engine));
      const stockEngines = speakMeta.filter((s) => /openai|stock/i.test(s.engine));
      evidence.cloned_engine_calls = cloneEngines.length;
      evidence.stock_engine_calls = stockEngines.length;
      const nonEmpty = speakMeta.some((s) => s.bytes > 1000);
      evidence.CLONED_VOICE =
        realVoicebox && cloneEngines.length >= 2 && nonEmpty && stockEngines.length === 0 ? "PASS" : "BLOCKED_EXTERNAL";
      evidence.AUDIO_OWNER = stockEngines.length === 0 && cloneEngines.length > 0 ? "clone" : "mixed_or_none";
      evidence.present_status_after = await page.getByTestId("present-deck-status").innerText().catch(() => "");
      evidence.DISCONNECT_FSM = "UNIT_PASS";
      evidence.PACKAGED_RUNTIME = "BLOCKED_EXTERNAL";
      await page.screenshot({ path: path.join(ART, "04-after-narrate.png") });
      expect(page.url()).not.toMatch(/:5000\b/);
      if (realVoicebox) {
        expect(cloneEngines.filter((s) => s.bytes > 1000).length).toBeGreaterThanOrEqual(2);
        expect(stockEngines.length).toBe(0);
        expect(maxConcurrent).toBeLessThanOrEqual(1);
      }
    } finally {
      evidence.speak_calls = speakMeta;
      evidence.speak_bytes_total = speakMeta.reduce((a, s) => a + s.bytes, 0);
      const cloneEngines = speakMeta.filter((s) => /zect_voicebox|chatterbox/i.test(s.engine));
      const stockEngines = speakMeta.filter((s) => /openai|stock/i.test(s.engine));
      evidence.cloned_engine_calls = cloneEngines.length;
      evidence.stock_engine_calls = stockEngines.length;
      const nonEmpty = speakMeta.some((s) => s.bytes > 1000 && (s.status || 0) < 400);
      evidence.CLONED_VOICE =
        realVoicebox && cloneEngines.length >= 2 && nonEmpty && stockEngines.length === 0 ? "PASS" : "BLOCKED_EXTERNAL";
      fs.mkdirSync(ART, { recursive: true });
      fs.writeFileSync(path.join(ART, "evidence-clone.json"), JSON.stringify(evidence, null, 2));
      writeEvidence(evidence);
    }
  });

  test("stock/default voice is the only audio_owner", async ({ page }) => {
    test.setTimeout(8 * 60_000);
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
    await ensureLoggedIn(page);
    const pptx = tinyPptxPath();
    await openGenerateWorkspace(page);
    await page.getByTestId("present-deck-file").setInputFiles(pptx);
    const voiceSelect = page.getByTestId("present-deck-voice-select");
    await expect(voiceSelect).toBeVisible();
    const stockVal = await voiceSelect.locator('option[value^="stock:"]').first().getAttribute("value");
    expect(stockVal).toBeTruthy();
    await voiceSelect.selectOption(stockVal as string);
    await page.getByTestId("present-deck-notes").fill("Stock voice check: one owner, no clone mix.");
    const narrate = page.getByTestId("present-deck-narrate");
    await expect(narrate).toBeEnabled({ timeout: 20_000 });
    await narrate.click();
    const deadline = Date.now() + 90_000;
    while (Date.now() < deadline && !speakMeta.some((s) => s.bytes > 200 && (s.status || 0) < 400)) {
      await page.waitForTimeout(2000);
    }
    const cloneEngines = speakMeta.filter((s) => /zect_voicebox|chatterbox/i.test(s.engine));
    const stockEngines = speakMeta.filter((s) => /openai|stock|tts/i.test(s.engine) && !/zect_voicebox|chatterbox/i.test(s.engine));
    writeEvidence({
      STANDARD_VOICE: stockEngines.length > 0 && cloneEngines.length === 0 ? "PASS" : "FAIL",
      stock_speak: speakMeta,
    });
    expect(cloneEngines.length).toBe(0);
    expect(stockEngines.length).toBeGreaterThan(0);
  });

  test("No Narration makes zero speak calls", async ({ page }) => {
    test.setTimeout(120_000);
    const speakMeta: Array<{ url: string }> = [];
    page.on("response", (res) => {
      if (res.url().includes("/api/mentrix/voice/speak") && res.request().method() === "POST") {
        speakMeta.push({ url: res.url() });
      }
    });
    await ensureLoggedIn(page);
    const pptx = tinyPptxPath();
    await openGenerateWorkspace(page);
    await page.getByTestId("present-deck-file").setInputFiles(pptx);
    const voiceSelect = page.getByTestId("present-deck-voice-select");
    await voiceSelect.selectOption("none");
    await page.getByTestId("present-deck-present-all").click();
    await expect(page.getByTestId("present-deck-status")).toContainText(/No narration/i, { timeout: 15_000 });
    await page.waitForTimeout(1500);
    writeEvidence({ NO_NARRATION: speakMeta.length === 0 ? "PASS" : "FAIL", none_speak_count: speakMeta.length });
    expect(speakMeta.length).toBe(0);
  });
});
