/**
 * MSAL helpers for Azure AD / Entra OIDC.
 * Used when ZECT_AUTH_MODE is oidc or hybrid and VITE_AZURE_CLIENT_ID is set.
 */

import { DEFAULT_LOGIN_SCOPES } from "./scopes";

export type MsalConfig = {
  clientId: string;
  tenantId: string;
  redirectUri?: string;
};

export function isMsalConfigured(): boolean {
  return Boolean(
    import.meta.env.VITE_AZURE_CLIENT_ID && import.meta.env.VITE_AZURE_TENANT_ID
  );
}

export function getMsalConfig(): MsalConfig | null {
  const clientId = import.meta.env.VITE_AZURE_CLIENT_ID as string | undefined;
  const tenantId = import.meta.env.VITE_AZURE_TENANT_ID as string | undefined;
  if (!clientId || !tenantId) return null;
  return {
    clientId,
    tenantId,
    redirectUri: import.meta.env.VITE_AZURE_REDIRECT_URI || window.location.origin,
  };
}

/** Build authorize URL (PKCE-ready shell; backend also exposes /api/auth/oidc/login-url). */
export function buildAuthorizeUrl(loginHint?: string): string | null {
  const cfg = getMsalConfig();
  if (!cfg) return null;
  const params = new URLSearchParams({
    client_id: cfg.clientId,
    response_type: "token",
    redirect_uri: cfg.redirectUri || window.location.origin,
    scope: DEFAULT_LOGIN_SCOPES.join(" "),
    response_mode: "fragment",
  });
  if (loginHint) params.set("login_hint", loginHint);
  return `https://login.microsoftonline.com/${cfg.tenantId}/oauth2/v2.0/authorize?${params}`;
}

export async function exchangeOidcToken(accessToken: string): Promise<{ token: string }> {
  const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
  const res = await fetch(`${API}/api/auth/oidc/exchange`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ access_token: accessToken }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : "OIDC exchange failed");
  }
  return res.json();
}
