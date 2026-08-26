import { test, expect } from "@playwright/test";

const GOLDEN_PROMPT =
  "AI Agentic architectures: graph-based agents, tool loops, and KV-cache efficiency for enterprise inference.";

test.describe("Present golden V2 — 3 slides", () => {
  test("create flow requests exactly 3 slides via API contract", async ({ page, request }) => {
    test.skip(!process.env.PRESENT_GOLDEN_E2E, "Set PRESENT_GOLDEN_E2E=1 with backend running");

    const apiBase = process.env.PRESENT_API_BASE || "http://127.0.0.1:8000";
    const token = process.env.PRESENT_E2E_TOKEN || "";
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers.Authorization = `Bearer ${token}`;

    const gen = await request.post(`${apiBase}/api/mentrix/present/generate`, {
      headers,
      data: {
        content: GOLDEN_PROMPT,
        n_slides: 3,
        template: "zinnia-executive-v1",
        ui_template_choice: "zinnia-executive-v1",
        filename: "golden-v2-e2e.pptx",
        fast_basic: true,
      },
      timeout: 300_000,
    });
    expect(gen.ok()).toBeTruthy();
    const body = await gen.json();
    expect(body.requested_slide_count ?? body.n_slides).toBe(3);
    expect(body.path).toBeTruthy();

    await page.goto("/present/create");
    await expect(page.getByTestId("present-deck-n-slides")).toBeVisible();
  });
});
