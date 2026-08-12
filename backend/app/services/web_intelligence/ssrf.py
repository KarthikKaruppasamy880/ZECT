"""SSRF / network-boundary protection for Web Intelligence URL retrieval.

Denies localhost, loopback, link-local, private/internal ranges, unsafe schemes,
and cloud metadata endpoints unless an explicitly trusted connector is used.
Revalidates redirects and resolved destinations.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse, urljoin

ALLOWED_SCHEMES = frozenset({"http", "https"})
BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "metadata.google.com",
        "instance-data",
    }
)
# Link-local / metadata IPv4 specials
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
    "application/javascript",  # rarely; still treated as untrusted text
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
    # AWS/GCP/Azure metadata classic
    if str(ip) in ("169.254.169.254", "169.254.170.2", "fd00:ec2::254"):
        return True
    return False


def resolve_and_validate_host(host: str) -> list[str]:
    """DNS-resolve host and ensure no resolved address is private/metadata."""
    if _host_is_blocked_name(host):
        raise SsrfBlocked(f"blocked_host:{host}")
    # Literal IP in hostname
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


def validate_url_for_fetch(url: str, *, trusted_connector: str | None = None) -> str:
    """Validate URL scheme/host for generic retrieval. Returns normalized URL.

    `trusted_connector` may be set for existing authorized connectors (e.g. github)
    that already enforce their own auth — still blocks private IPs and metadata.
    """
    u = (url or "").strip()
    if not u:
        raise SsrfBlocked("url_required")
    parsed = urlparse(u if "://" in u else f"https://{u}")
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise SsrfBlocked(f"unsafe_scheme:{parsed.scheme or 'none'}")
    host = (parsed.hostname or "").lower()
    if not host:
        raise SsrfBlocked("host_required")
    # Userinfo (embedded credentials) rejected early
    if parsed.username or parsed.password:
        raise SsrfBlocked("credentials_in_url_denied")
    # Even trusted connectors cannot hit metadata/private nets
    resolve_and_validate_host(host)
    path = parsed.path or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.scheme}://{host}{path}{query}"


def validate_redirect_target(base_url: str, location: str) -> str:
    """Revalidate absolute or relative redirect Location against SSRF policy."""
    joined = urljoin(base_url, location or "")
    return validate_url_for_fetch(joined)


def content_type_allowed(content_type: str | None) -> bool:
    ct = (content_type or "").split(";")[0].strip().lower()
    if not ct:
        return True  # allow empty; body still size-capped and sanitized
    return any(ct.startswith(p) or ct == p.rstrip("/") for p in ALLOWED_CONTENT_PREFIXES)
