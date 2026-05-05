"""Pre-built Playwright login script for ZECT.

Usage:
    python scripts/playwright_login.py [--url http://localhost:5173] [--email EMAIL] [--password PASSWORD]

This script automates login to the ZECT frontend using Playwright.
It can connect to an existing Chrome instance via CDP or launch a new browser.
After login, session state persists for further manual or automated testing.
"""

import argparse
import asyncio
import os
import sys

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)


async def login(
    url: str = "http://localhost:5173",
    email: str | None = None,
    password: str | None = None,
    cdp_url: str | None = None,
    headless: bool = False,
    screenshot_path: str | None = None,
):
    """Login to ZECT and verify dashboard loads."""
    email = email or os.environ.get("ZECT_EMAIL", "karthik.karuppasamy@Zinnia.com")
    password = password or os.environ.get("ZECT_PASSWORD", "Karthik@1234")

    async with async_playwright() as p:
        if cdp_url:
            browser = await p.chromium.connect_over_cdp(cdp_url)
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
        else:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context()

        page = await context.new_page()

        print(f"[ZECT Login] Navigating to {url}")
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Check if already logged in (dashboard visible)
        if await page.query_selector("text=Engineering Delivery"):
            print("[ZECT Login] Already logged in - dashboard visible")
        else:
            print("[ZECT Login] Filling login form...")
            # Fill email
            email_input = await page.query_selector('input[type="email"], input[placeholder*="email" i]')
            if email_input:
                await email_input.fill(email)
            else:
                # Try first input field
                inputs = await page.query_selector_all("input")
                if len(inputs) >= 1:
                    await inputs[0].fill(email)

            # Fill password
            password_input = await page.query_selector('input[type="password"]')
            if password_input:
                await password_input.fill(password)
            elif len(inputs) >= 2:
                await inputs[1].fill(password)

            # Click login button
            login_btn = await page.query_selector('button[type="submit"], button:has-text("Sign In"), button:has-text("Login")')
            if login_btn:
                await login_btn.click()
            else:
                await page.keyboard.press("Enter")

            await page.wait_for_timeout(2000)
            print("[ZECT Login] Login submitted, waiting for dashboard...")

        # Verify dashboard loaded
        await page.wait_for_timeout(1000)
        title = await page.title()
        current_url = page.url

        if screenshot_path:
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"[ZECT Login] Screenshot saved to {screenshot_path}")

        # Check for dashboard indicators
        dashboard_visible = await page.query_selector("text=Engineering Delivery") is not None
        sidebar_visible = await page.query_selector("nav") is not None

        if dashboard_visible and sidebar_visible:
            print(f"[ZECT Login] SUCCESS - Dashboard loaded at {current_url}")
            return True
        else:
            # Check for error messages
            error_el = await page.query_selector(".text-red-700, .text-red-500, [role='alert']")
            if error_el:
                error_text = await error_el.text_content()
                print(f"[ZECT Login] FAILED - Error: {error_text}")
            else:
                print(f"[ZECT Login] FAILED - Dashboard not detected at {current_url} (title: {title})")
            return False


async def test_all_pages(url: str = "http://localhost:5173", cdp_url: str | None = None):
    """Navigate to all sidebar pages and verify they load without errors."""
    pages = [
        ("/", "Dashboard"),
        ("/ask", "Ask Mode"),
        ("/plan", "Plan Mode"),
        ("/build", "Build Phase"),
        ("/review", "Review Phase"),
        ("/deploy", "Deployment"),
        ("/skills", "Skill Library"),
        ("/token-controls", "Token Controls"),
        ("/audit-trail", "Audit Trail"),
        ("/rules", "Rules Engine"),
        ("/integrations", "Integrations"),
        ("/export", "Export/Share"),
        ("/output-history", "Output History"),
        ("/settings", "Settings"),
        ("/analytics", "Analytics"),
        ("/code-review", "Code Review"),
        ("/repo-analysis", "Repo Analysis"),
    ]

    async with async_playwright() as p:
        if cdp_url:
            browser = await p.chromium.connect_over_cdp(cdp_url)
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
        else:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()

        page = await context.new_page()
        results = []

        for path, name in pages:
            try:
                await page.goto(f"{url}{path}", wait_until="networkidle", timeout=10000)
                # Check for React error boundaries or 500 errors
                error_el = await page.query_selector(".text-red-700, [role='alert'], text=500")
                has_error = error_el is not None
                results.append({"page": name, "path": path, "status": "FAIL" if has_error else "PASS"})
                status = "FAIL" if has_error else "PASS"
                print(f"  [{status}] {name} ({path})")
            except Exception as e:
                results.append({"page": name, "path": path, "status": "ERROR", "error": str(e)})
                print(f"  [ERROR] {name} ({path}): {e}")

        passed = sum(1 for r in results if r["status"] == "PASS")
        total = len(results)
        print(f"\nResults: {passed}/{total} pages passed")
        return results


def main():
    parser = argparse.ArgumentParser(description="ZECT Playwright Login & Test Script")
    parser.add_argument("--url", default="http://localhost:5173", help="ZECT frontend URL")
    parser.add_argument("--email", help="Login email (or set ZECT_EMAIL env var)")
    parser.add_argument("--password", help="Login password (or set ZECT_PASSWORD env var)")
    parser.add_argument("--cdp", default=None, help="Chrome CDP URL (e.g., http://localhost:29229)")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--screenshot", default=None, help="Save screenshot after login")
    parser.add_argument("--test-all", action="store_true", help="Test all pages after login")
    args = parser.parse_args()

    success = asyncio.run(login(
        url=args.url,
        email=args.email,
        password=args.password,
        cdp_url=args.cdp,
        headless=args.headless,
        screenshot_path=args.screenshot,
    ))

    if success and args.test_all:
        print("\n--- Testing all pages ---")
        asyncio.run(test_all_pages(url=args.url, cdp_url=args.cdp))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
