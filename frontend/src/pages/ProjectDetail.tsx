import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getProject, getGitHubPulls, getGitHubCommits, getGitHubWorkflowRuns } from "@/lib/api";
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
  const [project, setProject] = useState<Project | null>(null);
  const [pulls, setPulls] = useState<GitHubPR[]>([]);
  const [commits, setCommits] = useState<GitHubCommit[]>([]);
  const [runs, setRuns] = useState<GitHubWorkflowRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"overview" | "prs" | "commits" | "ci">("overview");

  useEffect(() => {
    if (!id) return;
    getProject(Number(id))
      .then((p) => {
        setProject(p);
        if (p.repos.length > 0) {
          const r = p.repos[0];
          return Promise.all([
            getGitHubPulls(r.owner, r.repo_name).catch(() => []),
            getGitHubCommits(r.owner, r.repo_name).catch(() => []),
            getGitHubWorkflowRuns(r.owner, r.repo_name).catch(() => []),
          ]).then(([prs, cs, rs]) => {
            setPulls(prs);
            setCommits(cs);
            setRuns(rs);
          });
        }
      })
      .finally(() => setLoading(false));
  }, [id]);

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
            <h1 className="text-xl font-bold text-slate-900">{project.name}</h1>
            <p className="text-sm text-slate-500 mt-1">{project.description}</p>
          </div>
          <span className={`text-xs font-medium px-2.5 py-1 rounded capitalize ${
            project.status === "active" ? "bg-emerald-100 text-emerald-700" :
            project.status === "completed" ? "bg-slate-100 text-slate-600" :
            "bg-orange-100 text-orange-700"
          }`}>
            {project.status}
          </span>
        </div>

        <div className="flex items-center gap-6 mb-6">
          {STAGES.map((s, i) => (
            <div key={s.key} className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                i < stageIdx ? "bg-green-500 text-white" :
                i === stageIdx ? "bg-indigo-600 text-white" :
                "bg-slate-200 text-slate-500"
              }`}>
                {i + 1}
              </div>
              <span className={`text-xs font-medium ${i === stageIdx ? "text-indigo-600" : "text-slate-500"}`}>
                {s.label}
              </span>
              {i < STAGES.length - 1 && <div className={`w-8 h-0.5 ${i < stageIdx ? "bg-green-400" : "bg-slate-200"}`} />}
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
            <p className="text-xl font-bold text-slate-900">{project.repos.length}</p>
            <p className="text-xs text-slate-500">Repositories</p>
          </div>
        </div>
      </div>

      {project.repos.length > 0 && (
        <>
          <div className="flex gap-1 mb-4 bg-white rounded-lg border border-slate-200 p-1 w-fit">
            {(["overview", "prs", "commits", "ci"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
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
                <div key={r.id} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg mb-2">
                  <GitBranch className="h-5 w-5 text-slate-400" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-slate-900">{r.owner}/{r.repo_name}</p>
                    <p className="text-xs text-slate-500">Branch: {r.default_branch}</p>
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
            <div className="bg-white rounded-xl border border-slate-200 divide-y divide-slate-100">
              {pulls.length === 0 && (
                <p className="p-6 text-sm text-slate-500 text-center">No pull requests found</p>
              )}
              {pulls.map((pr) => (
                <Link
                  key={pr.number}
                  to={`/projects/${id}/pr/${project.repos[0].owner}/${project.repos[0].repo_name}/${pr.number}`}
                  className="flex items-center gap-4 p-4 hover:bg-slate-50 transition-colors"
                >
                  <GitPullRequest className={`h-5 w-5 shrink-0 ${
                    pr.state === "merged" ? "text-purple-500" :
                    pr.state === "open" ? "text-green-500" :
                    "text-red-500"
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-900 truncate">
                      #{pr.number} {pr.title}
                    </p>
                    <p className="text-xs text-slate-500">
                      {pr.author} · {pr.head_branch} → {pr.base_branch} · {relativeTime(pr.updated_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 text-xs shrink-0">
                    <span className="text-green-600 font-mono">+{pr.additions}</span>
                    <span className="text-red-600 font-mono">-{pr.deletions}</span>
                    <span className="text-slate-500">{pr.changed_files} files</span>
                  </div>
                </Link>
              ))}
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
                  <span className={`text-xs font-medium px-2 py-0.5 rounded capitalize ${
                    r.conclusion === "success" ? "bg-green-100 text-green-700" :
                    r.conclusion === "failure" ? "bg-red-100 text-red-700" :
                    "bg-yellow-100 text-yellow-700"
                  }`}>
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
          <p className="text-sm text-slate-500 mt-1">Link a GitHub repository to see PRs, commits, and CI status.</p>
        </div>
      )}
    </div>
  );
}
