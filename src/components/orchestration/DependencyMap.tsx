"use client";

import { Repository, RepoDependency } from "@/types";
import Card from "@/components/shared/Card";

interface DependencyMapProps {
  repositories: Repository[];
  dependencies: RepoDependency[];
}

const depTypeLabels: Record<string, string> = {
  imports: "Imports",
  "api-consumer": "API Consumer",
  "shared-schema": "Shared Schema",
  "deploy-depends": "Deploy Depends",
  "event-subscriber": "Event Sub",
};

const depStatusStyles: Record<string, { bg: string; text: string; border: string }> = {
  healthy: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  warning: { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200" },
  broken: { bg: "bg-red-50", text: "text-red-700", border: "border-red-200" },
};

export default function DependencyMap({ repositories, dependencies }: DependencyMapProps) {
  const repoMap = new Map(repositories.map((r) => [r.id, r]));

  const healthCount = dependencies.filter((d) => d.status === "healthy").length;
  const warnCount = dependencies.filter((d) => d.status === "warning").length;
  const brokenCount = dependencies.filter((d) => d.status === "broken").length;

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Cross-Repo Dependencies</h3>
          <p className="text-sm text-slate-500 mt-0.5">
            How repositories in this project depend on each other.
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            {healthCount} healthy
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            {warnCount} warning
          </span>
          {brokenCount > 0 && (
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-red-500" />
              {brokenCount} broken
            </span>
          )}
        </div>
      </div>

      <div className="space-y-2">
        {dependencies.map((dep) => {
          const source = repoMap.get(dep.sourceRepoId);
          const target = repoMap.get(dep.targetRepoId);
          const style = depStatusStyles[dep.status];

          return (
            <div
              key={dep.id}
              className={`${style.bg} ${style.border} border rounded-xl p-3 flex items-center gap-3`}
            >
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <span className="font-mono text-xs font-medium text-slate-800 truncate">
                  {source?.name || dep.sourceRepoId}
                </span>
                <svg className="w-4 h-4 text-slate-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17 8l4 4m0 0l-4 4m4-4H3" />
                </svg>
                <span className="font-mono text-xs font-medium text-slate-800 truncate">
                  {target?.name || dep.targetRepoId}
                </span>
              </div>
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-white/60 text-slate-600 whitespace-nowrap">
                {depTypeLabels[dep.type] || dep.type}
              </span>
              <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${style.text} whitespace-nowrap`}>
                {dep.status}
              </span>
            </div>
          );
        })}
      </div>

      {dependencies.length === 0 && (
        <div className="text-center py-8 text-slate-400 text-sm">
          No cross-repo dependencies defined yet.
        </div>
      )}
    </Card>
  );
}
