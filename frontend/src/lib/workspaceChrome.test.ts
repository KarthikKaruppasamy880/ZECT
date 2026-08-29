import { describe, expect, it, beforeEach } from "vitest";
import {
  DEFAULT_WORKSPACE_CHROME,
  WORKSPACE_CHROME_KEY,
  effectivePanes,
  loadWorkspaceChrome,
  saveWorkspaceChrome,
} from "./workspaceChrome";

describe("workspaceChrome", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("defaults to editor-adjacent explorer/agent/bottom with context off", () => {
    expect(loadWorkspaceChrome()).toEqual(DEFAULT_WORKSPACE_CHROME);
    expect(effectivePanes(DEFAULT_WORKSPACE_CHROME)).toEqual({
      explorer: true,
      agent: true,
      bottom: true,
    });
  });

  it("maximize editor hides chrome panes; restore uses stored flags", () => {
    const maximized = { ...DEFAULT_WORKSPACE_CHROME, maximized: "editor" as const };
    expect(effectivePanes(maximized)).toEqual({ explorer: false, agent: false, bottom: false });
    saveWorkspaceChrome({ ...DEFAULT_WORKSPACE_CHROME, explorer: false, maximized: "agent" });
    expect(localStorage.getItem(WORKSPACE_CHROME_KEY)).toContain("agent");
    expect(loadWorkspaceChrome().maximized).toBe("agent");
    expect(effectivePanes(loadWorkspaceChrome())).toEqual({
      explorer: false,
      agent: true,
      bottom: false,
    });
  });
});
