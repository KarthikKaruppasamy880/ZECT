import { defineConfig, devices } from "@playwright/test";
import base from "./playwright.config";

const baseURL = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:5173";

/**
 * Headed + video demo config for ZOAS Delivery and Present Deck walkthroughs.
 * Output: artifacts/demo-e2e-zoas-present/
 */
export default defineConfig({
  ...base,
  outputDir: "../artifacts/demo-e2e-zoas-present/test-results",
  workers: 1,
  retries: 0,
  timeout: 180_000,
  use: {
    ...base.use,
    baseURL,
    headless: false,
    launchOptions: {
      slowMo: 450,
    },
    video: "on",
    screenshot: "on",
    trace: "on",
  },
  projects: [
    { name: "setup", testMatch: /auth\.setup\.ts/ },
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        storageState: "e2e/.auth/user.json",
        headless: false,
        video: "on",
        screenshot: "on",
      },
      dependencies: ["setup"],
      testIgnore: /auth\.setup\.ts/,
    },
  ],
});
