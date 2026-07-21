import { test, expect } from "@playwright/test";

test.describe("Mentrix approve → PR", () => {
  test("create-pr blocked without approve; works after approve", async ({ page, request }) => {
    await page.goto("/mentrix");
    await expect(page.getByTestId("mentrix-page")).toBeVisible();

    await page.getByTestId("mentrix-goal").fill("Deliver a small docs tweak with gates");
    await page.getByTestId("mentrix-mode").selectOption("deliver");
    await page.getByTestId("mentrix-engage").click();

    await expect(page.getByTestId("mentrix-run-status")).toContainText(
      /awaiting_approval|needs_human|completed|approved/i,
      { timeout: 60_000 }
    );

    // Create PR should be disabled until approve
    const createBtn = page.getByTestId("mentrix-create-pr");
    await expect(createBtn).toBeDisabled();

    // If needs_human, acknowledge to allow approve
    const statusText = await page.getByTestId("mentrix-run-status").innerText();
    if (/needs_human/i.test(statusText)) {
      await page.getByTestId("mentrix-acknowledge").check();
    }

    const approveBtn = page.getByTestId("mentrix-approve");
    if (await approveBtn.isEnabled()) {
      await approveBtn.click();
      await expect(page.getByTestId("mentrix-run-status")).toContainText(/approved/i, {
        timeout: 20_000,
      });
      await expect(createBtn).toBeEnabled();
      await createBtn.click();
      await expect(page.getByTestId("mentrix-gates")).toContainText(/PR:/i, { timeout: 20_000 });
    } else {
      // Gates still red even with ack — verify API rejects create-pr without approve
      const token = await page.evaluate(() => localStorage.getItem("zect_token"));
      const api = process.env.VITE_API_URL || "http://localhost:8000";
      const runs = await request.get(`${api}/api/mentrix/runs?limit=1`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      expect(runs.ok()).toBeTruthy();
      const list = await runs.json();
      const id = list[0]?.id;
      expect(id).toBeTruthy();
      const pr = await request.post(`${api}/api/mentrix/runs/${id}/create-pr`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: { dry_run: true },
      });
      expect(pr.status()).toBe(403);
    }
  });
});
