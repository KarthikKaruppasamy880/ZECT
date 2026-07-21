import { test, expect } from "@playwright/test";

test.describe("Mentrix quality gates", () => {
  test("upgrade run exposes anti-hallucination gates in UI", async ({ page }) => {
    await page.goto("/mentrix");
    await expect(page.getByTestId("mentrix-page")).toBeVisible();
    await page.getByTestId("mentrix-mode").selectOption("upgrade");
    await page
      .getByTestId("mentrix-goal")
      .fill("Quality gates smoke: port helper module python to typescript");
    await page.getByTestId("mentrix-engage").click();

    await expect(page.getByTestId("mentrix-live-status")).toBeVisible();
    await expect(page.getByTestId("mentrix-run-status")).toContainText(
      /completed|awaiting|needs_human|running|approved/i,
      { timeout: 90_000 }
    );
    await expect(page.getByTestId("mentrix-gates")).toContainText(/grounding_ok|contract_ok|acceptance_ok|incomplete_ok/i);
  });

  test("create-pr stays disabled until approve", async ({ page }) => {
    await page.goto("/mentrix");
    await page.getByTestId("mentrix-mode").selectOption("deliver");
    await page.getByTestId("mentrix-goal").fill("Small deliverable for PR gate check");
    await page.getByTestId("mentrix-engage").click();
    await expect(page.getByTestId("mentrix-run-status")).toContainText(
      /awaiting_approval|needs_human|completed|approved/i,
      { timeout: 60_000 }
    );
    await expect(page.getByTestId("mentrix-create-pr")).toBeDisabled();
  });
});
