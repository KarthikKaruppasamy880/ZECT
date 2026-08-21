import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ChevronDown, ChevronRight, FolderPlus, GitBranch, RefreshCw, X } from "lucide-react";
import { getRepoIdentity, latticeIngest, latticeStatus, type RepoIdentity } from "@/lib/api";
import { canonicalLatticeState, latticeHeaderLabel, type LatticeState } from "@/lib/contextUsed";
import { deriveProjectKey } from "@/lib/workspaceContext";

export type WorkspaceRootRepo = {
  repo_id: number;
  project_id: number;
  owner: string;
  repo_name: string;
  local_path: string | null;
  clone_branch: string | null;
};

type RootRow = {
  repoId: number;
  label: string;
  branch: string;
  dirty: boolean;
  remote: string;
  lattice: LatticeState;
  liveSha: string;
  indexedSha: string;
  latticeAction: string;
  latticeActionLabel: string;
  projectKey: string;
  localPath: string;
  rootState: "READY" | "ROOT_UNAVAILABLE";
  detail: string;
};

type Props = {
  projectId: number | null;
  repos: WorkspaceRootRepo[];
  activeRepoId: number | null;
  onSelectRoot: (repoId: number) => void;
  onRemoveRoot: (repoId: number) => void;
  onAddRoot: () => void;
  onRepairRoot?: (repoId: number) => void;
  fileTree?: (repoId: number) => ReactNode;
};

function emptyRow(repo: WorkspaceRootRepo): RootRow {
  const missing = !repo.local_path;
  return {
    repoId: repo.repo_id,
    label: `${repo.owner}/${repo.repo_name}`,
    branch: repo.clone_branch || "—",
    dirty: false,
    remote: "",
    lattice: "NOT_APPLICABLE",
    liveSha: "",
    indexedSha: "",
    latticeAction: "",
    latticeActionLabel: "",
    projectKey: deriveProjectKey(repo.owner, repo.repo_name),
    localPath: repo.local_path || "",
    rootState: missing ? "ROOT_UNAVAILABLE" : "READY",
    detail: missing ? "Missing local path" : "",
  };
}

function shortSha(sha: string): string {
  return sha ? sha.slice(0, 7) : "—";
}

export default function WorkspaceRootsRail({
  projectId,
  repos,
  activeRepoId,
  onSelectRoot,
  onRemoveRoot,
  onAddRoot,
  onRepairRoot,
  fileTree,
}: Props) {
  const [rows, setRows] = useState<RootRow[]>(() => repos.map(emptyRow));
  const reposRef = useRef(repos);
  reposRef.current = repos;
  const catalogKey = useMemo(
    () => repos.map((r) => `${r.repo_id}:${r.owner}/${r.repo_name}:${r.local_path || ""}`).join("|"),
    [repos],
  );

  const [indexingId, setIndexingId] = useState<number | null>(null);
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set());
  const loadGen = useRef(0);
  const loadRows = useCallback(async () => {
    const current = reposRef.current;
    const gen = ++loadGen.current;
    if (!current.length) {
      setRows([]);
      return;
    }
    if (typeof localStorage !== "undefined" && !localStorage.getItem("zect_token")) {
      setRows(current.map(emptyRow));
      return;
    }
    const next = await Promise.all(
      current.map(async (repo) => {
        const base = emptyRow(repo);
        try {
          const ident: RepoIdentity = await getRepoIdentity(repo.repo_id);
          const unavailable =
            ident.root_state === "ROOT_UNAVAILABLE" || ident.cloned === false;
          base.rootState = unavailable ? "ROOT_UNAVAILABLE" : "READY";
          base.branch = ident.branch || base.branch;
          base.dirty = Boolean(ident.dirty);
          base.remote = String(ident.origin_url || "");
          base.detail = unavailable ? String(ident.error || "ROOT_UNAVAILABLE") : "";
        } catch {
          base.rootState = "ROOT_UNAVAILABLE";
          base.detail = "identity_failed";
        }
        try {
          const key = deriveProjectKey(repo.owner, repo.repo_name);
          const lat = await latticeStatus(key, repo.repo_id);
          base.lattice = canonicalLatticeState(lat.state || (lat.indexed ? "READY" : "NOT_INDEXED"));
          base.liveSha = String(lat.live_commit_sha || "");
          base.indexedSha = String(lat.indexed_commit_sha || "");
          base.latticeAction = String(lat.action || "");
          base.latticeActionLabel = String(lat.action_label || "");
          base.projectKey = lat.project_key || key;
        } catch {
          base.lattice = "ERROR";
          base.latticeAction = "reindex";
          base.latticeActionLabel = "Re-index repository";
        }
        return base;
      }),
    );
    if (gen !== loadGen.current) return;
    setRows(next);
  }, [catalogKey]);

  useEffect(() => {
    void loadRows();
  }, [loadRows]);

  return (
    <section
      className="flex min-h-0 flex-1 flex-col overflow-hidden border-b border-slate-100 bg-slate-50/80"
      data-testid="workspace-roots-rail"
    >
      <div className="flex shrink-0 items-center justify-between gap-2 px-2 py-1.5">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">WORKSPACE</p>
        <div className="flex items-center gap-1">
          <button
            type="button"
            className="rounded border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] text-slate-600"
            data-testid="workspace-roots-refresh"
            onClick={() => void loadRows()}
            title="Refresh root identity"
          >
            <RefreshCw className="h-3 w-3" />
          </button>
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded border border-indigo-200 bg-indigo-50 px-1.5 py-0.5 text-[10px] font-medium text-indigo-800"
            data-testid="workspace-add-root"
            onClick={onAddRoot}
            title="Register a local project folder — not a Cursor untitled workspace"
          >
            <FolderPlus className="h-3 w-3" />
            Add
          </button>
        </div>
      </div>
      {!projectId ? (
        <p className="px-2 pb-2 text-[11px] text-slate-500">Select a project to attach authorized roots.</p>
      ) : !repos.length ? (
        <p className="px-2 pb-2 text-[11px] text-slate-500" data-testid="workspace-roots-empty">
          No authorized roots. Add registers a Project local folder — not a Cursor untitled workspace.
        </p>
      ) : (
        <div
          className="h-0 min-h-0 flex-1 overflow-y-scroll overscroll-contain pb-1"
          data-testid="workspace-explorer-scroll"
        >
        <ul className="m-0 list-none p-0">
          {rows.map((row) => {
            const active = Number(row.repoId) === Number(activeRepoId);
            const unavailable = row.rootState === "ROOT_UNAVAILABLE";
            const isCollapsed = collapsed.has(row.repoId);
            return (
              <li
                key={row.repoId}
                data-testid={`workspace-root-${row.repoId}`}
                data-active={active ? "true" : "false"}
                data-collapsed={isCollapsed ? "true" : "false"}
                aria-current={active ? "true" : undefined}
              >
                <div
                  className={`flex items-start gap-1 px-2 py-1.5 ${
                    active ? "bg-teal-50" : "hover:bg-white"
                  }`}
                >
                  <button
                    type="button"
                    className="mt-0.5 shrink-0 rounded p-0.5 text-slate-500 hover:bg-white"
                    data-testid={`workspace-root-collapse-${row.repoId}`}
                    aria-expanded={!isCollapsed}
                    title={isCollapsed ? "Expand folder" : "Collapse folder"}
                    onClick={() => {
                      setCollapsed((prev) => {
                        const next = new Set(prev);
                        if (next.has(row.repoId)) next.delete(row.repoId);
                        else next.add(row.repoId);
                        return next;
                      });
                    }}
                  >
                    {isCollapsed ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                  </button>
                  <button
                    type="button"
                    className="min-w-0 flex-1 text-left"
                    data-testid={`workspace-root-select-${row.repoId}`}
                    onClick={() => onSelectRoot(Number(row.repoId))}
                    title={row.remote || row.detail || row.label}
                  >
                    <span className="block truncate text-xs font-medium text-slate-800">{row.label}</span>
                    <span className="mt-0.5 flex flex-wrap items-center gap-1 text-[10px] text-slate-500">
                      <span className="inline-flex items-center gap-0.5">
                        <GitBranch className="h-2.5 w-2.5" />
                        {row.branch}
                      </span>
                      <span>{row.dirty ? "dirty" : "clean"}</span>
                      <span data-testid={`workspace-root-lattice-${row.repoId}`}>{latticeHeaderLabel(row.lattice)}</span>
                      <span
                        className="font-mono text-slate-400"
                        data-testid={`workspace-root-sha-${row.repoId}`}
                        data-live-sha={row.liveSha || ""}
                        data-indexed-sha={row.indexedSha || ""}
                        data-lattice-state={row.lattice}
                        title={`live=${row.liveSha || "—"} indexed=${row.indexedSha || "—"}`}
                      >
                        head {shortSha(row.liveSha)} · idx {shortSha(row.indexedSha)}
                      </span>
                      <span className="text-slate-400">authorized</span>
                    </span>
                    {unavailable ? (
                      <span
                        className="mt-0.5 inline-block rounded bg-amber-100 px-1 py-0.5 text-[10px] font-semibold uppercase text-amber-900"
                        data-testid={`workspace-root-unavailable-${row.repoId}`}
                      >
                        ROOT_UNAVAILABLE
                      </span>
                    ) : null}
                  </button>
                  {!unavailable ? (
                    <span className="flex shrink-0 flex-col items-end gap-0.5">
                      {row.latticeAction === "index_repository" ||
                      row.latticeAction === "reindex" ||
                      row.latticeAction === "clone_or_index" ? (
                        <button
                          type="button"
                          className="rounded border border-teal-200 bg-teal-50 px-1 py-0.5 text-[10px] text-teal-900 disabled:opacity-40"
                          data-testid={`workspace-root-index-${row.repoId}`}
                          disabled={indexingId === row.repoId || !row.localPath}
                          onClick={async () => {
                            if (!row.localPath) return;
                            setIndexingId(row.repoId);
                            try {
                              await latticeIngest(row.localPath, row.projectKey, true);
                              await loadRows();
                            } finally {
                              setIndexingId(null);
                            }
                          }}
                        >
                          {indexingId === row.repoId
                            ? "Indexing…"
                            : row.latticeAction === "reindex"
                              ? "Re-index"
                              : "Index"}
                        </button>
                      ) : null}
                      {row.latticeAction === "view_intelligence" || row.lattice === "READY" || row.lattice === "STALE" ? (
                        <a
                          href={`/lattice?project_key=${encodeURIComponent(row.projectKey)}`}
                          className="rounded border border-slate-200 bg-white px-1 py-0.5 text-[10px] text-slate-700"
                          data-testid={`workspace-root-view-lattice-${row.repoId}`}
                        >
                          View
                        </a>
                      ) : null}
                      {row.lattice === "ERROR" ? (
                        <span className="text-[10px] text-rose-700" data-testid={`workspace-root-lattice-error-${row.repoId}`}>
                          Error
                        </span>
                      ) : null}
                    </span>
                  ) : null}
                  {unavailable && onRepairRoot ? (
                    <button
                      type="button"
                      className="shrink-0 rounded border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-[10px] text-amber-900"
                      data-testid={`workspace-root-repair-${row.repoId}`}
                      onClick={() => onRepairRoot(row.repoId)}
                    >
                      Repair
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className="shrink-0 rounded border border-slate-200 bg-white p-0.5 text-slate-500 hover:text-rose-700"
                    data-testid={`workspace-root-remove-${row.repoId}`}
                    title="Remove from workspace (does not delete disk)"
                    onClick={() => onRemoveRoot(row.repoId)}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
                {!unavailable && !isCollapsed && fileTree ? (
                  <div data-testid={`workspace-root-tree-${row.repoId}`}>{fileTree(row.repoId)}</div>
                ) : null}
              </li>
            );
          })}
        </ul>
        </div>
      )}
    </section>
  );
}
