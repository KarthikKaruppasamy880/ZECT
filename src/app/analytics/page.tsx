"use client";

import Header from "@/components/layout/Header";
import Card from "@/components/shared/Card";
import { projects } from "@/data/projects";
import { getGlobalRepoStats } from "@/data/orchestration";

export default function AnalyticsPage() {
  const stats = getGlobalRepoStats();
  const activeProjects = projects.filter((p) => p.status === "active");
  const completedProjects = projects.filter((p) => p.status === "completed");

  const avgTokenSavings = Math.round(
    projects.reduce((sum, p) => sum + p.metrics.tokenSavings, 0) / projects.length
  );
  const totalRiskAlerts = projects.reduce(
    (sum, p) => sum + p.metrics.riskAlerts, 0
  );
  const avgCompletion = Math.round(
    projects.reduce((sum, p) => sum + p.metrics.completionPercent, 0) / projects.length
  );

  const stageDistribution = [
    { stage: "Ask", count: projects.filter((p) => p.currentStage === "ask").length, color: "bg-violet-500" },
    { stage: "Plan", count: projects.filter((p) => p.currentStage === "plan").length, color: "bg-blue-500" },
    { stage: "Build", count: projects.filter((p) => p.currentStage === "build").length, color: "bg-amber-500" },
    { stage: "Review", count: projects.filter((p) => p.currentStage === "review").length, color: "bg-orange-500" },
    { stage: "Deploy", count: projects.filter((p) => p.currentStage === "deploy").length, color: "bg-emerald-500" },
  ];

  const teamMetrics = [
    { team: "Platform Engineering", projects: 2, avgCompletion: 78, tokenSavings: 42, alerts: 2 },
    { team: "Claims Engineering", projects: 1, avgCompletion: 78, tokenSavings: 42, alerts: 5 },
    { team: "Product Engineering", projects: 1, avgCompletion: 28, tokenSavings: 25, alerts: 1 },
    { team: "Underwriting Tech", projects: 1, avgCompletion: 92, tokenSavings: 51, alerts: 0 },
    { team: "AI/ML Engineering", projects: 1, avgCompletion: 8, tokenSavings: 12, alerts: 3 },
  ];

  const weeklyActivity = [
    { week: "Mar 10", tasks: 12, reviews: 4, deploys: 1 },
    { week: "Mar 17", tasks: 18, reviews: 6, deploys: 2 },
    { week: "Mar 24", tasks: 15, reviews: 8, deploys: 1 },
    { week: "Mar 31", tasks: 22, reviews: 5, deploys: 3 },
    { week: "Apr 7", tasks: 19, reviews: 9, deploys: 2 },
    { week: "Apr 14", tasks: 24, reviews: 7, deploys: 1 },
  ];

  const maxTasks = Math.max(...weeklyActivity.map((w) => w.tasks));

  return (
    <>
      <Header
        title="Analytics & Reporting"
        subtitle="Engineering delivery metrics, team performance, stage distribution, and trend analysis across all projects."
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Analytics" },
        ]}
      />

      {/* Summary Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4 mb-6">
        <Card className="text-center">
          <div className="text-2xl font-bold text-slate-900">{projects.length}</div>
          <div className="text-xs text-slate-500 mt-1">Total Projects</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-bold text-blue-600">{activeProjects.length}</div>
          <div className="text-xs text-slate-500 mt-1">Active</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-bold text-emerald-600">{completedProjects.length}</div>
          <div className="text-xs text-slate-500 mt-1">Completed</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-bold text-indigo-600">{avgTokenSavings}%</div>
          <div className="text-xs text-slate-500 mt-1">Avg Token Savings</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-bold text-amber-600">{totalRiskAlerts}</div>
          <div className="text-xs text-slate-500 mt-1">Total Risk Alerts</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-bold text-slate-900">{avgCompletion}%</div>
          <div className="text-xs text-slate-500 mt-1">Avg Completion</div>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
        {/* Stage Distribution */}
        <Card>
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Stage Distribution</h3>
          <div className="space-y-3">
            {stageDistribution.map((item) => (
              <div key={item.stage} className="flex items-center gap-3">
                <span className="w-16 text-sm text-slate-600">{item.stage}</span>
                <div className="flex-1 h-8 bg-slate-100 rounded-lg overflow-hidden relative">
                  <div
                    className={`h-full ${item.color} rounded-lg transition-all duration-500`}
                    style={{ width: `${projects.length > 0 ? (item.count / projects.length) * 100 : 0}%` }}
                  />
                  <span className="absolute inset-0 flex items-center px-3 text-xs font-medium text-slate-700">
                    {item.count} project{item.count !== 1 ? "s" : ""}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Weekly Activity Chart */}
        <Card>
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Weekly Activity</h3>
          <div className="flex items-end gap-2 h-40 mb-2">
            {weeklyActivity.map((week) => (
              <div key={week.week} className="flex-1 flex flex-col items-center gap-1">
                <div className="w-full flex flex-col gap-0.5 items-center justify-end h-32">
                  <div
                    className="w-full bg-blue-500 rounded-t-sm"
                    style={{ height: `${(week.tasks / maxTasks) * 100}%` }}
                    title={`${week.tasks} tasks`}
                  />
                </div>
                <span className="text-[10px] text-slate-400">{week.week}</span>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-4 justify-center text-xs text-slate-500 mt-2">
            <div className="flex items-center gap-1.5">
              <div className="w-2.5 h-2.5 rounded-sm bg-blue-500" />
              Tasks Completed
            </div>
          </div>
        </Card>
      </div>

      {/* Repo Health Overview */}
      <Card className="mb-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">Repository Health Overview</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 bg-slate-50 rounded-xl text-center">
            <div className="text-xl font-bold text-slate-900">{stats.totalRepos}</div>
            <div className="text-xs text-slate-500 mt-1">Total Repositories</div>
          </div>
          <div className="p-4 bg-emerald-50 rounded-xl text-center">
            <div className="text-xl font-bold text-emerald-600">{stats.reposByCiStatus.passing}</div>
            <div className="text-xs text-slate-500 mt-1">CI Passing</div>
          </div>
          <div className="p-4 bg-red-50 rounded-xl text-center">
            <div className="text-xl font-bold text-red-600">{stats.reposByCiStatus.failing}</div>
            <div className="text-xs text-slate-500 mt-1">CI Failing</div>
          </div>
          <div className="p-4 bg-amber-50 rounded-xl text-center">
            <div className="text-xl font-bold text-amber-600">{stats.warningDeps + stats.brokenDeps}</div>
            <div className="text-xs text-slate-500 mt-1">Dependency Issues</div>
          </div>
        </div>
      </Card>

      {/* Team Performance */}
      <Card className="mb-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">Team Performance</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2 px-3 text-slate-500 font-medium">Team</th>
                <th className="text-center py-2 px-3 text-slate-500 font-medium">Projects</th>
                <th className="text-left py-2 px-3 text-slate-500 font-medium">Avg Completion</th>
                <th className="text-center py-2 px-3 text-slate-500 font-medium">Token Savings</th>
                <th className="text-center py-2 px-3 text-slate-500 font-medium">Risk Alerts</th>
              </tr>
            </thead>
            <tbody>
              {teamMetrics.map((team) => (
                <tr key={team.team} className="border-b border-slate-100 last:border-0">
                  <td className="py-2.5 px-3 font-medium text-slate-800">{team.team}</td>
                  <td className="py-2.5 px-3 text-center text-slate-600">{team.projects}</td>
                  <td className="py-2.5 px-3">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden max-w-[120px]">
                        <div
                          className="h-full bg-blue-600 rounded-full"
                          style={{ width: `${team.avgCompletion}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-500 w-8">{team.avgCompletion}%</span>
                    </div>
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    <span className="text-emerald-600 font-medium">{team.tokenSavings}%</span>
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    {team.alerts > 0 ? (
                      <span className="px-2 py-0.5 bg-amber-50 text-amber-700 rounded-full text-xs font-medium">
                        {team.alerts}
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded-full text-xs font-medium">0</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Project Completion Breakdown */}
      <Card>
        <h3 className="text-lg font-semibold text-slate-900 mb-4">Project Completion Breakdown</h3>
        <div className="space-y-3">
          {projects.map((project) => (
            <div key={project.id} className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl">
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium text-slate-800 truncate">{project.name}</div>
                <div className="text-xs text-slate-500">{project.team}</div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  project.status === "completed"
                    ? "bg-emerald-50 text-emerald-700"
                    : project.status === "active"
                      ? "bg-blue-50 text-blue-700"
                      : "bg-slate-100 text-slate-500"
                }`}>
                  {project.currentStage}
                </span>
              </div>
              <div className="flex items-center gap-2 w-32">
                <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      project.metrics.completionPercent === 100
                        ? "bg-emerald-500"
                        : project.metrics.completionPercent >= 75
                          ? "bg-blue-500"
                          : project.metrics.completionPercent >= 50
                            ? "bg-amber-500"
                            : "bg-slate-400"
                    }`}
                    style={{ width: `${project.metrics.completionPercent}%` }}
                  />
                </div>
                <span className="text-xs font-medium text-slate-500 w-8 text-right">
                  {project.metrics.completionPercent}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </>
  );
}
