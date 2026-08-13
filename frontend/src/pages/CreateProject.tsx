import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  attachProjectRepoById,
  cloneRepoFromUrl,
  createProject,
  getClonedRepos,
  registerLocalRepo,
} from "@/lib/api";
import { useActiveProject } from "@/contexts/ActiveProjectContext";
import { deriveProjectKey, writeMentrixWorkspace } from "@/lib/workspaceContext";
import { ArrowLeft, Wrench } from "lucide-react";

const ACTIVE_SKILL_KEY = "mentrix_active_skill_id";

type SetupMode = "empty" | "registered" | "local" | "clone" | "github_meta";

export default function CreateProject() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setActiveProject, setActiveRepo, refresh } = useActiveProject();
  const skillIdParam = searchParams.get("skill_id");
  const [name, setName] = useState(() => searchParams.get("name") || "");
  const [description, setDescription] = useState(() => searchParams.get("description") || "");
  const [team, setTeam] = useState("");
  const [setupMode, setSetupMode] = useState<SetupMode>("empty");
  const [repoOwner, setRepoOwner] = useState("");
  const [repoName, setRepoName] = useState("");
  const [localPath, setLocalPath] = useState("");
  const [gitUrl, setGitUrl] = useState("");
  const [destination, setDestination] = useState("");
  const [registeredRepos, setRegisteredRepos] = useState<any[]>([]);
  const [attachRepoId, setAttachRepoId] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (skillIdParam) {
      try {
        localStorage.setItem(ACTIVE_SKILL_KEY, skillIdParam);
      } catch {
        /* ignore */
      }
    }
  }, [skillIdParam]);

  useEffect(() => {
    if (setupMode === "registered") {
      getClonedRepos()
        .then(setRegisteredRepos)
        .catch(() => setRegisteredRepos([]));
    }
  }, [setupMode]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    setError("");
    try {
      const repos =
        setupMode === "github_meta" && repoOwner.trim() && repoName.trim()
          ? [{ owner: repoOwner.trim(), repo_name: repoName.trim(), default_branch: "main" }]
          : [];
      const project = await createProject({
        name: name.trim(),
        description: description.trim(),
        team: team.trim(),
        current_stage: "ask",
        repos,
      } as Parameters<typeof createProject>[0]);

      setActiveProject(project.id);

      if (setupMode === "local" && localPath.trim()) {
        const out = await registerLocalRepo(project.id, localPath.trim());
        setActiveRepo(out.repo_id);
        const id = out.identity || {};
        if (id.local_path && id.owner && id.name) {
          writeMentrixWorkspace(id.local_path, deriveProjectKey(id.owner, id.name));
        }
      } else if (setupMode === "clone" && gitUrl.trim()) {
        const out = await cloneRepoFromUrl(project.id, gitUrl.trim(), destination.trim());
        setActiveRepo(out.repo_id);
        if (out.local_path && out.identity?.owner && out.identity?.name) {
          writeMentrixWorkspace(
            out.local_path,
            deriveProjectKey(out.identity.owner, out.identity.name),
          );
        }
      } else if (setupMode === "registered" && attachRepoId) {
        const rid = Number(attachRepoId);
        await attachProjectRepoById(project.id, rid);
        setActiveRepo(rid);
        const hit = registeredRepos.find((r) => r.repo_id === rid);
        if (hit?.local_path) {
          writeMentrixWorkspace(hit.local_path, deriveProjectKey(hit.owner, hit.repo_name));
        }
      }

      if (skillIdParam) {
        try {
          localStorage.setItem(ACTIVE_SKILL_KEY, skillIdParam);
          localStorage.setItem("zect_active_skill_project_id", String(project.id));
        } catch {
          /* ignore */
        }
      }
      await refresh();
      navigate(`/projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
      setSaving(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-4"
      >
        <ArrowLeft className="h-4 w-4" /> Back
      </button>

      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h1 className="text-xl font-bold text-slate-900 mb-1">Create New Project</h1>
        <p className="text-sm text-slate-500 mb-6">
          Empty project, open local Git, clone URL, or attach a registered repository
        </p>

        {skillIdParam && (
          <div className="mb-5 flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
            <Wrench className="h-4 w-4 mt-0.5 shrink-0" />
            <p>
              Scaffolded from Skills Engine (skill #{skillIdParam}). Mentrix will treat this skill as
              active for the new project.
            </p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5" data-testid="create-project-form">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Project Name *</label>
            <input
              data-testid="create-project-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="e.g. Policy Admin Modernization"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="Brief description of the project"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Team</label>
            <input
              type="text"
              value={team}
              onChange={(e) => setTeam(e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="e.g. Platform Engineering"
            />
          </div>

          <div className="border-t border-slate-100 pt-5 space-y-3">
            <p className="text-sm font-medium text-slate-700">Repository setup</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {(
                [
                  ["empty", "Create Empty Project"],
                  ["registered", "Use Existing Registered Repository"],
                  ["local", "Open Existing Local Repository"],
                  ["clone", "Clone Remote Repository"],
                  ["github_meta", "Link GitHub owner/name only"],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  data-testid={`create-setup-${id}`}
                  onClick={() => setSetupMode(id)}
                  className={`text-left text-sm px-3 py-2 rounded-lg border ${
                    setupMode === id
                      ? "border-indigo-300 bg-indigo-50 text-indigo-800"
                      : "border-slate-200 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            {setupMode === "github_meta" && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-500 mb-1">Owner</label>
                  <input
                    type="text"
                    value={repoOwner}
                    onChange={(e) => setRepoOwner(e.target.value)}
                    className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
                    placeholder="e.g. org-or-user"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-500 mb-1">Repository</label>
                  <input
                    type="text"
                    value={repoName}
                    onChange={(e) => setRepoName(e.target.value)}
                    className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
                    placeholder="e.g. my-service"
                  />
                </div>
              </div>
            )}

            {setupMode === "local" && (
              <input
                data-testid="create-local-path"
                value={localPath}
                onChange={(e) => setLocalPath(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
                placeholder="Local Git folder path"
              />
            )}

            {setupMode === "clone" && (
              <div className="space-y-2">
                <input
                  data-testid="create-git-url"
                  value={gitUrl}
                  onChange={(e) => setGitUrl(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
                  placeholder="https://github.com/org/repo.git"
                />
                <input
                  data-testid="create-destination"
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
                  placeholder="Optional destination under approved roots"
                />
              </div>
            )}

            {setupMode === "registered" && (
              <select
                data-testid="create-attach-repo"
                value={attachRepoId}
                onChange={(e) => setAttachRepoId(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
              >
                <option value="">Select registered repo…</option>
                {registeredRepos.map((r) => (
                  <option key={r.repo_id} value={String(r.repo_id)}>
                    #{r.repo_id} {r.owner}/{r.repo_name}
                  </option>
                ))}
              </select>
            )}
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              data-testid="create-project-submit"
              disabled={saving || !name.trim()}
              className="bg-indigo-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50"
            >
              {saving ? "Creating..." : "Create Project"}
            </button>
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="border border-slate-200 text-slate-600 px-6 py-2 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
