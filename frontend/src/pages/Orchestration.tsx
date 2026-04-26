import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getProjects, getGitHubRepo } from "@/lib/api";
import type { Project, GitHubRepoInfo } from "@/types";
import {
  GitBranch,
  ExternalLink,
  Star,
  GitFork,
  AlertCircle,
  CheckCircle2,
  Loader2,
} from "lucide-react";

export default function Orchestration() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [repoInfos, setRepoInfos] = useState<Record<string, GitHubRepoInfo>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getProjects().then(async (ps) => {
      setProjects(ps);
      const infos: Record<string, GitHubRepoInfo> = {};
      for (const p of ps) {
        for (const r of p.repos) {
          const key = `${r.owner}/${r.repo_name}`;
          if (!infos[key]) {
            try {
              infos[key] = await getGitHubRepo(r.owner, r.repo_name);
            } catch {
              // skip repos we can't fetch
            }
          }
        }
      }
      setRepoInfos(infos);
    }).finally(() => setLoading(false));
  }, []);

  const allRepos = projects.flatMap((p) =>
    p.repos.map((r) => ({ ...r, projectName: p.name, projectId: p.id }))
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-800" />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Multi-Repo Orchestration</h1>
        <p className="text-slate-500 text-sm">
          Manage and monitor all repositories across projects
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-xl border border-slate-200 p-5 text-center">
          <p className="text-3xl font-bold text-slate-900">{allRepos.length}</p>
          <p className="text-sm text-slate-500">Total Repos</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5 text-center">
          <p className="text-3xl font-bold text-slate-900">{projects.length}</p>
          <p className="text-sm text-slate-500">Projects</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5 text-center">
          <p className="text-3xl font-bold text-green-600">
            {Object.values(repoInfos).length}
          </p>
          <p className="text-sm text-slate-500">Connected</p>
        </div>
      </div>

      {allRepos.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
          <GitBranch className="h-10 w-10 mx-auto mb-3 text-slate-300" />
          <p className="font-medium text-slate-700">No repositories linked</p>
          <p className="text-sm text-slate-500 mt-1">
            Link repositories to your projects to see them here.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {allRepos.map((r) => {
            const key = `${r.owner}/${r.repo_name}`;
            const info = repoInfos[key];
            return (
              <div
                key={`${r.projectId}-${key}`}
                className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <GitBranch className="h-5 w-5 text-indigo-500" />
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{key}</p>
                      <p className="text-xs text-slate-500">
                        Project:{" "}
                        <Link
                          to={`/projects/${r.projectId}`}
                          className="text-indigo-600 hover:text-indigo-700"
                        >
                          {r.projectName}
                        </Link>
                      </p>
                    </div>
                  </div>
                  <a
                    href={info?.html_url ?? `https://github.com/${key}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
                  >
                    Open <ExternalLink className="h-3 w-3" />
                  </a>
                </div>

                {info ? (
                  <>
                    {info.description && (
                      <p className="text-xs text-slate-500 mb-3 line-clamp-2">{info.description}</p>
                    )}
                    <div className="flex items-center gap-4 text-xs text-slate-500">
                      {info.language && (
                        <span className="flex items-center gap-1">
                          <span className="w-2.5 h-2.5 rounded-full bg-indigo-400" />
                          {info.language}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <Star className="h-3 w-3" /> {info.stars}
                      </span>
                      <span className="flex items-center gap-1">
                        <GitFork className="h-3 w-3" /> {info.forks}
                      </span>
                      <span className="flex items-center gap-1">
                        <AlertCircle className="h-3 w-3" /> {info.open_issues} issues
                      </span>
                      <span className="flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3 text-green-500" /> Connected
                      </span>
                    </div>
                  </>
                ) : (
                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    <Loader2 className="h-3 w-3 animate-spin" /> Loading repo info...
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
