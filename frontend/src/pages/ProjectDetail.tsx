import { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getProject,
  getGitHubPulls,
  getGitHubCommits,
  getGitHubWorkflowRuns,
  getClonedRepos,
  openPrWorktree,
} from "@/lib/api";
import { useActiveProject } from "@/contexts/ActiveProjectContext";
import RepoOnboardingPanel from "@/components/RepoOnboardingPanel";
import { deriveProjectKey, writeMentrixWorkspace } from "@/lib/workspaceContext";
import type { Project, GitHubPR, GitHubCommit, GitHubWorkflowRun } from "@/types";
import { STAGES } from "@/types";
import {
  ArrowLeft,
  GitBranch,
  GitPullRequest,
  GitCommit,
  CheckCircle2,
  XCircle,
  Clock,
  ExternalLink,
  Loader2,
} from "lucide-react";

function ciIcon(conclusion: string | null) {
  switch (conclusion) {
    case "success":
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    case "failure":
      return <XCircle className="h-4 w-4 text-red-500" />;
    default:
      return <Clock className="h-4 w-4 text-yellow-500" />;
  }
}

function relativeTime(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const { activeBranch, activeRepo, setActiveRepo, setActiveProject, refresh } = useActiveProject();
  const [project, setProject] = useState<Project | null>(null);
  const [pulls, setPulls] = useState<GitHubPR[]>([]);
  const [commits, setCommits] = useState<GitHubCommit[]>([]);
  const [runs, setRuns] = useState<GitHubWorkflowRun[]>([]);
  const [cloned, setCloned] = useState<any[]>([]);
  const [selectedRepoIdx, setSelectedRepoIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"overview" | "prs" | "commits" | "ci">("overview");
  const [wtBusy, setWtBusy] = useState<number | null>(null);
  const [wtMessage, setWtMessage] = useState("");
  const [wtError, setWtError] = useState("");
  const [prNumberInput, setPrNumberInput] = useState("");
  const [prHeadInput, setPrHeadInput] = useState("");

  useEffect(() => {
    if (!id) return;
    const pid = Number(id);
    setActiveProject(pid);
    getProject(pid)
      .then(async (p) => {
        setProject(p);
        const list = await getClonedRepos().catch(() => []);
        setCloned(list);
        if (p.repos.length > 0) {
          setSelectedRepoIdx(0);
        }
      })
      .finally(() => setLoading(false));
  }, [id, setActiveProject]);

  const selectedRepo = project?.repos[selectedRepoIdx] || null;

  const clonedMatch = useMemo(() => {
    if (!selectedRepo) return null;
    return (
      cloned.find(
        (c) => c.owner === selectedRepo.owner && c.repo_name === selectedRepo.repo_name,
      ) || null
    );
  }, [cloned, selectedRepo]);

  useEffect(() => {
    if (!selectedRepo) {
      setPulls([]);
      setCommits([]);
      setRuns([]);
      return;
    }
    Promise.all([
      getGitHubPulls(selectedRepo.owner, selectedRepo.repo_name).catch(() => []),
      getGitHubCommits(selectedRepo.owner, selectedRepo.repo_name).catch(() => []),
      getGitHubWorkflowRuns(selectedRepo.owner, selectedRepo.repo_name).catch(() => []),
    ]).then(([prs, cs, rs]) => {
      setPulls(prs);
      setCommits(cs);
      setRuns(rs);
    });
  }, [selectedRepo?.id, selectedRepo?.owner, selectedRepo?.repo_name]);

  const openWorktree = async (pr: GitHubPR) => {
    const repoId = clonedMatch?.repo_id || selectedRepo?.id;
    if (!repoId) {
      setWtError("Clone or register this repository locally first");
      return;
    }
    setWtBusy(pr.number);
    setWtError("");
    setWtMessage("");
    try {
      const out = await openPrWorktree(repoId, pr.number, pr.head_branch);
      setActiveRepo(repoId);
      writeMentrixWorkspace(
        out.worktree_path,
        deriveProjectKey(selectedRepo!.owner, selectedRepo!.repo_name),
      );
      await refresh();
      setWtMessage(
        `PR #${pr.number} worktree ${out.reused ? "reused" : "created"} at ${out.worktree_path} (branch ${out.branch}, HEAD ${(out.head_sha || "").slice(0, 12)})`,
      );
    } catch (e) {
      setWtError(e instanceof Error ? e.message : "Worktree failed");
    } finally {
      setWtBusy(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-800" />
      </div>
    );
  }

  if (!project) {
    return <p className="text-slate-500">Project not found</p>;
  }

  const stageIdx = STAGES.findIndex((s) => s.key === project.current_stage);

  return (
    <div>
      <Link to="/projects" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-4">
        <ArrowLeft className="h-4 w-4" /> Back to Projects
      </Link>

      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-xl font-bold text-slate-900" data-testid="project-detail-name">
              {project.name}
            </h1>
            <p className="text-sm text-slate-500 mt-1">{project.description}</p>
          </div>
          <span
            className={`text-xs font-medium px-2.5 py-1 rounded capitalize ${
              project.status === "active"
                ? "bg-emerald-100 text-emerald-700"
                : project.status === "completed"
                  ? "bg-slate-100 text-slate-600"
                  : "bg-orange-100 text-orange-700"
            }`}
          >
            {project.status}
          </span>
        </div>

        <div className="flex items-center gap-6 mb-6 flex-wrap">
          {STAGES.map((s, i) => (
            <div key={s.key} className="flex items-center gap-2">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                  i < stageIdx
                    ? "bg-green-500 text-white"
                    : i === stageIdx
                      ? "bg-indigo-600 text-white"
                      : "bg-slate-200 text-slate-500"
                }`}
              >
                {i + 1}
              </div>
              <span className={`text-xs font-medium ${i === stageIdx ? "text-indigo-600" : "text-slate-500"}`}>
                {s.label}
              </span>
              {i < STAGES.length - 1 && (
                <div className={`w-8 h-0.5 ${i < stageIdx ? "bg-green-400" : "bg-slate-200"}`} />
              )}
            </div>
          ))}
        </div>

        <div className="grid grid-cols-4 gap-4">
          <div className="bg-slate-50 rounded-lg p-3 text-center">
            <p className="text-xl font-bold text-slate-900">{project.completion_percent}%</p>
            <p className="text-xs text-slate-500">Completion</p>
          </div>
          <div className="bg-slate-50 rounded-lg p-3 text-center">
            <p className="text-xl font-bold text-blue-600">{project.token_savings}%</p>
            <p className="text-xs text-slate-500">Token Savings</p>
          </div>
          <div className="bg-slate-50 rounded-lg p-3 text-center">
            <p className="text-xl font-bold text-red-600">{project.risk_alerts}</p>
            <p className="text-xs text-slate-500">Risk Alerts</p>
          </div>
          <div className="bg-slate-50 rounded-lg p-3 text-center">
            <p className="text-xl font-bold text-slate-900" data-testid="project-repo-count">
              {project.repos.length}
            </p>
            <p className="text-xs text-slate-500">Repositories</p>
          </div>
        </div>
      </div>

      <div className="mb-6">
        <RepoOnboardingPanel projectId={project.id} compact />
      </div>

      {project.repos.length > 0 && (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-slate-500">Active repository</span>
            {project.repos.map((r, idx) => (
              <button
                key={r.id}
                type="button"
                data-testid={`project-repo-tab-${r.id}`}
                onClick={() => {
                  setSelectedRepoIdx(idx);
                  const hit = cloned.find(
                    (c) => c.owner === r.owner && c.repo_name === r.repo_name,
                  );
                  if (hit?.repo_id) setActiveRepo(hit.repo_id);
                }}
                className={`text-xs px-3 py-1.5 rounded-lg border ${
                  idx === selectedRepoIdx
                    ? "border-indigo-300 bg-indigo-50 text-indigo-800"
                    : "border-slate-200 text-slate-600 hover:bg-slate-50"
                }`}
              >
                {r.owner}/{r.repo_name}
              </button>
            ))}
          </div>

          <div className="flex gap-1 mb-4 bg-white rounded-lg border border-slate-200 p-1 w-fit">
            {(["overview", "prs", "commits", "ci"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                data-testid={`project-tab-${t}`}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors capitalize ${
                  tab === t ? "bg-indigo-600 text-white" : "text-slate-600 hover:bg-slate-50"
                }`}
              >
                {t === "prs" ? "Pull Requests" : t === "ci" ? "CI/CD" : t}
              </button>
            ))}
          </div>

          {tab === "overview" && (
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="text-sm font-semibold text-slate-700 mb-3">Linked Repositories</h2>
              {project.repos.map((r) => (
                <div
                  key={r.id}
                  data-testid={`project-repo-row-${r.id}`}
                  className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg mb-2"
                >
                  <GitBranch className="h-5 w-5 text-slate-400" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-slate-900">
                      {r.owner}/{r.repo_name}
                    </p>
                    <p className="text-xs text-slate-500">
                      Workspace:{" "}
                      {activeRepo &&
                      activeRepo.owner === r.owner &&
                      activeRepo.repo_name === r.repo_name &&
                      activeBranch
                        ? activeBranch
                        : r.default_branch || "—"}
                      {r.default_branch ? ` · default: ${r.default_branch}` : ""}
                    </p>
                  </div>
                  <a
                    href={`https://github.com/${r.owner}/${r.repo_name}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
                  >
                    GitHub <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              ))}
              <div className="mt-4 grid grid-cols-3 gap-3 text-center text-sm">
                <div className="bg-slate-50 rounded-lg p-3">
                  <GitPullRequest className="h-5 w-5 mx-auto mb-1 text-purple-500" />
                  <p className="font-bold text-slate-900">{pulls.length}</p>
                  <p className="text-xs text-slate-500">Pull Requests</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3">
                  <GitCommit className="h-5 w-5 mx-auto mb-1 text-blue-500" />
                  <p className="font-bold text-slate-900">{commits.length}</p>
                  <p className="text-xs text-slate-500">Commits</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3">
                  <CheckCircle2 className="h-5 w-5 mx-auto mb-1 text-green-500" />
                  <p className="font-bold text-slate-900">{runs.length}</p>
                  <p className="text-xs text-slate-500">CI Runs</p>
                </div>
              </div>
            </div>
          )}

          {tab === "prs" && (
            <div className="bg-white rounded-xl border border-slate-200" data-testid="project-prs-panel">
              <div className="px-4 py-3 border-b border-slate-100 space-y-2">
                <p className="text-xs font-medium text-slate-600">Open Pull Request by number</p>
                <div className="flex flex-wrap gap-2">
                  <input
                    data-testid="pr-number-input"
                    type="number"
                    min={1}
                    placeholder="PR #"
                    value={prNumberInput}
                    onChange={(e) => setPrNumberInput(e.target.value)}
                    className="w-24 border border-slate-200 rounded-lg px-2 py-1.5 text-sm"
                  />
                  <input
                    data-testid="pr-head-branch-input"
                    placeholder="head branch"
                    value={prHeadInput}
                    onChange={(e) => setPrHeadInput(e.target.value)}
                    className="flex-1 min-w-[140px] border border-slate-200 rounded-lg px-2 py-1.5 text-sm"
                  />
                  <button
                    type="button"
                    data-testid="pr-open-by-number"
                    disabled={wtBusy !== null}
                    onClick={() => {
                      const n = Number(prNumberInput || 0);
                      const br = prHeadInput.trim();
                      if (!n || !br) {
                        setWtError("Enter PR number and head branch");
                        return;
                      }
                      void openWorktree({
                        number: n,
                        title: `PR #${n}`,
                        state: "open",
                        author: "",
                        created_at: new Date().toISOString(),
                        updated_at: new Date().toISOString(),
                        merged_at: null,
                        additions: 0,
                        deletions: 0,
                        changed_files: 0,
                        html_url: "",
                        head_branch: br,
                        base_branch: "",
                        body: null,
                      });
                    }}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-sm disabled:opacity-50"
                  >
                    Open worktree
                  </button>
                </div>
              </div>
              {(wtMessage || wtError) && (
                <div className="px-4 py-2 border-b border-slate-100 text-sm">
                  {wtMessage && (
                    <p data-testid="pr-worktree-message" className="text-emerald-700">
                      {wtMessage}
                    </p>
                  )}
                  {wtError && (
                    <p data-testid="pr-worktree-error" className="text-red-600">
                      {wtError}
                    </p>
                  )}
                </div>
              )}
              <div className="divide-y divide-slate-100">
                {pulls.length === 0 && (
                  <p className="p-6 text-sm text-slate-500 text-center">No pull requests found</p>
                )}
                {pulls.map((pr) => (
                  <div
                    key={pr.number}
                    data-testid={`project-pr-${pr.number}`}
                    className="flex items-center gap-4 p-4"
                  >
                    <GitPullRequest
                      className={`h-5 w-5 shrink-0 ${
                        pr.state === "merged"
                          ? "text-purple-500"
                          : pr.state === "open"
                            ? "text-green-500"
                            : "text-red-500"
                      }`}
                    />
                    <div className="flex-1 min-w-0">
                      <Link
                        to={`/projects/${id}/pr/${selectedRepo!.owner}/${selectedRepo!.repo_name}/${pr.number}`}
                        className="text-sm font-medium text-slate-900 truncate hover:text-indigo-700 block"
                      >
                        #{pr.number} {pr.title}
                      </Link>
                      <p className="text-xs text-slate-500">
                        {pr.author} · {pr.head_branch} → {pr.base_branch} · {relativeTime(pr.updated_at)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 text-xs shrink-0">
                      <span className="text-green-600 font-mono">+{pr.additions}</span>
                      <span className="text-red-600 font-mono">-{pr.deletions}</span>
                      <button
                        type="button"
                        data-testid={`pr-open-worktree-${pr.number}`}
                        disabled={wtBusy === pr.number}
                        onClick={() => void openWorktree(pr)}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded border border-indigo-200 bg-indigo-50 text-indigo-800 hover:bg-indigo-100 disabled:opacity-50"
                      >
                        {wtBusy === pr.number ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <GitBranch className="h-3 w-3" />
                        )}
                        Open worktree
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {tab === "commits" && (
            <div className="bg-white rounded-xl border border-slate-200 divide-y divide-slate-100">
              {commits.length === 0 && (
                <p className="p-6 text-sm text-slate-500 text-center">No commits found</p>
              )}
              {commits.map((c) => (
                <a
                  key={c.sha}
                  href={c.html_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-4 p-4 hover:bg-slate-50 transition-colors"
                >
                  <GitCommit className="h-5 w-5 text-blue-500 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-900 truncate">{c.message.split("\n")[0]}</p>
                    <p className="text-xs text-slate-500">
                      {c.author} · {c.sha.slice(0, 7)} · {relativeTime(c.date)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-xs shrink-0">
                    <span className="text-green-600 font-mono">+{c.additions}</span>
                    <span className="text-red-600 font-mono">-{c.deletions}</span>
                  </div>
                </a>
              ))}
            </div>
          )}

          {tab === "ci" && (
            <div className="bg-white rounded-xl border border-slate-200 divide-y divide-slate-100">
              {runs.length === 0 && (
                <p className="p-6 text-sm text-slate-500 text-center">No CI/CD runs found</p>
              )}
              {runs.map((r) => (
                <a
                  key={r.id}
                  href={r.html_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-4 p-4 hover:bg-slate-50 transition-colors"
                >
                  {ciIcon(r.conclusion)}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-900 truncate">{r.name}</p>
                    <p className="text-xs text-slate-500">
                      {r.event} · {r.head_branch} · {relativeTime(r.updated_at)}
                    </p>
                  </div>
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded capitalize ${
                      r.conclusion === "success"
                        ? "bg-green-100 text-green-700"
                        : r.conclusion === "failure"
                          ? "bg-red-100 text-red-700"
                          : "bg-yellow-100 text-yellow-700"
                    }`}
                  >
                    {r.conclusion ?? r.status}
                  </span>
                </a>
              ))}
            </div>
          )}
        </>
      )}

      {project.repos.length === 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
          <GitBranch className="h-10 w-10 mx-auto mb-3 text-slate-300" />
          <p className="font-medium text-slate-700">No repositories linked</p>
          <p className="text-sm text-slate-500 mt-1">
            Use Open Local / Clone / Discover / Attach above to bind repositories to this project.
          </p>
        </div>
      )}
    </div>
  );
}
