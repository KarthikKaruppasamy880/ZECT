/** Client-side feature flags (localStorage + optional Vite env override). */

const AGENT_MODE_KEY = "zect_feature_agent_mode";

/** Env force-on: VITE_ENABLE_AGENT_MODE=true. Force-off: =false. Else localStorage. */
export function isAgentModeEnabled(): boolean {
  const env = (import.meta.env.VITE_ENABLE_AGENT_MODE as string | undefined)?.trim().toLowerCase();
  if (env === "true" || env === "1") return true;
  if (env === "false" || env === "0") return false;
  try {
    return localStorage.getItem(AGENT_MODE_KEY) === "1";
  } catch {
    return false;
  }
}

export function setAgentModeEnabled(enabled: boolean): void {
  try {
    if (enabled) localStorage.setItem(AGENT_MODE_KEY, "1");
    else localStorage.removeItem(AGENT_MODE_KEY);
  } catch {
    /* ignore quota */
  }
  window.dispatchEvent(new CustomEvent("zect-feature-flags"));
}

export function agentModeEnvLocked(): boolean {
  const env = (import.meta.env.VITE_ENABLE_AGENT_MODE as string | undefined)?.trim().toLowerCase();
  return env === "true" || env === "1" || env === "false" || env === "0";
}
