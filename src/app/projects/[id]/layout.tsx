"use client";

import { useParams, usePathname } from "next/navigation";
import Header from "@/components/layout/Header";
import StageTracker from "@/components/projects/StageTracker";
import Card from "@/components/shared/Card";
import { projects } from "@/data/projects";

export default function ProjectLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const pathname = usePathname();
  const projectId = params.id as string;
  const project = projects.find((p) => p.id === projectId);
  const pathSegments = pathname.split("/");
  const activeStage = pathSegments[pathSegments.length - 1];

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
          <StageTracker
            stages={project.stages}
            projectId={project.id}
            currentStage={activeStage || project.currentStage}
          />
        </Card>
      </div>

      {children}
    </>
  );
}
