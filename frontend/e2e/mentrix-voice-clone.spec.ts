import { test, expect } from "@playwright/test";

test.describe("Mentrix ZECT Voicebox voice", () => {
  test("Settings hosts clone panel; Companion Voice tab has speak controls", async ({ page }) => {
    await page.goto("/mentrix-home");
    await expect(page.getByTestId("mentrix-companion-page")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("mentrix-companion-modes")).toBeVisible();
    await page.getByTestId("mentrix-mode-voice").click();
    await expect(page).toHaveURL(/voice=1/);
    await expect(page.getByTestId("mentrix-voice-section")).toBeVisible();

    await page.goto("/settings");
    await expect(page.getByTestId("clone-voice-panel")).toBeVisible({ timeout: 15_000 });
  });

  test("Settings Voice section expands ZECT Voicebox form", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.getByTestId("clone-voice-panel")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("clone-voice-record")).toBeVisible();
    await expect(page.getByTestId("clone-voice-engine-status")).toContainText(/ZECT Voicebox|Voicebox|online|offline/i);
  });

  test("Labs no longer lists Voice Cloning; Incident shortcut remains", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("link", { name: /Voice Cloning/i })).toHaveCount(0);
    await page.getByRole("link", { name: /Incident Runbook/i }).click();
    await expect(page).toHaveURL(/\/mentrix-home\?incident=1/, { timeout: 15_000 });
    await expect(page.getByTestId("mentrix-incident-section")).toBeVisible({ timeout: 15_000 });
  });

  test("Delivery page does not host voice cloning", async ({ page }) => {
    await page.goto("/mentrix");
    await expect(page.getByTestId("mentrix-page")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("clone-voice-panel")).toHaveCount(0);
    await expect(page.getByTestId("clone-voice-expand")).toHaveCount(0);
  });

  test("Present / Narrate control visible on Companion", async ({ page }) => {
    await page.goto("/mentrix-home");
    await expect(page.getByTestId("mentrix-companion-page")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("mentrix-present-narrate")).toBeVisible();
  });

  test("Clone submit surfaces API error when clone fails", async ({ page }) => {
    await page.route("**/api/mentrix/voice/clone", async (route) => {
      await route.fulfill({
        status: 502,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Chatterbox generation failed (502)" }),
      });
    });

    await page.goto("/settings");
    await expect(page.getByTestId("clone-voice-panel")).toBeVisible({ timeout: 15_000 });

    const del = page.getByTestId("clone-voice-reset").first();
    if (await del.isVisible().catch(() => false)) {
      await del.click();
    }

    await expect(page.getByTestId("clone-voice-name")).toBeVisible({ timeout: 10_000 });
    await page.getByTestId("clone-voice-name").fill("Test Voice");
    await page.getByTestId("clone-voice-transcript").fill("Hello this is a test sample for cloning.");

    await page.setInputFiles("input[data-testid='clone-voice-file']", {
      name: "sample.wav",
      mimeType: "audio/wav",
      buffer: Buffer.from("RIFFfake"),
    });

    await page.getByTestId("clone-voice-submit").click();
    await expect(page.getByTestId("clone-voice-error")).toContainText(/Voicebox|Chatterbox|502|failed/i, {
      timeout: 10_000,
    });
  });

  test("Engine online unlocks Test speak (127.0.0.1 Voicebox)", async ({ page }) => {
    await page.route("**/api/mentrix/voice/engine-status", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          online: true,
          base_url: "http://127.0.0.1:17493",
          default_voice: null,
          hint: "ZECT Voicebox online — Test speak unlocked.",
        }),
      });
    });

    await page.goto("/settings");
    await expect(page.getByTestId("clone-voice-panel")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("clone-voice-engine-status")).toContainText(/online/i, {
      timeout: 10_000,
    });
    await expect(page.getByTestId("clone-voice-engine-status")).toContainText("127.0.0.1:17493");
    await expect(page.getByTestId("clone-voice-test-speak")).toBeEnabled({ timeout: 5_000 });
  });

  test("Successful clone lists voice and ready note", async ({ page }) => {
    await page.route("**/api/mentrix/voice/clone", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: 1,
          voice_id: "abc123",
          name: "Test Voice",
          provider: "chatterbox",
          is_default: true,
          has_sample: true,
        }),
      });
    });
    await page.route("**/api/mentrix/voice/voices", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: 1,
            voice_id: "abc123",
            name: "Test Voice",
            provider: "chatterbox",
            is_default: true,
            has_sample: true,
          },
        ]),
      });
    });

    await page.goto("/settings");
    await expect(page.getByTestId("clone-voice-panel")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("clone-voice-name").fill("Test Voice");
    await page.getByTestId("clone-voice-transcript").fill("Hello this is a test sample for cloning.");
    await page.setInputFiles("input[data-testid='clone-voice-file']", {
      name: "sample.wav",
      mimeType: "audio/wav",
      buffer: Buffer.from("RIFFfake"),
    });
    await page.getByTestId("clone-voice-submit").click();
    await expect(page.getByTestId("clone-voice-ready")).toContainText(/Present/i, { timeout: 10_000 });
    await expect(page.getByTestId("clone-voice-list")).toBeVisible();
  });
});
