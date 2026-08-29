/**
 * Tranche G: accessibility + product UX sweep (headed).
 * Skip ≠ PASS for Electron / live Presenton / Voicebox / Jira / Camunda.
 */
import { test, expect, type Page } from "@playwright/test";
import { gotoAuthed } from "./helpers/login";

const SURFACES: { path: string; testId: string; nav: string; heading?: RegExp; viaNav?: boolean }[] = [
  { path: "/mentrix-home", testId: "mentrix-companion-page", nav: "Mentrix Companion", heading: /Mentrix/i },
  { path: "/present", testId: "zect-present-page", nav: "Present", heading: /Presentations/ },
  { path: "/workspace", testId: "developer-workspace", nav: "Developer" },
  // Agent Workspace is hidden from primary nav (superseded by Developer
  // cockpit) — route stays live, reached directly rather than via sidebar.
  { path: "/ask", testId: "agent-workspace", nav: "Agent Workspace", heading: /Agent Workspace/, viaNav: false },
  { path: "/projects", testId: "projects-page", nav: "Projects", heading: /^Projects$/ },
  { path: "/work-items", testId: "work-items-page", nav: "Work Items" },
  { path: "/fabric", testId: "mentrix-fabric-page", nav: "Processes" },
  { path: "/project-intelligence", testId: "project-intelligence-page", nav: "Project Intelligence", heading: /Project Intelligence/ },
  { path: "/lattice", testId: "lattice-page", nav: "Lattice", heading: /^Lattice$/ },
  { path: "/knowledge-base", testId: "knowledge-base-page", nav: "Knowledge Base", heading: /Knowledge Base/ },
  { path: "/learning", testId: "zect-learning-page", nav: "ZECT Learning" },
  { path: "/skills-engine", testId: "skills-engine-page", nav: "Skills Engine", heading: /Skills Engine/ },
  { path: "/playbooks", testId: "playbooks-page", nav: "Playbooks", heading: /Playbooks/ },
];

async function horizontalOverflow(page: Page): Promise<number> {
  return page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
}

async function openSurface(page: Page, surface: (typeof SURFACES)[number]) {
  if (surface.viaNav === false) {
    await page.goto(surface.path, { waitUntil: "domcontentloaded" });
  } else {
    await page.getByTestId("app-sidebar").getByRole("link", { name: surface.nav, exact: true }).click();
  }
  await expect(page.getByTestId(surface.testId)).toBeVisible({ timeout: 30_000 });
  if (surface.path === "/fabric") {
    await expect(page.getByTestId("process-sample-card")).toBeVisible();
  }
  if (surface.heading) {
    await expect(page.getByRole("heading", { name: surface.heading }).first()).toBeVisible();
  }
  const overflow = await horizontalOverflow(page);
  expect(overflow, `${surface.path} overflow`).toBeLessThanOrEqual(24);
}

test.describe("UX accessibility production 1280x720", () => {
  test.use({ viewport: { width: 1280, height: 720 } });
  test.setTimeout(180_000);

  test("skip link, named nav, surfaces, collapse, Escape dropdown", async ({ page }) => {
    await gotoAuthed(page, "/projects", "projects-page");
    const skip = page.getByTestId("skip-to-main");
    await skip.focus();
    await expect(skip).toBeFocused();
    await skip.press("Enter");
    await expect(page.getByTestId("zect-main")).toBeFocused();

    const nav = page.getByTestId("app-sidebar");
    await expect(nav).toBeVisible();
    await expect(nav.getByRole("link", { name: "Mentrix Companion" })).toBeVisible();

    for (const surface of SURFACES) {
      await openSurface(page, surface);
    }

    await openSurface(page, SURFACES.find((s) => s.path === "/projects")!);
    await page.keyboard.press("Control+b");
    await expect(nav.getByText("Mentrix Companion", { exact: true })).toBeHidden({ timeout: 8_000 });
    await page.keyboard.press("Control+b");
    await expect(nav.getByText("Mentrix Companion", { exact: true })).toBeVisible({ timeout: 8_000 });

    const projectBtn = page.getByTestId("select-project-button");
    if (await projectBtn.isVisible().catch(() => false)) {
      await projectBtn.click();
      await expect(page.getByTestId("select-project-dropdown")).toBeVisible();
      await page.keyboard.press("Escape");
      await expect(page.getByTestId("select-project-dropdown")).toHaveCount(0);
    }
  });

  test("Companion tabs keyboard and Present nav names", async ({ page }) => {
    await gotoAuthed(page, "/mentrix-home", "mentrix-companion-page");
    const chat = page.getByTestId("mentrix-mode-chat");
    await chat.focus();
    await page.keyboard.press("ArrowRight");
    await expect(page.getByTestId("mentrix-mode-incident")).toHaveAttribute("aria-selected", "true");
    await expect(page.getByTestId("mentrix-mode-incident")).toBeFocused();
    await page.keyboard.press("Home");
    await expect(chat).toHaveAttribute("aria-selected", "true");
    await expect(chat).toBeFocused();

    await gotoAuthed(page, "/present", "zect-present-page");
    await expect(page.getByTestId("present-nav-dashboard")).toBeVisible();
    await page.getByTestId("present-nav-create").click();
    await expect(page).toHaveURL(/\/present\/create/);
  });
});

test.describe("UX accessibility production 1920x1080", () => {
  test.use({ viewport: { width: 1920, height: 1080 } });
  test.setTimeout(120_000);

  test("production surfaces fit without overlap at 1920", async ({ page }) => {
    await gotoAuthed(page, "/projects", "projects-page");
    for (const surface of SURFACES) {
      await openSurface(page, surface);
    }
    await openSurface(page, SURFACES.find((s) => s.path === "/workspace")!);
    const handle = page.getByTestId("workspace-split-h-handle");
    if (await handle.isVisible().catch(() => false)) {
      await handle.focus();
      await page.keyboard.press("ArrowRight");
      await page.keyboard.press("Home");
    }
  });
});
