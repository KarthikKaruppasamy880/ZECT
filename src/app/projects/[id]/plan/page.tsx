"use client";

import { useParams } from "next/navigation";
import PlanModeView from "@/components/stages/PlanModeView";
import { getProjectStageData } from "@/data/project-stages";

export default function PlanModePage() {
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

  return <PlanModeView sections={stageData.planSections} />;
}
