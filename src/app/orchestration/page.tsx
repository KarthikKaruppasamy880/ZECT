"use client";

import { useState } from "react";
import Header from "@/components/layout/Header";
import Card from "@/components/shared/Card";
import RepoCard from "@/components/orchestration/RepoCard";
import { projectOrchestrations, getGlobalRepoStats } from "@/data/orchestration";
import { projects } from "@/data/projects";

export default function GlobalOrchestrationPage() {
  const [selectedProject, setSelectedProject] = useState<string>("all");
  const stats = getGlobalRepoStats();

  const allRepos = selectedProject === "all"
    ? projectOrchestrations.flatMap((o) => o.repositories)
    : projectOrchestrations
        .filter((o) => o.projectId === selectedProject)
        .flatMap((o) => o.repositories);

  const allDeps = selectedProject === "all"
    ? projectOrchestrations.flatMap((o) => o.dependencies)
    : projectOrchestrations
        .filter((o) => o.projectId === selectedProject)
        .flatMap((o) => o.dependencies);

  const projectOptions = projectOrchestrations.map((o) => {
    const project = projects.find((p) => p.id === o.projectId);
    return { id: o.projectId, name: project?.name || o.projectId };
  });

  return (
    <>
      <Header
        title="Multi-Repo Orchestration"
        subtitle="Cross-repository dependency tracking, CI health monitoring, and orchestration events across all Zinnia engineering projects."
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Orchestration" },
        ]}
      />

      {/* Global Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-6 gap-4 mb-6">
        <Card className="text-center">
          <div className="text-2xl font-bold text-slate-900">{stats.totalRepos}</div>
          <div className="text-xs text-slate-500 mt-1">Total Repos</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-bold text-emerald-600">{stats.reposByCiStatus.passing}</div>
          <div className="text-xs text-slate-500 mt-1">CI Passing</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-bold text-red-600">{stats.reposByCiStatus.failing}</div>
          <div className="text-xs text-slate-500 mt-1">CI Failing</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-bold text-slate-900">{stats.totalDependencies}</div>
          <div className="text-xs text-slate-500 mt-1">Dependencies</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-bold text-amber-600">{stats.warningDeps}</div>
          <div className="text-xs text-slate-500 mt-1">Dep Warnings</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-bold text-red-600">{stats.criticalEvents}</div>
          <div className="text-xs text-slate-500 mt-1">Critical Events</div>
        </Card>
      </div>

      {/* Project Filter */}
      <Card className="mb-6">
        <div className="flex items-center gap-3">
          <span className="text-sm text-slate-600 font-medium">Filter by project:</span>
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => setSelectedProject("all")}
              className={`px-3 py-2 rounded-xl text-xs font-medium transition-colors ${
                selectedProject === "all"
                  ? "bg-slate-900 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              All Projects
            </button>
            {projectOptions.map((opt) => (
              <button
                key={opt.id}
                onClick={() => setSelectedProject(opt.id)}
                className={`px-3 py-2 rounded-xl text-xs font-medium transition-colors ${
                  selectedProject === opt.id
                    ? "bg-slate-900 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {opt.name}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Dependency Health */}
      {allDeps.length > 0 && (
        <Card className="mb-6">
          <h3 className="text-lg font-semibold text-slate-900 mb-3">Dependency Health</h3>
          <div className="space-y-2">
            {allDeps.map((dep) => {
              const sourceRepo = allRepos.find((r) => r.id === dep.sourceRepoId);
              const targetRepo = allRepos.find((r) => r.id === dep.targetRepoId);
              const statusColor =
                dep.status === "healthy"
                  ? "bg-emerald-50 border-emerald-200"
                  : dep.status === "warning"
                    ? "bg-amber-50 border-amber-200"
                    : "bg-red-50 border-red-200";
              const statusText =
                dep.status === "healthy"
                  ? "text-emerald-700"
                  : dep.status === "warning"
                    ? "text-amber-700"
                    : "text-red-700";

              return (
                <div key={dep.id} className={`${statusColor} border rounded-xl p-3 flex items-center gap-3`}>
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <span className="font-mono text-xs font-medium text-slate-800 truncate">
                      {sourceRepo?.name || dep.sourceRepoId}
                    </span>
                    <svg className="w-4 h-4 text-slate-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M17 8l4 4m0 0l-4 4m4-4H3" />
                    </svg>
                    <span className="font-mono text-xs font-medium text-slate-800 truncate">
                      {targetRepo?.name || dep.targetRepoId}
                    </span>
                  </div>
                  <span className="text-xs text-slate-500 whitespace-nowrap">{dep.description.slice(0, 60)}</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${statusText} whitespace-nowrap`}>
                    {dep.status}
                  </span>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* Repository Grid */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-slate-900">
            Repositories ({allRepos.length})
          </h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {allRepos.map((repo) => (
            <RepoCard key={repo.id} repo={repo} />
          ))}
        </div>
      </div>

      {/* Recent Events */}
      <Card>
        <h3 className="text-lg font-semibold text-slate-900 mb-3">Recent Cross-Repo Events</h3>
        <div className="space-y-2">
          {stats.recentEvents.map((event) => {
            const severityBorder =
              event.severity === "critical"
                ? "border-l-red-400"
                : event.severity === "warning"
                  ? "border-l-amber-400"
                  : "border-l-blue-400";

            return (
              <div
                key={event.id}
                className={`border-l-4 ${severityBorder} bg-slate-50 rounded-r-xl p-3`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="text-xs font-medium text-slate-500">
                      {event.type.replace("-", " ").toUpperCase()}
                    </span>
                    <p className="text-sm text-slate-700 mt-0.5">{event.message}</p>
                    {event.impactedRepoIds.length > 0 && (
                      <div className="flex items-center gap-1 mt-1 flex-wrap">
                        <span className="text-xs text-slate-400">Impacts:</span>
                        {event.impactedRepoIds.map((id) => {
                          const repo = allRepos.find((r) => r.id === id);
                          return (
                            <span key={id} className="px-1.5 py-0.5 rounded text-xs font-mono bg-white text-slate-600">
                              {repo?.name || id}
                            </span>
                          );
                        })}
                      </div>
                    )}
                  </div>
                  <span className="text-xs text-slate-400 whitespace-nowrap">
                    {new Date(event.timestamp).toLocaleDateString()}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </Card>
    </>
  );
}
