import { test, expect } from "@playwright/test";

test.describe("Present Deck (PPTX + Zoom)", () => {
  test("Present Deck panel visible on Companion Voice; browser shows Electron hint", async ({
    page,
  }) => {
    await page.goto("/mentrix-home?voice=1");
    await expect(page.getByTestId("mentrix-companion-page")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("mentrix-voice-section")).toBeVisible();
    await expect(page.getByTestId("present-deck-panel")).toBeVisible();
    await expect(page.getByTestId("present-deck-path")).toBeVisible();
    await expect(page.getByTestId("present-deck-open-pptx")).toBeVisible();
    await expect(page.getByTestId("present-deck-open-zoom")).toBeVisible();
    await expect(page.getByTestId("present-deck-narrate")).toBeVisible();

    await page.getByTestId("present-deck-path").fill("C:\\Users\\test\\Documents\\demo.pptx");
    await page.getByTestId("present-deck-open-pptx").click();
    await expect(page.getByTestId("present-deck-status")).toContainText(/Electron/i, {
      timeout: 5_000,
    });
  });

  test("Present / Narrate hint mentions Board artifacts + Chatterbox", async ({ page }) => {
    await page.goto("/mentrix-home");
    await expect(page.getByTestId("mentrix-companion-page")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("mentrix-present-narrate")).toBeVisible();
    await expect(page.getByTestId("mentrix-present-hint")).toContainText(/Board artifacts|Chatterbox/i);
  });

  test("Mocked Electron bridge records open_presentation action", async ({ page }) => {
    await page.addInitScript(() => {
      const store: { action: string; args: Record<string, unknown> }[] = [];
      (window as unknown as { __presentDeckCalls?: typeof store }).__presentDeckCalls = store;
      (window as unknown as { zectDesktop?: unknown }).zectDesktop = {
        isDesktopApp: true,
        mentrix: {
          setComputerMode: async () => ({ ok: true }),
          computer: async (action: string, args: Record<string, unknown> = {}) => {
            store.push({ action, args });
            return { ok: true, desktop: action };
          },
        },
      };
    });

    await page.goto("/mentrix-home?voice=1");
    await expect(page.getByTestId("present-deck-panel")).toBeVisible({ timeout: 30_000 });
    await page.getByTestId("present-deck-path").fill("C:\\Users\\test\\Documents\\demo.pptx");
    await page.getByTestId("present-deck-open-pptx").click();
    await expect(page.getByTestId("present-deck-status")).toContainText(/Opened presentation|Share/i, {
      timeout: 5_000,
    });

    const recorded = await page.evaluate(() => {
      return (window as unknown as { __presentDeckCalls?: { action: string }[] }).__presentDeckCalls || [];
    });
    expect(recorded.some((c) => c.action === "open_presentation")).toBeTruthy();
  });
});
