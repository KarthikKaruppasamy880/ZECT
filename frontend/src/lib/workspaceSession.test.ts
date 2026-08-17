import { describe, expect, it, beforeEach } from "vitest";
import {
  WORKSPACE_SESSION_KEY,
  loadWorkspaceSession,
  newTerminalSession,
  saveWorkspaceSession,
} from "./workspaceSession";

describe("workspaceSession", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("persists editors and locked terminals without secrets", () => {
    const term = newTerminalSession(3, "C:/tmp/other", "local/other");
    saveWorkspaceSession({
      openEditors: [{ repoId: 1, path: "C:/tmp/zect/README.md" }],
      terminals: [term],
      activeTerminalId: term.id,
      workItemId: 9,
      projectId: 4,
      activeRepoId: 1,
    });
    const raw = localStorage.getItem(WORKSPACE_SESSION_KEY) || "";
    expect(raw).not.toMatch(/token|password|secret/i);
    const loaded = loadWorkspaceSession();
    expect(loaded.openEditors[0].repoId).toBe(1);
    expect(loaded.terminals[0].rootPath).toContain("other");
    expect(loaded.workItemId).toBe(9);
    expect(loaded.projectId).toBe(4);
    expect(loaded.activeRepoId).toBe(1);
  });
});
