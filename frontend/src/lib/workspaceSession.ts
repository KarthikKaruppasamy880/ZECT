/** Persist safe Developer Workspace session — never stores tokens or secrets. */

export const WORKSPACE_SESSION_KEY = "zect_ws_session";

export type WorkspaceEditorTab = {
  repoId: number;
  path: string;
};

export type WorkspaceTerminalSession = {
  id: string;
  repoId: number;
  rootPath: string;
  label: string;
};

export type WorkspaceSession = {
  openEditors: WorkspaceEditorTab[];
  terminals: WorkspaceTerminalSession[];
  activeTerminalId: string | null;
  workItemId: number | null;
  projectId: number | null;
  activeRepoId: number | null;
  /** Server-side Mission id, so a reload or a tab switch re-attaches to a
   *  running Mission instead of showing an empty start form (finding F4). */
  codingMissionId: string | null;
};

function emptySession(): WorkspaceSession {
  return {
    openEditors: [],
    terminals: [],
    activeTerminalId: null,
    workItemId: null,
    projectId: null,
    activeRepoId: null,
    codingMissionId: null,
  };
}

export function loadWorkspaceSession(): WorkspaceSession {
  try {
    const raw = JSON.parse(localStorage.getItem(WORKSPACE_SESSION_KEY) || "{}") as Record<string, unknown>;
    const openEditors = Array.isArray(raw.openEditors)
      ? raw.openEditors
          .map((row) => {
            const r = row as Record<string, unknown>;
            const repoId = Number(r.repoId);
            const path = String(r.path || "");
            if (!Number.isFinite(repoId) || repoId <= 0 || !path) return null;
            return { repoId, path };
          })
          .filter((x): x is WorkspaceEditorTab => Boolean(x))
      : [];
    const terminals = Array.isArray(raw.terminals)
      ? raw.terminals
          .map((row) => {
            const r = row as Record<string, unknown>;
            const id = String(r.id || "");
            const repoId = Number(r.repoId);
            const rootPath = String(r.rootPath || "");
            const label = String(r.label || "");
            if (!id || !Number.isFinite(repoId) || !rootPath) return null;
            return { id, repoId, rootPath, label };
          })
          .filter((x): x is WorkspaceTerminalSession => Boolean(x))
      : [];
    return {
      openEditors,
      terminals,
      activeTerminalId: typeof raw.activeTerminalId === "string" ? raw.activeTerminalId : terminals[0]?.id || null,
      workItemId: typeof raw.workItemId === "number" && raw.workItemId > 0 ? raw.workItemId : null,
      projectId: typeof raw.projectId === "number" && raw.projectId > 0 ? raw.projectId : null,
      activeRepoId: typeof raw.activeRepoId === "number" && raw.activeRepoId > 0 ? raw.activeRepoId : null,
      codingMissionId:
        typeof raw.codingMissionId === "string" && raw.codingMissionId.trim() ? raw.codingMissionId.trim() : null,
    };
  } catch {
    return emptySession();
  }
}

export function saveWorkspaceSession(session: WorkspaceSession): void {
  try {
    localStorage.setItem(
      WORKSPACE_SESSION_KEY,
      JSON.stringify({
        openEditors: session.openEditors.slice(0, 12),
        terminals: session.terminals.slice(0, 8),
        activeTerminalId: session.activeTerminalId,
        workItemId: session.workItemId,
        projectId: session.projectId,
        activeRepoId: session.activeRepoId,
        codingMissionId: session.codingMissionId,
      }),
    );
  } catch {
    /* ignore quota */
  }
}

/** CP-09 -- a WorkItem/Mission id persisted in localStorage that no longer
 *  resolves on the backend (deleted, or a different backend/DB entirely --
 *  e.g. after `ZECT_USER_DATA`/`ZECT_CODING_MISSIONS_DIR` changes) must not
 *  keep poisoning every future ASK/PLAN/AGENT interaction by being silently
 *  re-offered on every mount. Callers reconcile a confirmed 404 by writing
 *  the result back through `setWsSession`, not by only clearing local
 *  component state (which is what left the stale id in localStorage
 *  indefinitely before this fix).
 *
 *  Clearing workItemId cascades to codingMissionId: a Mission belongs to
 *  exactly one WorkItem (WorkItem.coding_mission_id is the durable
 *  pointer), so a dead WorkItem's mission id is equally meaningless.
 *  Clearing a Mission on its own (its WorkItem is still perfectly valid)
 *  must not touch workItemId. */
export function withoutWorkItem(session: WorkspaceSession): WorkspaceSession {
  return { ...session, workItemId: null, codingMissionId: null };
}

export function withoutMission(session: WorkspaceSession): WorkspaceSession {
  return { ...session, codingMissionId: null };
}

export function editorTabLabel(path: string): string {
  const norm = (path || "").replace(/\\/g, "/");
  return norm.split("/").filter(Boolean).pop() || path || "untitled";
}

export function upsertEditorTab(
  tabs: WorkspaceEditorTab[],
  tab: WorkspaceEditorTab,
  limit = 12,
): WorkspaceEditorTab[] {
  if (!tab?.path || !Number.isFinite(tab.repoId) || tab.repoId <= 0) return tabs;
  const exists = tabs.some((t) => t.path === tab.path);
  if (exists) {
    return tabs.map((t) => (t.path === tab.path ? tab : t));
  }
  const next = [...tabs, tab];
  return next.length > limit ? next.slice(next.length - limit) : next;
}

export function closeEditorTab(tabs: WorkspaceEditorTab[], path: string): WorkspaceEditorTab[] {
  return tabs.filter((t) => t.path !== path);
}

export function closeTerminalSession(
  terminals: WorkspaceTerminalSession[],
  id: string,
): WorkspaceTerminalSession[] {
  return terminals.filter((t) => t.id !== id);
}

export function newTerminalSession(repoId: number, rootPath: string, label: string): WorkspaceTerminalSession {
  const id =
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `term-${Date.now()}-${repoId}`;
  return { id, repoId, rootPath, label };
}
