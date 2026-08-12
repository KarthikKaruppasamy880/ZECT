"""SSRF / network-boundary protection for Web Intelligence URL retrieval.

Denies localhost, loopback, link-local, private/internal ranges, unsafe schemes,
unauthorized ports, and cloud metadata endpoints.
Resolves DNS, validates addresses, and connects only to a policy-safe IP
(mitigates DNS-rebinding TOCTOU). Revalidates every redirect target.
"""

from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from urllib.parse import urlparse, urljoin

ALLOWED_SCHEMES = frozenset({"http", "https"})
ALLOWED_PORTS = frozenset({80, 443})
BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "metadata.google.com",
        "instance-data",
    }
)
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
FETCH_TIMEOUT_SEC = 15
MAX_REDIRECTS = 5
ALLOWED_CONTENT_PREFIXES = (
    "text/",
    "application/json",
    "application/xml",
    "application/rss",
    "application/atom",
    "application/xhtml",
    "application/javascript",
)


class SsrfBlocked(ValueError):
    """Raised when a URL violates network-boundary policy."""


def _host_is_blocked_name(host: str) -> bool:
    h = (host or "").strip().lower().rstrip(".")
    if not h:
        return True
    if h in BLOCKED_HOSTS:
        return True
    if h.endswith(".localhost") or h.endswith(".local") or h.endswith(".internal"):
        return True
    if h == "metadata" or h.startswith("metadata."):
        return True
    return False


def _ip_is_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
        return True
    if ip.is_unspecified:
        return True
    for net in BLOCKED_NETWORKS:
        try:
            if ip in net:
                return True
        except Exception:
            continue
    if str(ip) in ("169.254.169.254", "169.254.170.2", "fd00:ec2::254"):
        return True
    return False


def resolve_and_validate_host(host: str) -> list[str]:
    """DNS-resolve host and ensure no resolved address is private/metadata."""
    if _host_is_blocked_name(host):
        raise SsrfBlocked(f"blocked_host:{host}")
    try:
        ip = ipaddress.ip_address(host)
        if _ip_is_blocked(ip):
            raise SsrfBlocked(f"blocked_ip:{host}")
        return [str(ip)]
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise SsrfBlocked(f"dns_failed:{host}") from e
    resolved: list[str] = []
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if _ip_is_blocked(ip):
            raise SsrfBlocked(f"blocked_resolved_ip:{addr}")
        resolved.append(str(ip))
    if not resolved:
        raise SsrfBlocked(f"no_resolvable_public_ip:{host}")
    return resolved


def _default_port(scheme: str, port: int | None) -> int:
    if port is not None:
        return int(port)
    return 443 if scheme == "https" else 80


def validate_url_for_fetch(url: str, *, trusted_connector: str | None = None) -> str:
    """Validate URL scheme/host/port for generic retrieval. Returns normalized URL.

    `trusted_connector` may be set for existing authorized connectors (e.g. github)
    that already enforce their own auth — still blocks private IPs and metadata.
    """
    del trusted_connector  # reserved; private/metadata always denied
    u = (url or "").strip()
    if not u:
        raise SsrfBlocked("url_required")
    parsed = urlparse(u if "://" in u else f"https://{u}")
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise SsrfBlocked(f"unsafe_scheme:{parsed.scheme or 'none'}")
    host = (parsed.hostname or "").lower()
    if not host:
        raise SsrfBlocked("host_required")
    if parsed.username or parsed.password:
        raise SsrfBlocked("credentials_in_url_denied")
    port = _default_port(parsed.scheme, parsed.port)
    if port not in ALLOWED_PORTS:
        raise SsrfBlocked(f"port_denied:{port}")
    resolve_and_validate_host(host)
    path = parsed.path or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    # Preserve explicit port (including non-default) for correct revalidation/connect
    if parsed.port:
        netloc = f"{host}:{parsed.port}"
    else:
        netloc = host
    return f"{parsed.scheme}://{netloc}{path}{query}"


def validate_redirect_target(base_url: str, location: str) -> str:
    """Revalidate absolute or relative redirect Location against SSRF policy."""
    joined = urljoin(base_url, location or "")
    return validate_url_for_fetch(joined)


def content_type_allowed(content_type: str | None) -> bool:
    ct = (content_type or "").split(";")[0].strip().lower()
    if not ct:
        return True
    return any(ct.startswith(p) or ct == p.rstrip("/") for p in ALLOWED_CONTENT_PREFIXES)


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, pinned_ip: str, port: int | None = None, **kwargs):
        self._pinned_ip = pinned_ip
        super().__init__(host, port=port, **kwargs)

    def connect(self) -> None:
        self.sock = socket.create_connection((self._pinned_ip, self.port), self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, pinned_ip: str, port: int | None = None, **kwargs):
        self._pinned_ip = pinned_ip
        super().__init__(host, port=port, **kwargs)

    def connect(self) -> None:
        sock = socket.create_connection((self._pinned_ip, self.port), self.timeout)
        context = self._context or ssl.create_default_context()
        server_hostname = self.host if isinstance(self.host, str) else None
        self.sock = context.wrap_socket(sock, server_hostname=server_hostname)


def pinned_http_get(url: str, *, trusted_connector: str | None = None) -> tuple[str, bytes, str]:
    """GET with DNS pin + redirect revalidation + size/timeout/content-type limits."""
    current = validate_url_for_fetch(url, trusted_connector=trusted_connector)
    redirects = 0
    while True:
        parsed = urlparse(current)
        host = (parsed.hostname or "").lower()
        scheme = parsed.scheme
        port = _default_port(scheme, parsed.port)
        if port not in ALLOWED_PORTS:
            raise SsrfBlocked(f"port_denied:{port}")
        # Re-resolve and pin: connect only to a currently validated public IP
        ips = resolve_and_validate_host(host)
        pinned_ip = ips[0]
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        headers = {
            "Host": host if not parsed.port else f"{host}:{parsed.port}",
            "User-Agent": "ZECT-WebIntelligence/1.0 (+untrusted-external-context)",
            "Accept": "text/*, application/json, application/xml, application/rss+xml, application/atom+xml, */*",
            "Connection": "close",
        }
        if scheme == "https":
            conn: http.client.HTTPConnection = _PinnedHTTPSConnection(
                host, pinned_ip, port=port, timeout=FETCH_TIMEOUT_SEC, context=ssl.create_default_context()
            )
        else:
            conn = _PinnedHTTPConnection(host, pinned_ip, port=port, timeout=FETCH_TIMEOUT_SEC)
        try:
            conn.request("GET", path, headers=headers)
            resp = conn.getresponse()
            if resp.status in (301, 302, 303, 307, 308):
                loc = resp.getheader("Location") or ""
                resp.read()
                conn.close()
                redirects += 1
                if redirects > MAX_REDIRECTS:
                    raise SsrfBlocked("too_many_redirects")
                current = validate_redirect_target(current, loc)
                continue
            ct = resp.getheader("Content-Type") or ""
            if not content_type_allowed(ct):
                raise ValueError(f"content_type_not_allowed:{ct}")
            chunks: list[bytes] = []
            total = 0
            while True:
                block = resp.read(64 * 1024)
                if not block:
                    break
                total += len(block)
                if total > MAX_RESPONSE_BYTES:
                    raise ValueError("response_too_large")
                chunks.append(block)
            body = b"".join(chunks)
            final_url = current
            return final_url, body, ct
        finally:
            try:
                conn.close()
            except Exception:
                pass
