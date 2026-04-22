"use client";

import { useParams } from "next/navigation";
import PlanModeView from "@/components/stages/PlanModeView";
import { getProjectStageData } from "@/data/project-stages";

export default function PlanModePage() {
  const params = useParams();
  const projectId = params.id as string;
  const stageData = getProjectStageData(projectId);

  return <PlanModeView sections={stageData.planSections} />;
}
