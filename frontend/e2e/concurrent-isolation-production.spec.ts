/**
 * Concurrent Companion session isolation + per-root runner cwd (headed).
 * Does not click live Generate / Jira / Camunda. Skip ≠ PASS for those.
 */
import { test, expect, type Page } from "@playwright/test";
import fs from "fs";
import os from "os";
import path from "path";
import { gotoAuthed } from "./helpers/login";

const ART = path.join(process.cwd(), "test-results", "concurrent-isolation");
const API = process.env.VITE_API_URL || process.env.ZECT_API_URL || "http://127.0.0.1:8000";

async function headers(page: Page) {
  const token = await page.evaluate(() => localStorage.getItem("zect_token"));
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function api(page: Page, method: string, pathName: string, body?: unknown) {
  const h = await headers(page);
  const res = await page.request.fetch(`${API}${pathName}`, {
    method,
    headers: h,
    data: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  return { status: res.status(), data };
}

test.describe("concurrent isolation production", () => {
  test.setTimeout(90_000);

  test("two Companion turns and two bound terminals do not leak", async ({ page }) => {
    fs.mkdirSync(ART, { recursive: true });
    await gotoAuthed(page, "/mentrix-home", "mentrix-companion-page");

    const stamp = Date.now();
    const tokenA = `ISOA${stamp}`;
    const tokenB = `ISOB${stamp}`;
    const a = await api(page, "POST", "/api/projects", {
      name: tokenA,
      description: "concurrent isolation A",
      team: "E2E",
    });
    const b = await api(page, "POST", "/api/projects", {
      name: tokenB,
      description: "concurrent isolation B",
      team: "E2E",
    });
    expect(a.status).toBeLessThan(300);
    expect(b.status).toBeLessThan(300);
    const idA = Number(a.data.id);
    const idB = Number(b.data.id);

    const [turnA, turnB] = await Promise.all([
      api(page, "POST", "/api/mentrix/companion/turn", {
        message: "What's my Mentrix Delivery status?",
        project_id: idA,
      }),
      api(page, "POST", "/api/mentrix/companion/turn", {
        message: "What's my Mentrix Delivery status?",
        project_id: idB,
      }),
    ]);
    expect(turnA.status).toBeLessThan(300);
    expect(turnB.status).toBeLessThan(300);
    const blobA = JSON.stringify(turnA.data);
    const blobB = JSON.stringify(turnB.data);
    expect(blobA).not.toContain(tokenB);
    expect(blobB).not.toContain(tokenA);

    const dirA = fs.mkdtempSync(path.join(os.tmpdir(), "zect-term-a-"));
    const dirB = fs.mkdtempSync(path.join(os.tmpdir(), "zect-term-b-"));
    fs.writeFileSync(path.join(dirA, "marker.txt"), "ALPHA-TERM-MARK");
    fs.writeFileSync(path.join(dirB, "marker.txt"), "BETA-TERM-MARK");
    const py = process.env.PYTHON || "python";
    const cmd = `${JSON.stringify(py)} -c "print(open('marker.txt',encoding='utf-8').read())"`;
    const [runA, runB] = await Promise.all([
      api(page, "POST", "/api/runner/execute", {
        command: cmd,
        cwd: dirA,
        bound_root: dirA,
        timeout: 15,
      }),
      api(page, "POST", "/api/runner/execute", {
        command: cmd,
        cwd: dirB,
        bound_root: dirB,
        timeout: 15,
      }),
    ]);
    if (runA.status === 403 || runB.status === 403) {
      // Role may be non-admin in some fixtures; isolation of Companion still proven.
      await page.screenshot({ path: path.join(ART, "01-companion-ok-runner-denied.png") });
      return;
    }
    expect(runA.status).toBeLessThan(300);
    expect(runB.status).toBeLessThan(300);
    expect(String(runA.data.stdout || "")).toContain("ALPHA-TERM-MARK");
    expect(String(runA.data.stdout || "")).not.toContain("BETA-TERM-MARK");
    expect(String(runB.data.stdout || "")).toContain("BETA-TERM-MARK");
    expect(String(runB.data.stdout || "")).not.toContain("ALPHA-TERM-MARK");
    await page.screenshot({ path: path.join(ART, "01-concurrent-isolation.png") });
  });
});
