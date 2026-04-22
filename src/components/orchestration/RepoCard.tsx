"use client";

import { Repository } from "@/types";
import Card from "@/components/shared/Card";

interface RepoCardProps {
  repo: Repository;
}

const roleColors: Record<string, string> = {
  frontend: "bg-blue-100 text-blue-700",
  backend: "bg-purple-100 text-purple-700",
  "shared-lib": "bg-amber-100 text-amber-700",
  infra: "bg-slate-100 text-slate-700",
  docs: "bg-teal-100 text-teal-700",
  "ml-pipeline": "bg-rose-100 text-rose-700",
};

const syncStatusStyles: Record<string, { label: string; dot: string }> = {
  synced: { label: "Synced", dot: "bg-emerald-500" },
  ahead: { label: "Ahead", dot: "bg-blue-500" },
  behind: { label: "Behind", dot: "bg-amber-500" },
  diverged: { label: "Diverged", dot: "bg-orange-500" },
  conflict: { label: "Conflict", dot: "bg-red-500" },
};

const ciStatusStyles: Record<string, { label: string; color: string }> = {
  passing: { label: "Passing", color: "text-emerald-600" },
  failing: { label: "Failing", color: "text-red-600" },
  pending: { label: "Pending", color: "text-amber-600" },
  none: { label: "No CI", color: "text-slate-400" },
};

export default function RepoCard({ repo }: RepoCardProps) {
  const sync = syncStatusStyles[repo.syncStatus];
  const ci = ciStatusStyles[repo.ciStatus];

  return (
    <Card className="hover:shadow-md hover:border-slate-300 transition-all">
      <div className="flex items-start justify-between mb-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${roleColors[repo.role] || "bg-slate-100 text-slate-600"}`}>
              {repo.role}
            </span>
            <span className="text-xs text-slate-400">{repo.language}</span>
          </div>
          <h4 className="font-semibold text-sm text-slate-900 truncate">{repo.name}</h4>
          <p className="text-xs text-slate-500 truncate">{repo.fullName}</p>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <span className={`w-2 h-2 rounded-full ${sync.dot}`} />
          <span className="text-xs text-slate-500">{sync.label}</span>
        </div>
      </div>

      <div className="text-xs text-slate-600 mb-3 line-clamp-1">
        <span className="text-slate-400">Latest:</span> {repo.lastCommitMessage}
      </div>

      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-3">
          <span className={`font-medium ${ci.color}`}>
            CI: {ci.label}
          </span>
          {repo.openPRs > 0 && (
            <span className="text-slate-500">
              {repo.openPRs} PR{repo.openPRs !== 1 ? "s" : ""}
            </span>
          )}
          {repo.openIssues > 0 && (
            <span className="text-slate-500">
              {repo.openIssues} issue{repo.openIssues !== 1 ? "s" : ""}
            </span>
          )}
        </div>
        {repo.coverage > 0 && (
          <span className={`font-medium ${repo.coverage >= 80 ? "text-emerald-600" : repo.coverage >= 60 ? "text-amber-600" : "text-red-600"}`}>
            {repo.coverage}% cov
          </span>
        )}
      </div>

      <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
        <span>branch: <span className="font-mono text-slate-500">{repo.branch}</span></span>
        <span>{repo.lastCommitAuthor}</span>
      </div>
    </Card>
  );
}
