"""Azure AD / Entra OIDC JWT validation (ready when ZECT_AUTH_MODE=oidc|hybrid)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class OidcClaims:
    sub: str
    email: str
    name: str
    raw: dict[str, Any]


def oidc_configured() -> bool:
    return bool(
        os.getenv("AZURE_TENANT_ID", "").strip()
        and os.getenv("AZURE_CLIENT_ID", "").strip()
        and os.getenv("AZURE_API_AUDIENCE", "").strip()
    )


def issuer_uri() -> str:
    tenant = os.getenv("AZURE_TENANT_ID", "").strip()
    return f"https://login.microsoftonline.com/{tenant}/v2.0"


async def validate_bearer_jwt(token: str) -> OidcClaims:
    """Validate JWT via JWKS. Raises ValueError on failure.

    Uses PyJWT when installed; otherwise raises with setup guidance.
    """
    try:
        import jwt
        from jwt import PyJWKClient
    except ImportError as exc:
        raise ValueError(
            "PyJWT is required for OIDC. Install with: pip install PyJWT cryptography"
        ) from exc

    if not oidc_configured():
        raise ValueError("OIDC is not configured (AZURE_TENANT_ID / CLIENT_ID / API_AUDIENCE)")

    audience = os.getenv("AZURE_API_AUDIENCE", "").strip()
    issuer = issuer_uri()
    jwks_url = f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID')}/discovery/v2.0/keys"
    jwks_client = PyJWKClient(jwks_url)
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=audience,
        issuer=issuer,
        options={"require": ["exp", "sub"]},
    )
    email = (
        payload.get("preferred_username")
        or payload.get("email")
        or payload.get("upn")
        or ""
    )
    return OidcClaims(
        sub=str(payload.get("sub", "")),
        email=str(email),
        name=str(payload.get("name") or email or payload.get("sub") or ""),
        raw=payload,
    )


def oidc_login_url(redirect_uri: str, state: str = "") -> str:
    tenant = os.getenv("AZURE_TENANT_ID", "").strip()
    client_id = os.getenv("AZURE_CLIENT_ID", "").strip()
    scope = os.getenv("AZURE_API_SCOPE", f"api://{client_id}/access_as_user").strip()
    from urllib.parse import urlencode

    params = {
        "client_id": client_id,
        "response_type": "token",
        "redirect_uri": redirect_uri,
        "scope": f"openid profile email {scope}",
        "response_mode": "fragment",
        "state": state or "zect",
    }
    return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?{urlencode(params)}"
