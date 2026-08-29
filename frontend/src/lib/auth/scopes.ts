/** Azure AD / Entra scopes for Mentrix SSO (OIDC mode). */
export const ZECT_API_SCOPE =
  import.meta.env.VITE_AZURE_API_SCOPE || "api://zect/.default";

export const DEFAULT_LOGIN_SCOPES = ["openid", "profile", "email", ZECT_API_SCOPE];
