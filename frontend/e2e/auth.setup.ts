import { test as setup, expect } from "@playwright/test";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const authFile = path.join(__dirname, ".auth", "user.json");

function loadEnvCreds() {
  const candidates = [
    path.resolve(__dirname, "../../../backend/.env"),
    path.resolve(__dirname, "../../backend/.env"),
  ];
  let username = process.env.ZECT_USERNAME || process.env.ZECT_E2E_USER || "admin@zect.local";
  let password = process.env.ZECT_PASSWORD || process.env.ZECT_E2E_PASSWORD || "zect-dev-local";
  for (const p of candidates) {
    try {
      for (const line of fs.readFileSync(p, "utf8").split(/\r?\n/)) {
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

setup("authenticate", async ({ page }) => {
  const { username, password } = loadEnvCreds();

  fs.mkdirSync(path.dirname(authFile), { recursive: true });

  await page.goto("/");
  await expect(page.getByTestId("login-username")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("login-username").fill(username);
  await page.getByTestId("login-password").fill(password);
  await page.getByTestId("login-submit").click();

  // Wait for post-login navigation (login page also contains "Mentrix" copy)
  await expect(page.getByTestId("login-submit")).toBeHidden({ timeout: 30_000 });
  await expect(page).not.toHaveURL(/\/login/, { timeout: 30_000 });

  const token = await page.evaluate(() => localStorage.getItem("zect_token"));
  expect(token).toBeTruthy();

  await page.context().storageState({ path: authFile });
});
