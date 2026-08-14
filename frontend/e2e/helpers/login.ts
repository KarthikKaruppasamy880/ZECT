import { expect, type Page } from "@playwright/test";
import { loadEnvCreds } from "./env";

async function submitLogin(page: Page) {
  const { username, password } = loadEnvCreds();
  await expect(page.getByTestId("login-username")).toBeVisible({ timeout: 20_000 });
  await page.getByTestId("login-username").fill(username);
  await page.getByTestId("login-password").fill(password);
  await page.getByTestId("login-submit").click();
  await expect(page.getByTestId("login-submit")).toBeHidden({ timeout: 30_000 });
}

/** Login even when storageState still holds an expired zect_token. */
export async function ensureLoggedIn(page: Page) {
  await page.goto("/");
  await page.waitForLoadState("domcontentloaded");
  const loginForm = page.getByTestId("login-username");
  if (await loginForm.isVisible().catch(() => false)) {
    await submitLogin(page);
    return;
  }
  await page.waitForTimeout(400);
  if (await loginForm.isVisible().catch(() => false)) {
    await submitLogin(page);
  }
}

/** Navigate to an authed route; re-login if the app bounced to the login form. */
export async function gotoAuthed(page: Page, path: string, readyTestId: string, timeout = 25_000) {
  await ensureLoggedIn(page);
  await page.goto(path);
  const ready = page.getByTestId(readyTestId);
  const loginForm = page.getByTestId("login-username");
  const seen = await Promise.race([
    ready.waitFor({ state: "visible", timeout }).then(() => "ready" as const),
    loginForm.waitFor({ state: "visible", timeout }).then(() => "login" as const),
  ]).catch(() => "none" as const);
  if (seen === "login" || (await loginForm.isVisible().catch(() => false))) {
    await submitLogin(page);
    await page.goto(path);
  }
  await expect(page.getByTestId(readyTestId)).toBeVisible({ timeout });
}
