"use client";

import { useParams } from "next/navigation";
import BuildPhaseView from "@/components/stages/BuildPhaseView";
import { getProjectStageData } from "@/data/project-stages";

export default function BuildPhasePage() {
  const params = useParams();
  const projectId = params.id as string;
  const stageData = getProjectStageData(projectId);

  if (!stageData) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-500">No stage data available for this project yet.</p>
      </div>
    );
  }

  return <BuildPhaseView tasks={stageData.buildTasks} />;
}
