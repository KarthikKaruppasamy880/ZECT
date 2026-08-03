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

    await page.getByTestId("present-deck-open-zoom").click();
    await expect(page.getByTestId("present-deck-status")).toContainText(/Zoom|share|Narrate/i, {
      timeout: 5_000,
    });
    const afterZoom = await page.evaluate(() => {
      return (window as unknown as { __presentDeckCalls?: { action: string }[] }).__presentDeckCalls || [];
    });
    expect(afterZoom.some((c) => c.action === "open_zoom")).toBeTruthy();
  });

  test("Present all slides mocks parse → open → f5 → right sequence", async ({ page }) => {
    // Tiny silent WAV so speakMentrixAwait can play + end quickly
    const silentWav = Buffer.from(
      "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=",
      "base64",
    );
    await page.route("**/api/mentrix/voice/speak", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "audio/wav",
        body: silentWav,
      });
    });

    await page.addInitScript(() => {
      const store: { action: string; args: Record<string, unknown> }[] = [];
      (window as unknown as { __presentDeckCalls?: typeof store }).__presentDeckCalls = store;
      (window as unknown as { zectDesktop?: unknown }).zectDesktop = {
        isDesktopApp: true,
        mentrix: {
          setComputerMode: async () => ({ ok: true }),
          computer: async (action: string, args: Record<string, unknown> = {}) => {
            store.push({ action, args });
            if (action === "parse_presentation_slides") {
              return {
                ok: true,
                count: 2,
                slides: [
                  { index: 0, notes: "Welcome to slide one.", text: "Title One" },
                  { index: 1, notes: "Closing thoughts.", text: "Title Two" },
                ],
              };
            }
            return { ok: true, desktop: action };
          },
        },
      };
    });

    await page.goto("/mentrix-home?voice=1");
    await expect(page.getByTestId("present-deck-present-all")).toBeVisible({ timeout: 30_000 });
    await page.getByTestId("present-deck-path").fill("C:\\Users\\test\\Documents\\demo.pptx");
    await page.getByTestId("present-deck-present-all").click();

    await expect(page.getByTestId("present-deck-status")).toContainText(/Finished presenting|Slide/i, {
      timeout: 30_000,
    });
    await expect(page.getByTestId("present-deck-status")).toContainText(/Finished presenting 2 slides/i, {
      timeout: 30_000,
    });

    const recorded = await page.evaluate(() => {
      return (
        (window as unknown as { __presentDeckCalls?: { action: string; args: Record<string, unknown> }[] })
          .__presentDeckCalls || []
      );
    });
    const actions = recorded.map((c) => c.action);
    expect(actions[0]).toBe("parse_presentation_slides");
    expect(actions).toContain("open_presentation");
    expect(recorded.some((c) => c.action === "powerpoint_key" && c.args?.key === "f5")).toBeTruthy();
    expect(recorded.some((c) => c.action === "powerpoint_key" && c.args?.key === "right")).toBeTruthy();
  });

  test("Generate deck button calls Presenton proxy and fills path", async ({ page }) => {
    await page.route("**/api/mentrix/companion/integrations", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          slack: false,
          jira: false,
          openai: true,
          presenton: true,
          presenton_base_url: "http://127.0.0.1:5000",
        }),
      });
    });
    await page.route("**/api/mentrix/presenton/generate", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ok: true,
          path: "C:\\\\Users\\\\test\\\\Documents\\\\mentrix-deck.pptx",
          bytes: 1024,
        }),
      });
    });

    await page.goto("/mentrix-home?voice=1");
    await expect(page.getByTestId("present-deck-generate")).toBeVisible({ timeout: 30_000 });
    await page.getByTestId("present-deck-prompt").fill("ZOAS status brief for leadership");
    await page.getByTestId("present-deck-generate").click();
    await expect(page.getByTestId("present-deck-path")).toHaveValue(/mentrix-deck\.pptx/i, {
      timeout: 10_000,
    });
  });
});
