import { test, expect } from "@playwright/test";

const GREEN_GATES = {
  plan_confirmed: true,
  lint_ok: true,
  sandbox_ready: true,
  review_ok: true,
  incomplete_ok: true,
  grounding_ok: true,
  contract_ok: true,
  acceptance_ok: true,
  api_eval_ok: true,
  sast_ok: true,
  sast_checked: true,
};

function mockRun(overrides: Record<string, unknown> = {}) {
  return {
    id: 9001,
    goal: "ZOAS mocked delivery bugfix",
    mode: "bugfix",
    status: "awaiting_plan_confirm",
    next_step: "confirm_plan",
    current_agent: "planner",
    project_key: "zinnia-zoas",
    workspace: "C:\\Users\\karuppk\\zect-workspaces\\zinnia\\zoas",
    approved_at: null,
    pr_url: null,
    events: [
      { agent: "scout", phase: "lattice", message: "Lattice context pack ready", next_step: "plan" },
      { agent: "planner", phase: "plan", message: "Grounded plan ready for confirm", next_step: "confirm_plan" },
    ],
    gates: { plan_confirmed: false, grounding_ok: true },
    result: {
      plan: {
        summary: "Fix ZOAS flaky auth retry and add regression coverage.",
        steps: [
          { title: "Reproduce auth retry flake", action: "inspect" },
          { title: "Patch retry backoff", action: "edit" },
          { title: "Add unit test", action: "test" },
        ],
      },
      gates: { plan_confirmed: false, grounding_ok: true },
    },
    ...overrides,
  };
}

async function installMentrixMocks(page: import("@playwright/test").Page) {
  let run = mockRun();

  await page.route("**/api/mentrix/agents", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        wake_phrases: ["Hey Mentrix"],
        agents: ["scout", "planner", "builder", "reviewer"],
      }),
    });
  });

  await page.route("**/api/mentrix/runs?**", async (route) => {
    if (route.request().method() !== "GET") {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([run]),
    });
  });

  await page.route(/\/api\/mentrix\/runs\/?$/, async (route) => {
    if (route.request().method() !== "POST") {
      await route.continue();
      return;
    }
    const body = (route.request().postDataJSON() as {
      project_key?: string;
      workspace?: string;
      goal?: string;
      mode?: string;
    }) || {};
    if (!String(body.project_key || "").trim() || !String(body.workspace || "").trim()) {
      await route.fulfill({
        status: 400,
        contentType: "application/json",
        body: JSON.stringify({
          detail: "Context pack required: workspace path and Lattice project key",
        }),
      });
      return;
    }
    run = mockRun({
      goal: body.goal || run.goal,
      mode: body.mode || "bugfix",
      project_key: body.project_key,
      workspace: body.workspace,
      status: "awaiting_plan_confirm",
      approved_at: null,
      pr_url: null,
    });
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(run),
    });
  });

  await page.route("**/api/mentrix/runs/*/confirm-plan", async (route) => {
    run = {
      ...run,
      status: "awaiting_approval",
      next_step: "approve",
      current_agent: "reviewer",
      gates: { ...GREEN_GATES },
      result: {
        ...run.result,
        plan: {
          ...(run.result as { plan?: Record<string, unknown> })?.plan,
          summary: "Confirmed ZOAS plan",
        },
        gates: { ...GREEN_GATES },
        ultra_review: { summary: "No blocking findings", score: 92 },
      },
      events: [
        ...(run.events as unknown[]),
        { agent: "builder", phase: "build", message: "Build complete", next_step: "gates" },
        { agent: "reviewer", phase: "review", message: "Ultra Review passed", next_step: "approve" },
      ],
    };
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(run),
    });
  });

  await page.route("**/api/mentrix/runs/*/approve", async (route) => {
    run = {
      ...run,
      status: "approved",
      approved_at: new Date().toISOString(),
      next_step: "create_pr",
      gates: { ...GREEN_GATES },
    };
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(run),
    });
  });

  await page.route("**/api/mentrix/runs/*/create-pr", async (route) => {
    run = {
      ...run,
      status: "pr_created",
      pr_url: "https://github.com/zinnia/zoas/pull/4242",
      next_step: "done",
      gates: { ...GREEN_GATES },
      result: {
        ...(run.result as object),
        pr_url: "https://github.com/zinnia/zoas/pull/4242",
        gates: { ...GREEN_GATES },
      },
    };
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(run),
    });
  });

  await page.route(/\/api\/mentrix\/runs\/\d+$/, async (route) => {
    if (route.request().method() !== "GET") {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(run),
    });
  });

  await page.route("**/api/code-review/sast-status**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ok: true,
        required: true,
        pending: false,
        note: "Semgrep check green (mocked)",
        matched: [
          {
            id: 1,
            name: "Semgrep",
            status: "completed",
            conclusion: "success",
            app: "semgrep",
            html_url: "https://github.com/zinnia/zoas/runs/1",
          },
        ],
      }),
    });
  });

  return {
    getRun: () => run,
  };
}

test.describe("ZOAS Mentrix full delivery (mocked)", () => {
  test("Engage → Confirm plan → Approve → Create PR → Ultra Review SAST", async ({ page }) => {
    await installMentrixMocks(page);

    await page.goto("/mentrix");
    await expect(page.getByTestId("mentrix-page")).toBeVisible({ timeout: 30_000 });

    await page.getByTestId("mentrix-mode").selectOption("bugfix");
    await page.getByTestId("mentrix-project-key").fill("zinnia-zoas");
    await page
      .getByTestId("mentrix-workspace")
      .fill("C:\\Users\\karuppk\\zect-workspaces\\zinnia\\zoas");
    await page.getByTestId("mentrix-goal").fill("Fix ZOAS auth retry flake with regression test");
    await page.getByTestId("mentrix-engage").click();

    await expect(page.getByTestId("mentrix-run-status")).toContainText(/awaiting_plan_confirm/i, {
      timeout: 15_000,
    });
    await expect(page.getByTestId("mentrix-plan-confirm")).toBeVisible();
    await expect(page.getByTestId("mentrix-plan-summary")).not.toHaveValue("");

    await page.getByTestId("mentrix-confirm-plan").click();
    await expect(page.getByTestId("mentrix-run-status")).toContainText(/awaiting_approval/i, {
      timeout: 15_000,
    });
    await expect(page.getByTestId("mentrix-gates")).toContainText(/plan_confirmed: true/);

    await expect(page.getByTestId("mentrix-approve")).toBeEnabled();
    await page.getByTestId("mentrix-approve").click();
    await expect(page.getByTestId("mentrix-run-status")).toContainText(/approved/i, {
      timeout: 15_000,
    });

    await expect(page.getByTestId("mentrix-create-pr")).toBeEnabled();
    await page.getByTestId("mentrix-create-pr").click();
    await expect(page.getByTestId("mentrix-gates")).toContainText(/PR:/i, { timeout: 15_000 });
    await expect(page.getByTestId("mentrix-gates")).toContainText(/zoas\/pull\/4242/);

    await page.goto("/code-review");
    await expect(page.getByTestId("sast-panel")).toBeVisible({ timeout: 30_000 });
    await page.getByPlaceholder("KarthikKaruppasamy880").fill("zinnia");
    await page.getByPlaceholder("ZECT").fill("zoas");
    await page.getByTestId("sast-refresh").click();
    await expect(page.getByTestId("sast-panel")).toContainText(/SAST ok|success|Semgrep/i, {
      timeout: 10_000,
    });
  });

  test("Engage without context pack shows mentrix-error", async ({ page }) => {
    await installMentrixMocks(page);

    await page.goto("/mentrix");
    await expect(page.getByTestId("mentrix-page")).toBeVisible({ timeout: 30_000 });
    await page.getByTestId("mentrix-mode").selectOption("bugfix");
    await page.getByTestId("mentrix-project-key").fill("");
    await page.getByTestId("mentrix-workspace").fill("");
    await page.getByTestId("mentrix-goal").fill("Should fail context pack preflight");
    await page.getByTestId("mentrix-engage").click();

    await expect(page.getByTestId("mentrix-error")).toContainText(/Context pack|workspace|Lattice/i, {
      timeout: 15_000,
    });
  });

  test("Ask → Plan → Mentrix handoff (mocked LLM)", async ({ page }) => {
    await page.route("**/api/context/load", async (route) => {
      const body = (route.request().postDataJSON() as { page?: string }) || {};
      const entries =
        body.page === "ask"
          ? [{ key: "blueprint_prompt", value: "ZOAS lattice blueprint context", page: "ask" }]
          : body.page === "plan"
            ? [
                {
                  key: "project_description",
                  value: "Implement ZOAS auth retry fix from Ask",
                  page: "plan",
                },
                { key: "repo_context", value: "ZOAS lattice blueprint context", page: "plan" },
              ]
            : [];
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ page: body.page || "ask", entries, total_tokens_estimated: 40 }),
      });
    });
    await page.route("**/api/context/save", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ saved: true }),
      });
    });
    await page.route("**/api/llm/ask", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          answer: "Priority: fix ZOAS auth retry backoff and add a regression test.",
          tokens_used: 64,
          model: "gpt-4o-mini",
        }),
      });
    });
    await page.route("**/api/llm/plan", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          plan: "# ZOAS plan\n\n1. Reproduce\n2. Patch backoff\n3. Test",
          phases: ["Reproduce", "Patch backoff", "Add regression test"],
          tokens_used: 80,
          model: "gpt-4o-mini",
        }),
      });
    });
    await installMentrixMocks(page);

    await page.goto("/ask");
    await expect(page.getByTestId("ask-input")).toBeVisible({ timeout: 30_000 });
    await page.getByTestId("ask-input").fill("What should we fix first in ZOAS auth?");
    await page.getByTestId("ask-send").click();
    await expect(page.getByTestId("ask-send-to-plan")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("ask-send-to-plan").click();

    await expect(page).toHaveURL(/\/plan/, { timeout: 15_000 });
    await expect(page.getByTestId("plan-description")).not.toHaveValue("", { timeout: 10_000 });
    await page.getByTestId("plan-generate").click();
    await expect(page.getByTestId("plan-open-mentrix")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("plan-open-mentrix").click();

    await expect(page).toHaveURL(/\/mentrix/, { timeout: 15_000 });
    await expect(page.getByTestId("mentrix-page")).toBeVisible();
    await expect(page.getByTestId("mentrix-goal")).not.toHaveValue("", { timeout: 10_000 });
  });
});
