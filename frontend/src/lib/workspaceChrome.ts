/** Persist Developer Workspace chrome: pane visibility, maximize, bottom tab. */

export type WorkspaceMaximized = "explorer" | "editor" | "agent" | "bottom" | null;
export type WorkspaceBottomTab = "terminal" | "timeline" | "context";

export type WorkspaceChrome = {
  explorer: boolean;
  agent: boolean;
  bottom: boolean;
  context: boolean;
  maximized: WorkspaceMaximized;
  bottomTab: WorkspaceBottomTab;
};

export const WORKSPACE_CHROME_KEY = "zect_ws_chrome";
export const WORKSPACE_SPLIT_KEYS = ["zect_ws_h", "zect_ws_agent", "zect_ws_v"] as const;

export const DEFAULT_WORKSPACE_CHROME: WorkspaceChrome = {
  explorer: true,
  agent: true,
  bottom: true,
  context: false,
  maximized: null,
  bottomTab: "terminal",
};

const MAXIMIZED: WorkspaceMaximized[] = ["explorer", "editor", "agent", "bottom"];
const TABS: WorkspaceBottomTab[] = ["terminal", "timeline", "context"];

export function loadWorkspaceChrome(): WorkspaceChrome {
  try {
    const raw = JSON.parse(localStorage.getItem(WORKSPACE_CHROME_KEY) || "{}") as Record<string, unknown>;
    const maximized = MAXIMIZED.includes(raw.maximized as WorkspaceMaximized)
      ? (raw.maximized as WorkspaceMaximized)
      : null;
    const bottomTab = TABS.includes(raw.bottomTab as WorkspaceBottomTab)
      ? (raw.bottomTab as WorkspaceBottomTab)
      : "terminal";
    return {
      explorer: raw.explorer !== false,
      agent: raw.agent !== false,
      bottom: raw.bottom !== false,
      context: Boolean(raw.context),
      maximized,
      bottomTab,
    };
  } catch {
    return { ...DEFAULT_WORKSPACE_CHROME };
  }
}

export function saveWorkspaceChrome(chrome: WorkspaceChrome): void {
  try {
    localStorage.setItem(WORKSPACE_CHROME_KEY, JSON.stringify(chrome));
  } catch {
    /* ignore */
  }
}

export function effectivePanes(chrome: WorkspaceChrome): {
  explorer: boolean;
  agent: boolean;
  bottom: boolean;
} {
  if (chrome.maximized === "editor") {
    return { explorer: false, agent: false, bottom: false };
  }
  if (chrome.maximized === "explorer") {
    return { explorer: true, agent: false, bottom: false };
  }
  if (chrome.maximized === "agent") {
    return { explorer: false, agent: true, bottom: false };
  }
  if (chrome.maximized === "bottom") {
    return { explorer: false, agent: false, bottom: true };
  }
  return {
    explorer: chrome.explorer,
    agent: chrome.agent,
    bottom: chrome.bottom,
  };
}
