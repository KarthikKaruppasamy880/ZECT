import Link from "next/link";
import { Project } from "@/types";
import Card from "@/components/shared/Card";
import StatusPill from "@/components/shared/StatusPill";
import ProgressBar from "@/components/shared/ProgressBar";
import { stageLabel } from "@/lib/utils";

interface ProjectCardProps {
  project: Project;
}

export default function ProjectCard({ project }: ProjectCardProps) {
  const currentStageObj = project.stages.find(
    (s) => s.id === project.currentStage
  );

  return (
    <Link href={`/projects/${project.id}/${project.currentStage}`}>
      <Card className="hover:shadow-md hover:border-slate-300 transition-all cursor-pointer">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h3 className="font-semibold text-slate-900">{project.name}</h3>
            <p className="text-xs text-slate-500 mt-0.5">{project.team}</p>
          </div>
          {currentStageObj && <StatusPill status={currentStageObj.status} />}
        </div>
        <p className="text-sm text-slate-600 line-clamp-2 mb-4">
          {project.description}
        </p>

        <div className="flex items-center justify-between text-xs text-slate-500 mb-2">
          <span>
            Stage: <span className="font-medium text-slate-700">{stageLabel(project.currentStage)}</span>
          </span>
          <span>{project.metrics.completionPercent}%</span>
        </div>
        <ProgressBar value={project.metrics.completionPercent} showLabel={false} />

        <div className="flex items-center gap-4 mt-4 pt-3 border-t border-slate-100 text-xs text-slate-500">
          <span>Tokens saved: {project.metrics.tokenSavings}%</span>
          {project.metrics.riskAlerts > 0 && (
            <span className="text-amber-600">
              {project.metrics.riskAlerts} alert{project.metrics.riskAlerts !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      </Card>
    </Link>
  );
}
