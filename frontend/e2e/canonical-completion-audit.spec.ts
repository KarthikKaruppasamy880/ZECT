/**
 * Headed live develop product reconciliation for ZECT_CANONICAL_COMPLETION_AUDIT.
 * Evidence-only — does not assert product completeness.
 */
import { test, expect, type Page, type ConsoleMessage } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const OUT = path.join(ROOT, "..", "artifacts", "canonical-audit-live");

function ensureOut() {
  fs.mkdirSync(OUT, { recursive: true });
}

function loadEnvCreds(): { username: string; password: string } {
  const envPath = path.join(ROOT, "..", "backend", ".env");
  let username =
    process.env.ZECT_USERNAME || process.env.ZECT_E2E_USER || "admin@zect.local";
  let password =
    process.env.ZECT_PASSWORD || process.env.ZECT_E2E_PASSWORD || "zect-dev-local";
  try {
    const raw = fs.readFileSync(envPath, "utf8");
    for (const line of raw.split(/\r?\n/)) {
      const m = line.match(/^(ZECT_USERNAME|ZECT_PASSWORD)=(.*)$/);
      if (!m) continue;
      const v = m[2].replace(/^["']|["']$/g, "");
      if (m[1] === "ZECT_USERNAME") username = v;
      if (m[1] === "ZECT_PASSWORD") password = v;
    }
  } catch {
    /* use defaults */
  }
  return { username, password };
}

async function ensureLoggedIn(page: Page) {
  const { username, password } = loadEnvCreds();
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const login = page.getByTestId("login-username");
  if (await login.isVisible().catch(() => false)) {
    await login.fill(username);
    await page.getByTestId("login-password").fill(password);
    await page.getByTestId("login-submit").click();
    await expect(page.getByTestId("login-submit")).toBeHidden({ timeout: 30_000 });
  }
  const token = await page.evaluate(() => localStorage.getItem("zect_token"));
  expect(token).toBeTruthy();
}

async function shot(page: Page, name: string) {
  ensureOut();
  await page.screenshot({ path: path.join(OUT, `${name}.png`), fullPage: false });
}

async function gotoSoft(page: Page, route: string) {
  await page.goto(route, { waitUntil: "domcontentloaded", timeout: 20000 });
  await page.waitForTimeout(500);
  if (await page.getByTestId("login-username").isVisible().catch(() => false)) {
    await ensureLoggedIn(page);
    await page.goto(route, { waitUntil: "domcontentloaded", timeout: 20000 });
    await page.waitForTimeout(500);
  }
}

test.describe("LIVE develop product reconciliation", () => {
  test.setTimeout(300_000);

  test("surface crawl + companion sidebar + present/learning", async ({ page }) => {
    ensureOut();
    const consoleErrors: string[] = [];
    const failedNet: string[] = [];
    page.on("console", (msg: ConsoleMessage) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
    page.on("response", (res) => {
      if (res.status() >= 400 && res.url().includes("/api/")) {
        failedNet.push(`${res.status()} ${res.request().method()} ${res.url()}`);
      }
    });

    await ensureLoggedIn(page);

    const surfaces: Array<{
      route: string;
      name: string;
      renders: boolean;
      notes: string;
    }> = [];

    const crawl: Array<{ route: string; name: string; probe?: RegExp }> = [
      { route: "/mentrix-home", name: "Companion", probe: /Mentrix|Companion|Ask|GOOD TO SEE/i },
      { route: "/projects", name: "Projects", probe: /Project|Import|Create|Repo/i },
      { route: "/work-items", name: "Work Items", probe: /Work|Item|Ready|Ship/i },
      { route: "/workspace", name: "Developer", probe: /Developer|Workspace|Import|Repo|Branch|Code/i },
      { route: "/ask", name: "Agent Workspace", probe: /Agent|Ask|Plan|Workspace|Forge|Loading/i },
      { route: "/project-intelligence", name: "Project Intelligence", probe: /Intelligence|Lattice|Blueprint|Knowledge|READY|STALE|Project/i },
      { route: "/knowledge-base", name: "Knowledge", probe: /Knowledge|Document|Context/i },
      { route: "/learning", name: "ZECT Learning", probe: /Learning|Lesson|Practice|GUIDED|Python|Language/i },
      { route: "/fabric", name: "Processes", probe: /Process|Automation|Fabric|Loop|Camunda/i },
      { route: "/settings", name: "Settings", probe: /Settings|Preference|Telemetry/i },
      { route: "/mentrix", name: "Runs", probe: /Mentrix|Run|Approve|Gate/i },
    ];

    for (const item of crawl) {
      let renders = false;
      let notes = "";
      try {
        await gotoSoft(page, item.route);
        const body = await page.locator("body").innerText();
        const onLogin = /Welcome Back|Sign in to Mentrix/i.test(body);
        renders = !onLogin && (item.probe ? item.probe.test(body) : body.length > 20);
        if (!renders) notes = `body_snip=${body.slice(0, 160).replace(/\s+/g, " ")}`;
        await shot(page, `surface-${item.name.replace(/[^a-zA-Z0-9]+/g, "_")}`);
      } catch (e) {
        notes = String(e);
      }
      surfaces.push({ route: item.route, name: item.name, renders, notes });
    }

    // Companion sidebar regression probe (authenticated)
    await page.evaluate(() => localStorage.setItem("sidebar-collapsed", "false"));
    await gotoSoft(page, "/mentrix-home");
    await page.waitForTimeout(800);
    const expandBtn = page.getByTitle(/Expand sidebar/i).first();
    const collapseBtn = page.getByTitle(/Collapse sidebar/i).first();
    const expandVisible = await expandBtn.isVisible().catch(() => false);
    const collapseVisible = await collapseBtn.isVisible().catch(() => false);
    // Measure rail width before/after expand attempt
    const widthBefore = await page.locator("aside").first().evaluate((el) => (el as HTMLElement).offsetWidth).catch(() => 0);
    if (expandVisible) {
      await expandBtn.click().catch(() => undefined);
      await page.waitForTimeout(500);
    } else {
      // try bottom toggle even if title differs
      await page.locator("aside").getByRole("button").last().click().catch(() => undefined);
      await page.waitForTimeout(500);
    }
    const afterExpandCollapseVisible = await collapseBtn.isVisible().catch(() => false);
    const afterExpandExpandVisible = await expandBtn.isVisible().catch(() => false);
    const widthAfter = await page.locator("aside").first().evaluate((el) => (el as HTMLElement).offsetWidth).catch(() => 0);
    await shot(page, "companion-sidebar-after-expand-attempt");

    // Present Deck panel lives under Companion → Voice tab
    await gotoSoft(page, "/mentrix-home");
    const voiceTab = page.getByRole("button", { name: /^Voice$/i }).or(page.getByText(/^Voice$/i));
    if (await voiceTab.first().isVisible().catch(() => false)) {
      await voiceTab.first().click().catch(() => undefined);
      await page.waitForTimeout(700);
    }
    const presentCandidates = [
      page.getByText(/Present deck/i),
      page.getByRole("button", { name: /Present|Deck|Display/i }),
      page.getByTitle(/Present/i),
    ];
    let presentTabVisible = false;
    for (const c of presentCandidates) {
      if (await c.first().isVisible().catch(() => false)) {
        presentTabVisible = true;
        await c.first().click().catch(() => undefined);
        await page.waitForTimeout(800);
        break;
      }
    }
    const presentBody = await page.locator("body").innerText();
    const presentFindings = {
      standalonePresentRoute: "MISSING (/present not in App routes)",
      companionPresentEntry: presentTabVisible,
      hasZinnia: /Zinnia/i.test(presentBody),
      hasTemplate: /Template/i.test(presentBody),
      hasGenerate: /Generate|Prompt|Upload/i.test(presentBody),
      hasClone: /Clone|Rehearsal|Voice|Narrat/i.test(presentBody),
      snip: presentBody.slice(0, 500).replace(/\s+/g, " "),
    };
    await shot(page, "present-companion-panel");

    await gotoSoft(page, "/learning");
    const learningText = await page.locator("body").innerText();
    const learning = {
      hasGuided: /GUIDED/i.test(learningText),
      hasPractice: /Practice|Hint|Retry/i.test(learningText),
      hasLanguages: /Python|TypeScript|JavaScript/i.test(learningText),
      snip: learningText.slice(0, 400).replace(/\s+/g, " "),
    };
    await shot(page, "learning-page");

    await gotoSoft(page, "/projects");
    const projectsText = await page.locator("body").innerText();
    const projects = {
      hasImport: /Import Already-Cloned|Open Existing|Browse|Discover Local|Clone Remote/i.test(projectsText),
      hasCreate: /Create|New Project/i.test(projectsText),
      snip: projectsText.slice(0, 400).replace(/\s+/g, " "),
    };
    await shot(page, "projects-page");

    const forcedCollapsed =
      (expandVisible || widthBefore > 0) &&
      widthAfter > 0 &&
      widthAfter < 100 &&
      !afterExpandCollapseVisible;

    const report = {
      generated_at: new Date().toISOString(),
      develop_sha_expected: "396216a7feaea2477ad010c74966910947eca900",
      baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://localhost:5173",
      out_dir: OUT,
      surfaces,
      companion_sidebar: {
        expandVisibleBeforeClick: expandVisible,
        collapseVisibleBeforeClick: collapseVisible,
        afterExpandCollapseVisible,
        afterExpandExpandVisible,
        widthBefore,
        widthAfter,
        forcedCollapsedLikely: forcedCollapsed || (widthAfter > 0 && widthAfter < 100),
        code_cause:
          "Layout.tsx: mentrixHud forces setCollapsed(true) and collapsed={collapsed || mentrixHud}",
        verdict: forcedCollapsed || (widthAfter > 0 && widthAfter < 100 && expandVisible)
          ? "REGRESSION"
          : afterExpandCollapseVisible && widthAfter >= 200
            ? "PASS"
            : "PARTIAL",
      },
      presentFindings,
      learning,
      projects,
      consoleErrors: consoleErrors.slice(0, 40),
      failedNet: [...new Set(failedNet)].slice(0, 40),
    };
    fs.writeFileSync(path.join(OUT, "live-reconciliation.json"), JSON.stringify(report, null, 2));

    expect(surfaces.length).toBeGreaterThan(5);
  });
});
