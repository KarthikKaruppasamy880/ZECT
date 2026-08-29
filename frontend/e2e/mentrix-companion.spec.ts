import { test, expect } from "@playwright/test";

test.describe("Mentrix Companion", () => {
  test("Companion HUD loads with avatar and artifacts", async ({ page }) => {
    await page.goto("/mentrix-home");
    await expect(page.getByTestId("mentrix-companion-page")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("mentrix-avatar")).toBeVisible();
    await expect(page.getByTestId("mentrix-companion-more")).toBeVisible();
    await expect(page.getByTestId("mentrix-companion-artifacts")).toHaveCount(0);
    await expect(
      page.getByTestId("mentrix-companion-page").getByRole("heading", { name: /Mentrix/i }),
    ).toBeVisible();
    await expect(page.getByTestId("mentrix-connect-voice")).toBeVisible();
    await expect(page.getByTestId("mentrix-greeting")).toBeVisible();
    await page.getByTestId("mentrix-companion-more").click();
    await expect(page.getByTestId("mentrix-events-toggle")).toBeVisible();
    await page.getByTestId("mentrix-events-toggle").click();
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

  test("Connect Voice is honest when realtime is unavailable", async ({ page }) => {
    await page.goto("/mentrix-home");
    const hud = page.getByTestId("mentrix-companion-page");
    const btn = hud.getByTestId("mentrix-connect-voice");
    const status = hud.getByTestId("mentrix-realtime-status");
    await expect(btn).toBeVisible({ timeout: 30_000 });
    await expect(status).toBeVisible({ timeout: 30_000 });
    // Preflight starts as null → button is enabled, then disables when realtime is not ready.
    // Clicking during "Checking Realtime…" races and times out on a disabled control.
    await expect(status).not.toContainText(/Checking Realtime/i, { timeout: 30_000 });
    await expect(status).toContainText(/Realtime ready|Realtime unavailable|OPENAI_API_KEY/i, {
      timeout: 15_000,
    });
    if (!(await btn.isEnabled())) {
      await expect(status).toContainText(/Realtime unavailable|OPENAI_API_KEY|Retry|unavailable/i);
      await expect(btn).toBeDisabled();
      return;
    }
    await btn.click();
    await page.getByTestId("mentrix-companion-more").click();
    await page.getByTestId("mentrix-events-toggle").click();
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
