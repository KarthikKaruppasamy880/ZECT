import { test, expect } from "@playwright/test";

test.describe("Mentrix voice clone", () => {
  test("Clone voice panel on Mentrix Delivery", async ({ page }) => {
    await page.goto("/mentrix");
    await expect(page.getByTestId("mentrix-page")).toBeVisible({ timeout: 30_000 });
    const expand = page.getByTestId("clone-voice-expand");
    if (await expand.isVisible().catch(() => false)) {
      await expand.click();
    }
    await expect(page.getByTestId("clone-voice-panel")).toBeVisible({ timeout: 10_000 });
    // If a voice is already active, reset so the clone form is available
    const reset = page.getByTestId("clone-voice-reset");
    if (await reset.isVisible().catch(() => false)) {
      await reset.click();
      await expect(page.getByTestId("clone-voice-name")).toBeVisible({ timeout: 10_000 });
    } else {
      await expect(page.getByTestId("clone-voice-name")).toBeVisible();
      await expect(page.getByTestId("clone-voice-transcript")).toBeVisible();
    }
  });

  test("Clone voice panel on Mentrix Companion", async ({ page }) => {
    await page.goto("/mentrix-home");
    await expect(page.getByTestId("mentrix-companion-page")).toBeVisible({ timeout: 30_000 });
    const expand = page.getByTestId("clone-voice-expand");
    if (await expand.isVisible().catch(() => false)) {
      await expand.click();
    }
    await expect(page.getByTestId("clone-voice-panel")).toBeVisible({ timeout: 10_000 });
  });

  test("Voice clone Labs sidebar link opens Mentrix Delivery", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: /Voice Cloning/i }).click();
    await expect(page).toHaveURL(/\/mentrix/, { timeout: 15_000 });
  });

  test("Clone submit shows Voicebox error when offline", async ({ page }) => {
    await page.route("**/api/mentrix/voice/clone", async (route) => {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Voicebox isn't reachable" }),
      });
    });

    await page.goto("/mentrix");
    await expect(page.getByTestId("mentrix-page")).toBeVisible({ timeout: 30_000 });

    const expand = page.getByTestId("clone-voice-expand");
    if (await expand.isVisible().catch(() => false)) {
      await expand.click();
    }
    await expect(page.getByTestId("clone-voice-panel")).toBeVisible({ timeout: 10_000 });

    const reset = page.getByTestId("clone-voice-reset");
    if (await reset.isVisible().catch(() => false)) {
      await reset.click();
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
    await expect(page.getByTestId("clone-voice-error")).toContainText(/Voicebox|503|reachable/i, {
      timeout: 10_000,
    });
  });
});
