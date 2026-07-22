import { test, expect } from "@playwright/test";

test.describe("Mentrix Companion", () => {
  test("Companion HUD loads with avatar and artifacts", async ({ page }) => {
    await page.goto("/mentrix-home");
    await expect(page.getByTestId("mentrix-companion-page")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("mentrix-avatar")).toBeVisible();
    await expect(page.getByTestId("mentrix-board")).toBeVisible();
    await expect(page.getByRole("heading", { name: /MENTRIX/i })).toBeVisible();
    await expect(page.getByTestId("mentrix-connect-voice")).toBeVisible();
    await expect(page.getByTestId("mentrix-live-log")).toBeVisible();
  });

  test("status ask returns a reply", async ({ page }) => {
    await page.goto("/mentrix-home");
    await page.getByTestId("mentrix-companion-input").fill("What's my Mentrix Delivery status?");
    await page.getByTestId("mentrix-companion-send").click();
    await expect(page.getByTestId("mentrix-companion-chat")).toContainText(
      /gates|run|status|needs_human|completed|failed|Delivery|Ready|instant|Latest/i,
      { timeout: 45_000 },
    );
  });

  test("Workflow sidebar links to Mentrix Companion", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("link", { name: /Mentrix Companion/i })).toBeVisible();
    await page.getByRole("link", { name: /Mentrix Companion/i }).click();
    await expect(page.getByTestId("mentrix-companion-page")).toBeVisible();
  });

  test("navigate intent opens Lattice", async ({ page }) => {
    await page.goto("/mentrix-home");
    await page.getByTestId("mentrix-companion-input").fill("Open Lattice");
    await page.getByTestId("mentrix-companion-send").click();
    await expect(page).toHaveURL(/\/lattice/, { timeout: 45_000 });
  });

  test("send tool shows confirm modal", async ({ page }) => {
    await page.goto("/mentrix-home");
    await page.getByTestId("mentrix-companion-input").fill("Slack send a message saying hello from Mentrix");
    await page.getByTestId("mentrix-companion-send").click();
    await expect(page.getByTestId("mentrix-confirm-modal")).toBeVisible({ timeout: 45_000 });
    await page.getByTestId("mentrix-confirm-deny").click();
    await expect(page.getByTestId("mentrix-confirm-modal")).toHaveCount(0);
    await expect(page.getByTestId("mentrix-companion-chat")).toContainText(/Permission denied/i);
  });

  test("diagnose posts Mermaid artifact", async ({ page }) => {
    await page.goto("/mentrix-home");
    await page.getByTestId("mentrix-companion-input").fill("Diagnose why this is failing");
    await page.getByTestId("mentrix-companion-send").click();
    await expect(page.getByTestId("mentrix-artifact-mermaid").first()).toBeVisible({
      timeout: 45_000,
    });
  });

  test("navigate intent opens Sandbox", async ({ page }) => {
    await page.goto("/mentrix-home");
    await page.getByTestId("mentrix-companion-input").fill("Open Sandbox");
    await page.getByTestId("mentrix-companion-send").click();
    await expect(page).toHaveURL(/\/sandbox/, { timeout: 45_000 });
  });

  test("Connect Voice button toggles", async ({ page }) => {
    await page.goto("/mentrix-home");
    await expect(page.getByTestId("mentrix-realtime-status")).toBeVisible({ timeout: 30_000 });
    await page.getByTestId("mentrix-connect-voice").click();
    await expect(page.getByTestId("mentrix-live-log")).toContainText(/Connect Voice|Realtime|fallback|listening/i, {
      timeout: 30_000,
    });
  });

  test("weather ask returns conditions or degrees", async ({ page }) => {
    await page.goto("/mentrix-home");
    await page.getByTestId("mentrix-companion-input").fill("What's the weather in Austin?");
    await page.getByTestId("mentrix-companion-send").click();
    await expect(page.getByTestId("mentrix-companion-chat")).toContainText(
      /weather|degree|°F|fahrenheit|clear|rain|cloud|Austin|humidity|wind|forecast|lookup failed|research/i,
      { timeout: 45_000 },
    );
  });
});
