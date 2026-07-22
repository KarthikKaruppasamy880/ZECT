import { test, expect } from "@playwright/test";

test.describe("Mentrix Companion", () => {
  test("Companion Home loads with avatar and board", async ({ page }) => {
    await page.goto("/mentrix-home");
    await expect(page.getByTestId("mentrix-companion-page")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("mentrix-avatar")).toBeVisible();
    await expect(page.getByTestId("mentrix-board")).toBeVisible();
    await expect(page.getByRole("heading", { name: /Mentrix Companion/i })).toBeVisible();
  });

  test("status ask returns a reply", async ({ page }) => {
    await page.goto("/mentrix-home");
    await page.getByTestId("mentrix-companion-input").fill("What's my Mentrix Delivery status?");
    await page.getByTestId("mentrix-companion-send").click();
    await expect(page.getByTestId("mentrix-companion-chat")).toContainText(
      /gates|run|status|needs_human|completed|failed|Ready|offline|no recent/i,
      { timeout: 45_000 },
    );
    await expect(page.getByTestId("mentrix-companion-chat")).not.toContainText(/^Not Found$/);
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
});
