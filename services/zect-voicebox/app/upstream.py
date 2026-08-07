"""HTTP proxy to an upstream Voicebox-compatible engine."""

from __future__ import annotations

from typing import Any

import httpx

from app import config


class UpstreamError(RuntimeError):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(f"upstream {status}: {detail[:300]}")


async def upstream_online(client: httpx.AsyncClient | None = None) -> bool:
    base = config.upstream_url()
    if not base:
        return False
    own = client is None
    if own:
        client = httpx.AsyncClient(timeout=httpx.Timeout(2.0, connect=1.0))
    assert client is not None
    try:
        res = await client.get(f"{base}/profiles")
        return res.status_code < 500
    except Exception:
        return False
    finally:
        if own:
            await client.aclose()


async def proxy_request(
    method: str,
    path: str,
    *,
    json: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    files: dict[str, Any] | None = None,
    timeout: float = 180.0,
) -> httpx.Response:
    base = config.upstream_url()
    if not base:
        raise UpstreamError(503, "ZECT_VOICEBOX_UPSTREAM_URL not set")
    url = f"{base}{path}"
    # Fast connect so Mentrix 2s /profiles health check is not blocked.
    # Pool timeout also capped — Windows can otherwise stall on a dead :17494.
    connect = min(0.5, timeout) if timeout <= 2.0 else min(1.5, timeout)
    timeout_cfg = httpx.Timeout(timeout, connect=connect, pool=connect)
    async with httpx.AsyncClient(timeout=timeout_cfg) as client:
        try:
            res = await client.request(method, url, json=json, data=data, files=files)
        except httpx.ConnectError as exc:
            raise UpstreamError(503, f"Cannot reach upstream at {base}: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise UpstreamError(504, f"Upstream timeout at {base}: {exc}") from exc
        except httpx.HTTPError as exc:
            raise UpstreamError(503, f"Upstream HTTP error at {base}: {exc}") from exc
        return res


def raise_if_bad(res: httpx.Response) -> None:
    if res.status_code >= 400:
        raise UpstreamError(res.status_code, res.text or res.reason_phrase or "error")
