import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useActiveProject } from "@/contexts/ActiveProjectContext";
import {
  attachProjectRepoById,
  cloneRepoFromUrl,
  createProject,
  discoverLocalRepos,
  getClonedRepos,
  registerLocalRepo,
} from "@/lib/api";
import { deriveProjectKey, writeMentrixWorkspace } from "@/lib/workspaceContext";
import { pickLocalFolder } from "@/lib/pickLocalFolder";
import { FolderOpen, GitBranch, Search, Link2, Loader2 } from "lucide-react";

type Mode = "idle" | "open" | "clone" | "discover" | "attach";

type Props = {
  /** When set, bind into this project; otherwise create/use selected project */
  projectId?: number | null;
  compact?: boolean;
  /** Where to go after bind; null = stay put (e.g. Developer Workspace) */
  navigateTo?: string | null;
  /** Called after a repo is registered/activated successfully */
  onActivated?: (info: { projectId: number; repoId: number; localPath?: string }) => void;
  /** Highlight Open Local as the primary action (Developer import flow) */
  preferOpenLocal?: boolean;
};

export default function RepoOnboardingPanel({
  projectId,
  compact,
  navigateTo,
  onActivated,
  preferOpenLocal,
}: Props) {
  const navigate = useNavigate();
  const { activeProjectId, setActiveProject, setActiveRepo, refresh } = useActiveProject();
  const boundProjectId = projectId ?? activeProjectId;

  const [mode, setMode] = useState<Mode>(preferOpenLocal ? "open" : "idle");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [localPath, setLocalPath] = useState("");
  const [gitUrl, setGitUrl] = useState("");
  const [destination, setDestination] = useState("");
  const [discoverRoot, setDiscoverRoot] = useState("");
  const [discovered, setDiscovered] = useState<any[]>([]);
  const [registered, setRegistered] = useState<any[]>([]);
  const [attachRepoId, setAttachRepoId] = useState("");

  async function ensureProject(): Promise<number> {
    if (boundProjectId) return boundProjectId;
    const p = await createProject({
      name: `Workspace ${new Date().toISOString().slice(0, 16)}`,
      description: "Auto-created for repository onboarding",
      team: "",
      current_stage: "ask",
      repos: [],
    } as Parameters<typeof createProject>[0]);
    setActiveProject(p.id);
    return p.id;
  }

  async function activateRepo(repoId: number, localPathForWs?: string, owner?: string, name?: string) {
    setActiveRepo(repoId);
    if (localPathForWs && owner && name) {
      writeMentrixWorkspace(localPathForWs, deriveProjectKey(owner, name));
    } else if (localPathForWs) {
      writeMentrixWorkspace(localPathForWs, deriveProjectKey(owner || "local", name || "repo"));
    }
    await refresh();
  }

  function finish(pid: number, repoId: number, local?: string) {
    onActivated?.({ projectId: pid, repoId, localPath: local });
    if (navigateTo === null) return;
    navigate(navigateTo ?? `/projects/${pid}`);
  }

  const runOpen = async () => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const pid = await ensureProject();
      const out = await registerLocalRepo(pid, localPath.trim());
      const id = out.identity || {};
      const lp = id.local_path || localPath.trim();
      await activateRepo(out.repo_id, lp, id.owner, id.name);
      setMessage(
        out.reused
          ? `Imported existing local clone #${out.repo_id} (no duplicate)`
          : `Imported local clone #${out.repo_id}`,
      );
      finish(pid, out.repo_id, lp);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Open local failed");
    } finally {
      setBusy(false);
    }
  };

  const runClone = async () => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const pid = await ensureProject();
      const out = await cloneRepoFromUrl(pid, gitUrl.trim(), destination.trim());
      await activateRepo(
        out.repo_id,
        out.local_path,
        out.identity?.owner,
        out.identity?.name,
      );
      setMessage(out.reused ? `Reused clone #${out.repo_id}` : `Cloned repo #${out.repo_id}`);
      finish(pid, out.repo_id, out.local_path);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Clone failed");
    } finally {
      setBusy(false);
    }
  };

  const runDiscover = async () => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const out = await discoverLocalRepos(discoverRoot.trim());
      setDiscovered(out.repos || []);
      setMessage(`Found ${out.count ?? 0} repositories under approved root`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Discover failed");
    } finally {
      setBusy(false);
    }
  };

  const attachDiscovered = async (item: any) => {
    setBusy(true);
    setError("");
    try {
      const pid = await ensureProject();
      if (item.registered && item.repo_id) {
        await attachProjectRepoById(pid, item.repo_id);
        await activateRepo(item.repo_id, item.local_path, item.owner, item.name);
        setMessage(`Attached registered repo #${item.repo_id}`);
        finish(pid, item.repo_id, item.local_path);
      } else {
        const out = await registerLocalRepo(pid, item.local_path);
        await activateRepo(out.repo_id, item.local_path, item.owner, item.name);
        setMessage(`Registered discovered repo #${out.repo_id}`);
        finish(pid, out.repo_id, item.local_path);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Attach failed");
    } finally {
      setBusy(false);
    }
  };

  const loadRegistered = async () => {
    setBusy(true);
    setError("");
    try {
      const list = await getClonedRepos();
      setRegistered(list || []);
      setMode("attach");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to list repos");
    } finally {
      setBusy(false);
    }
  };

  const runAttach = async () => {
    const rid = Number(attachRepoId);
    if (!Number.isFinite(rid) || rid <= 0) {
      setError("Enter a valid repo id");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const pid = await ensureProject();
      await attachProjectRepoById(pid, rid);
      const list = await getClonedRepos();
      const hit = list.find((r: any) => r.repo_id === rid);
      await activateRepo(rid, hit?.local_path, hit?.owner, hit?.repo_name);
      setMessage(`Attached repo #${rid} to project #${pid}`);
      finish(pid, rid, hit?.local_path);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Attach failed");
    } finally {
      setBusy(false);
    }
  };

  const actions = [
    {
      id: "open" as const,
      label: "Import Already-Cloned Local Repo",
      icon: FolderOpen,
      testId: "repo-onboard-open",
    },
    { id: "clone" as const, label: "Clone Remote Repository", icon: GitBranch, testId: "repo-onboard-clone" },
    { id: "discover" as const, label: "Discover Local Repositories", icon: Search, testId: "repo-onboard-discover" },
    { id: "attach" as const, label: "Attach Registered Repository", icon: Link2, testId: "repo-onboard-attach" },
  ];

  return (
    <div
      data-testid="repo-onboarding-panel"
      className={`bg-white rounded-xl border border-slate-200 ${compact ? "p-4" : "p-5"}`}
    >
      <div className="mb-3">
        <h2 className="text-sm font-semibold text-slate-800">
          {preferOpenLocal ? "Import local clone into Developer" : "Add Project / Repository"}
        </h2>
        <p className="text-xs text-slate-500 mt-0.5">
          {preferOpenLocal
            ? "Paste the path to a repo already on your Desktop (or elsewhere under allowed roots). ZECT binds it without re-cloning."
            : "Open local, clone URL, discover under an approved root, or attach an existing ZECT repo."}
        </p>
      </div>

      <div className={`grid gap-2 ${compact ? "grid-cols-1" : "sm:grid-cols-2"}`}>
        {actions.map((a) => {
          const Icon = a.icon;
          return (
            <button
              key={a.id}
              type="button"
              data-testid={a.testId}
              disabled={busy}
              onClick={() => {
                setError("");
                setMessage("");
                if (a.id === "attach") void loadRegistered();
                else setMode(a.id);
              }}
              className={`flex items-center gap-2 text-left px-3 py-2.5 rounded-lg border text-sm transition-colors ${
                mode === a.id
                  ? "border-indigo-300 bg-indigo-50 text-indigo-800"
                  : "border-slate-200 hover:bg-slate-50 text-slate-700"
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span>{a.label}</span>
            </button>
          );
        })}
      </div>

      {mode === "open" && (
        <div className="mt-4 space-y-2" data-testid="repo-onboard-open-form">
          <label className="block text-xs font-medium text-slate-600">
            Local Git folder (already cloned on Desktop / disk)
          </label>
          <div className="flex gap-2">
            <input
              data-testid="repo-onboard-local-path"
              value={localPath}
              onChange={(e) => setLocalPath(e.target.value)}
              placeholder="C:\\Users\\…\\Desktop\\my-repo"
              className="flex-1 border border-slate-200 rounded-lg px-3 py-2 text-sm"
            />
            <button
              type="button"
              data-testid="repo-onboard-browse"
              disabled={busy}
              onClick={() => {
                void (async () => {
                  setError("");
                  try {
                    const picked = await pickLocalFolder({
                      title: "Select already-cloned Git repository",
                    });
                    if (picked?.path) setLocalPath(picked.path);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "Folder picker unavailable");
                  }
                })();
              }}
              className="shrink-0 inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-slate-200 bg-white text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              <FolderOpen className="h-4 w-4" />
              Browse…
            </button>
          </div>
          <p className="text-[11px] text-slate-500">
            Prefer Browse in the ZECT Desktop app. In the browser you can still paste the full path.
          </p>
          <button
            type="button"
            data-testid="repo-onboard-open-submit"
            disabled={busy || !localPath.trim()}
            onClick={() => void runOpen()}
            className="inline-flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Import & Activate in Developer
          </button>
        </div>
      )}

      {mode === "clone" && (
        <div className="mt-4 space-y-2" data-testid="repo-onboard-clone-form">
          <label className="block text-xs font-medium text-slate-600">Git URL</label>
          <input
            data-testid="repo-onboard-git-url"
            value={gitUrl}
            onChange={(e) => setGitUrl(e.target.value)}
            placeholder="https://github.com/org/repo.git"
            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
          />
          <label className="block text-xs font-medium text-slate-600">Destination (optional, under approved roots)</label>
          <input
            data-testid="repo-onboard-destination"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            placeholder="Leave empty for ZECT workspace default"
            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
          />
          <button
            type="button"
            data-testid="repo-onboard-clone-submit"
            disabled={busy || !gitUrl.trim()}
            onClick={() => void runClone()}
            className="inline-flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Clone & Activate
          </button>
        </div>
      )}

      {mode === "discover" && (
        <div className="mt-4 space-y-2" data-testid="repo-onboard-discover-form">
          <label className="block text-xs font-medium text-slate-600">Approved root to scan</label>
          <div className="flex gap-2">
            <input
              data-testid="repo-onboard-discover-root"
              value={discoverRoot}
              onChange={(e) => setDiscoverRoot(e.target.value)}
              placeholder="Folder you explicitly approve"
              className="flex-1 border border-slate-200 rounded-lg px-3 py-2 text-sm"
            />
            <button
              type="button"
              data-testid="repo-onboard-discover-browse"
              disabled={busy}
              onClick={() => {
                void (async () => {
                  setError("");
                  try {
                    const picked = await pickLocalFolder({ title: "Choose folder to scan for Git repos" });
                    if (picked?.path) setDiscoverRoot(picked.path);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "Folder picker unavailable");
                  }
                })();
              }}
              className="shrink-0 inline-flex items-center gap-1 px-3 py-2 rounded-lg border border-slate-200 text-sm"
            >
              Browse…
            </button>
          </div>
          <button
            type="button"
            data-testid="repo-onboard-discover-submit"
            disabled={busy || !discoverRoot.trim()}
            onClick={() => void runDiscover()}
            className="inline-flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Discover
          </button>
          {discovered.length > 0 && (
            <ul className="mt-2 divide-y divide-slate-100 border border-slate-200 rounded-lg max-h-56 overflow-y-auto">
              {discovered.map((d) => (
                <li key={d.local_path} className="p-3 text-sm flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-medium truncate">{d.name}</p>
                    <p className="text-xs text-slate-500 truncate">{d.local_path}</p>
                    <p className="text-xs text-slate-500">
                      {d.branch} · {d.dirty ? "dirty" : "clean"}
                      {d.registered ? " · registered" : ""}
                    </p>
                  </div>
                  <button
                    type="button"
                    data-testid={`repo-onboard-discover-attach-${d.name}`}
                    disabled={busy}
                    onClick={() => void attachDiscovered(d)}
                    className="shrink-0 text-xs px-2 py-1 rounded border border-slate-200 hover:bg-slate-50"
                  >
                    Attach
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {mode === "attach" && (
        <div className="mt-4 space-y-2" data-testid="repo-onboard-attach-form">
          <label className="block text-xs font-medium text-slate-600">Registered repo id</label>
          <input
            data-testid="repo-onboard-attach-id"
            value={attachRepoId}
            onChange={(e) => setAttachRepoId(e.target.value)}
            placeholder="e.g. 12"
            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
          />
          {registered.length > 0 && (
            <select
              data-testid="repo-onboard-attach-select"
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
              value={attachRepoId}
              onChange={(e) => setAttachRepoId(e.target.value)}
            >
              <option value="">Select registered repo…</option>
              {registered.map((r) => (
                <option key={r.repo_id} value={String(r.repo_id)}>
                  #{r.repo_id} {r.owner}/{r.repo_name}
                </option>
              ))}
            </select>
          )}
          <button
            type="button"
            data-testid="repo-onboard-attach-submit"
            disabled={busy || !attachRepoId}
            onClick={() => void runAttach()}
            className="inline-flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Attach to Project
          </button>
        </div>
      )}

      {error && (
        <p data-testid="repo-onboard-error" className="mt-3 text-sm text-red-600">
          {error}
        </p>
      )}
      {message && (
        <p data-testid="repo-onboard-message" className="mt-3 text-sm text-emerald-700">
          {message}
        </p>
      )}
    </div>
  );
}
