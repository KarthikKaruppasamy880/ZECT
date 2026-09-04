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
  withoutMission,
  withoutWorkItem,
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
      codingMissionId: null,
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

  // A Mission id is what lets the Developer pane re-attach after a reload
  // instead of offering to start a second Mission (finding F4).
  it("round-trips the coding mission id", () => {
    saveWorkspaceSession({
      openEditors: [],
      terminals: [],
      activeTerminalId: null,
      workItemId: null,
      projectId: null,
      activeRepoId: null,
      codingMissionId: "mission-abc",
    });
    expect(loadWorkspaceSession().codingMissionId).toBe("mission-abc");
  });

  it("ignores a blank or non-string mission id", () => {
    localStorage.setItem(WORKSPACE_SESSION_KEY, JSON.stringify({ codingMissionId: "   " }));
    expect(loadWorkspaceSession().codingMissionId).toBeNull();
    localStorage.setItem(WORKSPACE_SESSION_KEY, JSON.stringify({ codingMissionId: 42 }));
    expect(loadWorkspaceSession().codingMissionId).toBeNull();
  });

  it("defaults to null for a session saved before mission ids were persisted", () => {
    localStorage.setItem(WORKSPACE_SESSION_KEY, JSON.stringify({ workItemId: 3 }));
    const loaded = loadWorkspaceSession();
    expect(loaded.workItemId).toBe(3);
    expect(loaded.codingMissionId).toBeNull();
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

  // CP-09: a WorkItem/Mission id that 404s on the backend must not keep
  // being handed back in on every future mount.
  it("withoutWorkItem clears both workItemId and codingMissionId, other fields untouched", () => {
    const session = {
      openEditors: [{ repoId: 1, path: "a.ts" }],
      terminals: [],
      activeTerminalId: null,
      workItemId: 9,
      projectId: 4,
      activeRepoId: 1,
      codingMissionId: "mission-abc",
    };
    const next = withoutWorkItem(session);
    expect(next.workItemId).toBeNull();
    expect(next.codingMissionId).toBeNull();
    expect(next.projectId).toBe(4);
    expect(next.activeRepoId).toBe(1);
    expect(next.openEditors).toBe(session.openEditors);
  });

  it("withoutMission clears only codingMissionId -- a dead Mission does not imply a dead WorkItem", () => {
    const session = {
      openEditors: [],
      terminals: [],
      activeTerminalId: null,
      workItemId: 9,
      projectId: 4,
      activeRepoId: 1,
      codingMissionId: "mission-abc",
    };
    const next = withoutMission(session);
    expect(next.codingMissionId).toBeNull();
    expect(next.workItemId).toBe(9);
  });
});
