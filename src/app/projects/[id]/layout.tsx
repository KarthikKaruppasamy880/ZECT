"use client";

import { useParams, usePathname } from "next/navigation";
import Link from "next/link";
import Header from "@/components/layout/Header";
import StageTracker from "@/components/projects/StageTracker";
import Card from "@/components/shared/Card";
import { projects } from "@/data/projects";
import { getOrchestration } from "@/data/orchestration";

export default function ProjectLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const pathname = usePathname();
  const projectId = params.id as string;
  const project = projects.find((p) => p.id === projectId);
  const validStages = ["ask", "plan", "build", "review", "deploy"];
  const pathSegments = pathname.split("/");
  const lastSegment = pathSegments[pathSegments.length - 1];
  const activeStage = validStages.includes(lastSegment) ? lastSegment : undefined;
  const orchestration = getOrchestration(projectId);

  if (!project) {
    return (
      <div className="flex items-center justify-center h-96">
        <Card className="text-center py-12 px-8">
          <div className="text-slate-400 text-sm">Project not found.</div>
        </Card>
      </div>
    );
  }

  return (
    <>
      <Header
        title={project.name}
        subtitle={project.description}
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Projects", href: "/projects" },
          { label: project.name },
        ]}
      />

      <div className="mb-6">
        <Card className="!p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-500">Team:</span>
              <span className="text-xs font-medium text-slate-700">
                {project.team}
              </span>
            </div>
            <div className="flex items-center gap-4 text-xs text-slate-500">
              <span>
                Tokens saved:{" "}
                <span className="font-medium text-emerald-600">
                  {project.metrics.tokenSavings}%
                </span>
              </span>
              {project.metrics.riskAlerts > 0 && (
                <span>
                  Alerts:{" "}
                  <span className="font-medium text-amber-600">
                    {project.metrics.riskAlerts}
                  </span>
                </span>
              )}
              <span>
                Progress:{" "}
                <span className="font-medium text-slate-700">
                  {project.metrics.completionPercent}%
                </span>
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex-1">
              <StageTracker
                stages={project.stages}
                projectId={project.id}
                currentStage={activeStage || project.currentStage}
              />
            </div>
            {orchestration && (
              <Link
                href={`/projects/${project.id}/orchestration`}
                className={`flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm whitespace-nowrap transition-all ${
                  lastSegment === "orchestration"
                    ? "bg-indigo-600 text-white font-medium shadow-sm"
                    : "bg-indigo-50 text-indigo-700 hover:bg-indigo-100"
                }`}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <line x1="6" y1="3" x2="6" y2="15" />
                  <circle cx="18" cy="6" r="3" />
                  <circle cx="6" cy="18" r="3" />
                  <path d="M18 9a9 9 0 0 1-9 9" />
                </svg>
                <span className="hidden sm:inline">Repos</span>
              </Link>
            )}
          </div>
        </Card>
      </div>

      {children}
    </>
  );
}
