import { describe, expect, it, beforeEach } from "vitest";
import {
  WORKSPACE_SESSION_KEY,
  closeEditorTab,
  editorTabLabel,
  loadWorkspaceSession,
  newTerminalSession,
  saveWorkspaceSession,
  upsertEditorTab,
  closeTerminalSession,
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

  it("upserts editor tabs without reordering existing ones", () => {
    const first = upsertEditorTab([], { repoId: 1, path: "C:/tmp/a.ts" });
    const two = upsertEditorTab(first, { repoId: 1, path: "C:/tmp/b.ts" });
    expect(two.map((t) => t.path)).toEqual(["C:/tmp/a.ts", "C:/tmp/b.ts"]);
    const again = upsertEditorTab(two, { repoId: 1, path: "C:/tmp/a.ts" });
    expect(again.map((t) => t.path)).toEqual(["C:/tmp/a.ts", "C:/tmp/b.ts"]);
    expect(closeEditorTab(again, "C:/tmp/a.ts")).toEqual([{ repoId: 1, path: "C:/tmp/b.ts" }]);
    expect(editorTabLabel("C:\\\\tmp\\\\zoas\\\\page.tsx")).toBe("page.tsx");
  });

  it("closes a locked terminal session without dropping the others", () => {
    const a = newTerminalSession(1, "C:/tmp/a", "a");
    const b = newTerminalSession(2, "C:/tmp/b", "b");
    expect(closeTerminalSession([a, b], a.id).map((t) => t.id)).toEqual([b.id]);
    expect(closeTerminalSession([a], a.id)).toEqual([]);
  });
});
