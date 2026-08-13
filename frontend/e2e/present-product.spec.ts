/**
 * Headed ZECT Present product proof (provider UI not used).
 * Login → /present → Zinnia visible → prompt → generate attempt → notes/rewrite → rehearsal controls.
 */
import { test, expect, type Page } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

const ART = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../test-results/present-product");

function loadEnvCreds() {
  const candidates = [
    path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../backend/.env"),
    path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../backend/.env"),
  ];
  let username = process.env.ZECT_USERNAME || "admin@zect.local";
  let password = process.env.ZECT_PASSWORD || "zect-dev-local";
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

async function ensureLoggedIn(page: Page) {
  const { username, password } = loadEnvCreds();
  await page.goto("/");
  const loginVisible = await page.getByTestId("login-username").isVisible().catch(() => false);
  const token = await page.evaluate(() => localStorage.getItem("zect_token"));
  if (loginVisible || !token) {
    await expect(page.getByTestId("login-username")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("login-username").fill(username);
    await page.getByTestId("login-password").fill(password);
    await page.getByTestId("login-submit").click();
    await expect(page.getByTestId("login-submit")).toBeHidden({ timeout: 30_000 });
  }
  expect(await page.evaluate(() => localStorage.getItem("zect_token"))).toBeTruthy();
}

test.describe("ZECT Present product", () => {
  test("gallery → zinnia → generate workspace → notes", async ({ page }) => {
    fs.mkdirSync(ART, { recursive: true });
    await ensureLoggedIn(page);
    await page.goto("/present");
    await expect(page.getByTestId("zect-present-page")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByRole("link", { name: "Present" })).toBeVisible();
    await expect(page.getByTestId("zect-present-template-zinnia-executive-v1")).toBeVisible();
    await expect(page.getByTestId("zect-present-upload-template")).toBeAttached();
    await expect(page.getByTestId("zect-present-upload-org-scope")).toBeAttached();
    await page.screenshot({ path: path.join(ART, "01-gallery.png") });

    await page.getByTestId("zect-present-template-zinnia-executive-v1").click();
    await expect(page.getByTestId("present-lifecycle-state")).toBeVisible();
    await expect(page.getByTestId("zect-present-template-preview")).toBeVisible();

    await page.getByTestId("zect-present-upload-template").setInputFiles({
      name: "tiny.pptx",
      mimeType: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
      buffer: Buffer.from("PK\x03\x04fake-pptx"),
    });
    await page.getByTestId("zect-present-template-zinnia-executive-v1").click();
    await page.getByTestId("zect-present-continue-generate").click();
    await expect(page.getByTestId("zect-present-workspace")).toBeVisible();
    await expect(page.getByTestId("zect-present-selected")).toContainText("zinnia-executive-v1");
    await expect(page.getByTestId("present-deck-panel")).toBeVisible();
    await expect(page.getByTestId("present-deck-template")).toHaveValue("zinnia-executive-v1");

    await page.getByTestId("present-deck-prompt").fill(
      "Zinnia executive brief: Q3 delivery status, top risks, decisions needed.",
    );
    await page.getByTestId("zect-present-rewrite").fill(
      "Executive tone: lead with status, then decisions, then owners.",
    );
    await page.screenshot({ path: path.join(ART, "02-workspace.png") });

    // Generate may be BLOCKED_EXTERNAL if Presenton is down — still prove UI + attempt
    const gen = page.getByTestId("present-deck-generate");
    await expect(gen).toBeVisible();
    let generateAttempted = false;
    let templateSent: string | null = null;
    let zinniaVerified: boolean | null = null;
    let blockedExternal = false;
    page.on("response", async (res) => {
      if (!res.url().includes("/api/mentrix/presenton/generate")) return;
      try {
        const body = await res.json();
        const detail = body?.detail && typeof body.detail === "object" ? body.detail : body;
        if (detail?.template_sent) templateSent = String(detail.template_sent);
        if (typeof detail?.zinnia_verified === "boolean") zinniaVerified = detail.zinnia_verified;
        if (detail?.blocked_external) blockedExternal = true;
      } catch {
        /* ignore non-json */
      }
    });
    if (await gen.isEnabled()) {
      generateAttempted = true;
      await gen.click();
      await page.waitForTimeout(3500);
    }
    await expect(page.getByTestId("present-deck-notes")).toBeVisible();
    await expect(page.getByTestId("present-deck-analyze")).toBeVisible();
    await page.screenshot({ path: path.join(ART, "03-notes-rehearse.png") });

    fs.writeFileSync(
      path.join(ART, "evidence.json"),
      JSON.stringify(
        {
          ok: true,
          zinnia_visible: true,
          workspace: true,
          generate_attempted: generateAttempted,
          template_sent: templateSent,
          zinnia_verified: zinniaVerified,
          blocked_external: blockedExternal,
          presenton_required_for_pptx: true,
          note: "PPTX PASS requires Presenton + registry mapping, not env",
        },
        null,
        2,
      ),
    );
  });
});
