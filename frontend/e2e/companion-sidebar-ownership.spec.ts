/**
 * P0: Companion sidebar user ownership — headed proof.
 * expand → Companion → labels remain → collapse → navigate/back → persisted → expand → labels restore
 */
import { test, expect, type Page } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

const ART = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../test-results/companion-sidebar-p0");

function ensureArt() {
  fs.mkdirSync(ART, { recursive: true });
}

function loadEnvCreds(): { username: string; password: string } {
  const candidates = [
    path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../backend/.env"),
    path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../backend/.env"),
  ];
  let username =
    process.env.ZECT_USERNAME || process.env.ZECT_E2E_USER || "admin@zect.local";
  let password =
    process.env.ZECT_PASSWORD || process.env.ZECT_E2E_PASSWORD || "zect-dev-local";
  for (const p of candidates) {
    try {
      const raw = fs.readFileSync(p, "utf8");
      for (const line of raw.split(/\r?\n/)) {
        const m = line.match(/^(ZECT_USERNAME|ZECT_PASSWORD)=(.*)$/);
        if (!m) continue;
        const v = m[2].replace(/^["']|["']$/g, "");
        if (m[1] === "ZECT_USERNAME") username = v;
        if (m[1] === "ZECT_PASSWORD") password = v;
      }
      break;
    } catch {
      /* next */
    }
  }
  return { username, password };
}

async function ensureLoggedIn(page: Page) {
  const { username, password } = loadEnvCreds();
  await page.goto("/", { waitUntil: "domcontentloaded" });
  if (await page.getByTestId("login-username").isVisible().catch(() => false)) {
    await page.getByTestId("login-username").fill(username);
    await page.getByTestId("login-password").fill(password);
    await page.getByTestId("login-submit").click();
    await expect(page.getByTestId("login-submit")).toBeHidden({ timeout: 30_000 });
  }
  expect(await page.evaluate(() => localStorage.getItem("zect_token"))).toBeTruthy();
}

async function shot(page: Page, name: string) {
  ensureArt();
  await page.screenshot({ path: path.join(ART, `${name}.png`), fullPage: false });
}

async function assertExpanded(page: Page) {
  const aside = page.locator('[data-testid="app-sidebar"]');
  await expect(aside.getByText("Mentrix Companion", { exact: true })).toBeVisible({ timeout: 10000 });
}

async function assertCollapsed(page: Page) {
  const aside = page.locator('[data-testid="app-sidebar"]');
  await expect(aside.getByText("Mentrix Companion", { exact: true })).toBeHidden({ timeout: 10000 });
}

async function gotoAuthed(page: Page, route: string) {
  await page.goto(route, { waitUntil: "domcontentloaded" });
  if (await page.getByTestId("login-username").isVisible().catch(() => false)) {
    await ensureLoggedIn(page);
    await page.goto(route, { waitUntil: "domcontentloaded" });
  }
  await page.waitForTimeout(300);
}

async function setCollapsed(page: Page, collapsed: boolean) {
  await page.evaluate((c) => localStorage.setItem("sidebar-collapsed", String(c)), collapsed);
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.waitForTimeout(300);
  if (await page.getByTestId("login-username").isVisible().catch(() => false)) {
    await ensureLoggedIn(page);
  }
}

test.describe("P0 Companion sidebar user ownership", () => {
  test("expand persists through Companion and navigation", async ({ page }) => {
    ensureArt();
    await ensureLoggedIn(page);

    await setCollapsed(page, false);
    await gotoAuthed(page, "/projects");
    await assertExpanded(page);
    await shot(page, "01-projects-expanded");

    await gotoAuthed(page, "/mentrix-home");
    await expect(page.getByText(/^Chat$/i).first()).toBeVisible({ timeout: 20000 });
    await assertExpanded(page);
    await expect(page.getByText(/^Voice$/i).first()).toBeVisible();
    await shot(page, "02-companion-expanded");

    await page.evaluate(() => {
      const btn = document.querySelector(
        '[data-testid="sidebar-toggle-footer"]',
      ) as HTMLButtonElement | null;
      if (!btn) throw new Error("sidebar toggle not found");
      btn.click();
    });
    await assertCollapsed(page);
    await shot(page, "03-companion-collapsed");

    await gotoAuthed(page, "/projects");
    await assertCollapsed(page);
    await gotoAuthed(page, "/mentrix-home");
    await assertCollapsed(page);
    expect(await page.evaluate(() => localStorage.getItem("sidebar-collapsed"))).toBe("true");
    await shot(page, "04-companion-persisted-collapsed");

    await setCollapsed(page, false);
    await gotoAuthed(page, "/projects");
    await assertExpanded(page);
    await gotoAuthed(page, "/mentrix-home");
    await expect(page.getByText(/^Chat$/i).first()).toBeVisible({ timeout: 20000 });
    await assertExpanded(page);
    expect(await page.evaluate(() => localStorage.getItem("sidebar-collapsed"))).toBe("false");

    await page.evaluate(() => {
      (document.querySelector('[data-testid="sidebar-toggle-footer"]') as HTMLButtonElement).click();
    });
    await assertCollapsed(page);
    await page.waitForTimeout(300);
    await page.evaluate(() => {
      (document.querySelector('[data-testid="sidebar-toggle-footer"]') as HTMLButtonElement).click();
    });
    await assertExpanded(page);
    await shot(page, "05-companion-labels-restored");

    fs.writeFileSync(
      path.join(ART, "evidence.json"),
      JSON.stringify(
        {
          ok: true,
          verdict: "PASS",
          proof: "expand→Companion labels→collapse→nav/back persist→expand restore",
        },
        null,
        2,
      ),
    );
  });
});
