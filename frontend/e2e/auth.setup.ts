import { test as setup, expect } from "@playwright/test";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const authFile = path.join(__dirname, ".auth", "user.json");

setup("authenticate", async ({ page }) => {
  const username =
    process.env.ZECT_USERNAME || process.env.ZECT_E2E_USER || "admin@zect.local";
  const password =
    process.env.ZECT_PASSWORD || process.env.ZECT_E2E_PASSWORD || "zect-dev-local";

  fs.mkdirSync(path.dirname(authFile), { recursive: true });

  await page.goto("/");
  await expect(page.getByTestId("login-username")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("login-username").fill(username);
  await page.getByTestId("login-password").fill(password);
  await page.getByTestId("login-submit").click();

  await expect(page.getByText(/Mentrix|Dashboard|Control Tower/i).first()).toBeVisible({
    timeout: 30_000,
  });

  const token = await page.evaluate(() => localStorage.getItem("zect_token"));
  expect(token).toBeTruthy();

  await page.context().storageState({ path: authFile });
});
