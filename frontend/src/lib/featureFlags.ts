/** Client-side feature flags (localStorage + optional Vite env override). */

const AGENT_MODE_KEY = "zect_feature_agent_mode";
const DEMO_MODE_KEY = "zect_feature_demo_mode";

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

/** Demo Mode: slim sidebar for team demos (Project → Workspace → Mentrix spine). */
export function isDemoModeEnabled(): boolean {
  const env = (import.meta.env.VITE_DEMO_MODE as string | undefined)?.trim().toLowerCase();
  if (env === "true" || env === "1") return true;
  if (env === "false" || env === "0") return false;
  try {
    return localStorage.getItem(DEMO_MODE_KEY) === "1";
  } catch {
    return false;
  }
}

export function setDemoModeEnabled(enabled: boolean): void {
  try {
    if (enabled) localStorage.setItem(DEMO_MODE_KEY, "1");
    else localStorage.removeItem(DEMO_MODE_KEY);
  } catch {
    /* ignore */
  }
  window.dispatchEvent(new CustomEvent("zect-feature-flags"));
}

export function demoModeEnvLocked(): boolean {
  const env = (import.meta.env.VITE_DEMO_MODE as string | undefined)?.trim().toLowerCase();
  return env === "true" || env === "1" || env === "false" || env === "0";
}
