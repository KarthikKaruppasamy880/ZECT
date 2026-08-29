"""ZECT Mentrix Playwright MCP adapter — local browser automation (no external IDE)."""

from __future__ import annotations

import os
from typing import Any

# Module-level browser reuse for a single process (optional).
# PA-4: each call still gets an isolated BrowserContext; contexts keyed by session.
_browser = None
_playwright = None
_session_contexts: dict[str, Any] = {}


def shutdown() -> None:
    """Close the shared browser/driver process. The module launches one
    Chromium + Playwright driver on first use and otherwise never closes it --
    fine for a long-lived backend process, but tests must call this in
    teardown or a live browser+driver process outlives the test file and can
    interfere with everything that runs after it in the same session."""
    global _browser, _playwright
    for ctx in list(_session_contexts.values()):
        try:
            ctx.close()
        except Exception:
            pass
    _session_contexts.clear()
    if _browser is not None:
        try:
            _browser.close()
        except Exception:
            pass
        _browser = None
    if _playwright is not None:
        try:
            _playwright.stop()
        except Exception:
            pass
        _playwright = None


def _pw_available() -> tuple[bool, str]:
    try:
        import playwright  # noqa: F401
        from playwright.sync_api import sync_playwright  # noqa: F401

        return True, ""
    except ImportError:
        return False, (
            "Playwright not installed. Run: pip install playwright && playwright install chromium"
        )


def _attach_evidence_listeners(page) -> None:
    """Every page gets console-error and failed/4xx+ network capture attached
    at creation, not opt-in per action -- so whichever action the agent takes
    (navigate/click/fill/select), the evidence is already there to read back."""
    console_errors: list[dict[str, Any]] = []
    network_failures: list[dict[str, Any]] = []

    def _on_console(msg) -> None:
        if msg.type in ("error", "warning"):
            console_errors.append({"type": msg.type, "text": msg.text})

    def _on_request_failed(request) -> None:
        network_failures.append(
            {"url": request.url, "method": request.method, "failure": str(request.failure)}
        )

    def _on_response(response) -> None:
        if response.status >= 400:
            network_failures.append({"url": response.url, "status": response.status})

    page.on("console", _on_console)
    page.on("requestfailed", _on_request_failed)
    page.on("response", _on_response)
    page._zect_console_errors = console_errors  # noqa: SLF001 -- our own tag, not Playwright internals
    page._zect_network_failures = network_failures  # noqa: SLF001


def _get_page(session_id: str = ""):
    """Return (context, page). Always a fresh context when session_id empty;
    reuse only within the same session_id for multi-step fills, then close.
    """
    global _browser, _playwright
    from playwright.sync_api import sync_playwright

    if _browser is None:
        _playwright = sync_playwright().start()
        headless = os.getenv("MENTRIX_PLAYWRIGHT_HEADLESS", "1") != "0"
        _browser = _playwright.chromium.launch(headless=headless)
    sid = (session_id or "").strip()
    if sid and sid in _session_contexts:
        ctx = _session_contexts[sid]
        page = ctx.new_page()
        _attach_evidence_listeners(page)
        return ctx, page
    context = _browser.new_context(
        accept_downloads=False,
        java_script_enabled=True,
        bypass_csp=False,
    )
    if sid:
        _session_contexts[sid] = context
        # Cap session map
        if len(_session_contexts) > 8:
            old = next(iter(_session_contexts))
            try:
                _session_contexts.pop(old).close()
            except Exception:
                _session_contexts.pop(old, None)
    page = context.new_page()
    _attach_evidence_listeners(page)
    return context, page


def _evidence(page) -> dict[str, Any]:
    """Tolerates a mocked ``page`` in tests (arbitrary-attribute mocks are not
    real lists) by only trusting an attribute that is actually a list."""

    def _safe_list(value: Any) -> list[Any]:
        return list(value) if isinstance(value, list) else []

    return {
        "console_errors": _safe_list(getattr(page, "_zect_console_errors", None)),
        "network_failures": _safe_list(getattr(page, "_zect_network_failures", None)),
    }


def execute(tool_name: str, arguments: dict, *, config: dict, enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {"status": "disabled"}
    ok, msg = _pw_available()
    if not ok:
        return {
            "status": "not_configured",
            "message": msg,
            "dry_run": {"tool": tool_name, "arguments": arguments},
        }

    if tool_name == "status":
        return {"status": "ready", "engine": "browser_automation"}

    # PA-4: never scrape or fill password fields
    selector = str(arguments.get("selector") or "")
    sel_l = selector.lower()
    if "password" in sel_l or "type=password" in sel_l or "[type=\"password\"]" in sel_l:
        return {
            "status": "error",
            "error": "password_scrape_forbidden",
            "message": "Mentrix never reads or fills password fields",
            "verified": False,
        }
    if tool_name == "fill" and str(arguments.get("field_type") or "").lower() == "password":
        return {
            "status": "error",
            "error": "password_scrape_forbidden",
            "message": "Mentrix never fills password fields",
            "verified": False,
        }

    try:
        session_id = str(arguments.get("session_id") or config.get("session_id") or "")
        context, page = _get_page(session_id)
        try:
            if tool_name == "navigate":
                url = arguments.get("url") or arguments.get("path") or ""
                if not url:
                    return {"status": "error", "message": "url required"}
                page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                return {
                    "status": "ok",
                    "url": page.url,
                    "title": page.title(),
                    "verified": True,
                    "verification": {"kind": "dom", "url": page.url, "title": page.title()},
                    **_evidence(page),
                }
            if tool_name == "snapshot":
                url = arguments.get("url")
                if url:
                    page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                # Refuse password values in snapshot text
                text = page.inner_text("body")[:8000]
                # Strip common password input values via DOM check
                try:
                    pwd_count = page.locator('input[type="password"]').count()
                except Exception:
                    pwd_count = 0
                return {
                    "status": "ok",
                    "url": page.url,
                    "title": page.title(),
                    "text": text,
                    "password_fields_present": pwd_count,
                    "password_values_redacted": True,
                    "verified": True,
                    "verification": {"kind": "dom_snapshot", "url": page.url},
                    **_evidence(page),
                }
            if tool_name == "click":
                selector = arguments.get("selector") or ""
                if not selector:
                    return {"status": "error", "message": "selector required"}
                loc = page.locator(selector).first
                loc.wait_for(state="visible", timeout=15_000)
                before_url = page.url
                loc.click(timeout=15_000)
                page.wait_for_timeout(150)
                return {
                    "status": "ok",
                    "clicked": selector,
                    "url": page.url,
                    "verified": True,
                    "verification": {
                        "kind": "dom_click",
                        "selector": selector,
                        "url_before": before_url,
                        "url_after": page.url,
                        "visible": True,
                    },
                    **_evidence(page),
                }
            if tool_name == "fill":
                selector = arguments.get("selector") or ""
                value = arguments.get("value", "")
                if not selector:
                    return {"status": "error", "message": "selector required"}
                # Guard: if matched element is password type, refuse
                try:
                    el_type = page.locator(selector).first.get_attribute("type") or ""
                    if el_type.lower() == "password":
                        return {
                            "status": "error",
                            "error": "password_scrape_forbidden",
                            "message": "Target element is type=password",
                            "verified": False,
                        }
                except Exception:
                    pass
                max_attempts = int(arguments.get("retries") or 2)
                last_err = None
                for attempt in range(max(1, max_attempts)):
                    try:
                        page.locator(selector).first.wait_for(state="visible", timeout=15_000)
                        page.fill(selector, str(value), timeout=15_000)
                        actual = page.input_value(selector)
                        if str(actual) != str(value):
                            raise RuntimeError(
                                f"fill verify failed: expected {value!r} got {actual!r}"
                            )
                        return {
                            "status": "ok",
                            "filled": selector,
                            "verified": True,
                            "url": page.url,
                            "engine": "browser_automation",
                            "attempt": attempt + 1,
                            "verification": {"kind": "dom_fill", "selector": selector, "matched": True},
                            **_evidence(page),
                        }
                    except Exception as exc:  # noqa: BLE001
                        last_err = exc
                        try:
                            shot = page.screenshot(type="png")
                            import base64

                            artifact = base64.b64encode(shot[:4096]).decode("ascii")
                        except Exception:
                            artifact = ""
                        if attempt + 1 >= max_attempts:
                            return {
                                "status": "error",
                                "message": str(last_err),
                                "tool": tool_name,
                                "verified": False,
                                "screenshot_b64_prefix": artifact,
                                "dom_excerpt": (page.content() or "")[:2000],
                                "engine": "browser_automation",
                            }
                return {"status": "error", "message": str(last_err), "tool": tool_name}
            if tool_name == "select_option":
                selector = arguments.get("selector") or ""
                value = arguments.get("value", "")
                if not selector:
                    return {"status": "error", "message": "selector required"}
                if arguments.get("url"):
                    page.goto(arguments["url"], wait_until="domcontentloaded", timeout=30_000)
                page.locator(selector).first.wait_for(state="visible", timeout=15_000)
                selected = page.select_option(selector, str(value))
                return {
                    "status": "ok",
                    "selected": selector,
                    "value": selected,
                    "verified": bool(selected),
                    "url": page.url,
                    **_evidence(page),
                }
            if tool_name == "screenshot":
                url = arguments.get("url")
                if url:
                    page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                png = page.screenshot(type="png", full_page=bool(arguments.get("full_page", True)))
                import base64

                return {
                    "status": "ok",
                    "url": page.url,
                    "png_bytes": png,  # raw bytes -- the tool-loop wrapper decides how much to keep
                    "verified": True,
                    "verification": {"kind": "screenshot", "url": page.url, "size_bytes": len(png)},
                    **_evidence(page),
                }
            if tool_name == "wait_for":
                selector = arguments.get("selector") or ""
                state = arguments.get("state") or "visible"
                timeout_ms = int(arguments.get("timeout_ms") or 15_000)
                if arguments.get("url"):
                    page.goto(arguments["url"], wait_until="domcontentloaded", timeout=30_000)
                if selector:
                    try:
                        page.locator(selector).first.wait_for(state=state, timeout=timeout_ms)
                        ok = True
                    except Exception:
                        ok = False
                else:
                    page.wait_for_timeout(min(timeout_ms, 10_000))
                    ok = True
                return {
                    "status": "ok" if ok else "error",
                    "waited_for": selector or f"{timeout_ms}ms",
                    "state": state,
                    "verified": ok,
                    **_evidence(page),
                }
            if tool_name == "assert_text":
                expected = str(arguments.get("expected") or "")
                selector = arguments.get("selector") or "body"
                if not expected:
                    return {"status": "error", "message": "expected required"}
                if arguments.get("url"):
                    page.goto(arguments["url"], wait_until="domcontentloaded", timeout=30_000)
                actual = page.locator(selector).first.inner_text()
                matched = expected in actual
                return {
                    "status": "ok" if matched else "error",
                    "assertion": "text_contains",
                    "expected": expected,
                    "matched": matched,
                    "verified": matched,
                    "actual_excerpt": actual[:500],
                    **_evidence(page),
                }
            if tool_name == "assert_visible":
                selector = arguments.get("selector") or ""
                if not selector:
                    return {"status": "error", "message": "selector required"}
                if arguments.get("url"):
                    page.goto(arguments["url"], wait_until="domcontentloaded", timeout=30_000)
                visible = page.locator(selector).first.is_visible()
                return {
                    "status": "ok" if visible else "error",
                    "assertion": "visible",
                    "selector": selector,
                    "verified": visible,
                    **_evidence(page),
                }
            if tool_name in ("console_errors", "network_failures"):
                url = arguments.get("url")
                if url:
                    page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                    page.wait_for_timeout(500)  # let late console/network events land
                return {"status": "ok", "url": page.url, "verified": True, **_evidence(page)}
            return {"status": "unknown_tool", "tool": tool_name}
        finally:
            # Close page always; close context unless held for a named session
            try:
                page.close()
            except Exception:
                pass
            sid = str(arguments.get("session_id") or config.get("session_id") or "").strip()
            if not sid:
                try:
                    context.close()
                except Exception:
                    pass
            elif arguments.get("end_session"):
                try:
                    context.close()
                except Exception:
                    pass
                _session_contexts.pop(sid, None)
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": str(exc), "tool": tool_name}

