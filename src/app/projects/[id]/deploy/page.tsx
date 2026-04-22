"use client";

import { useParams } from "next/navigation";
import DeployReadinessView from "@/components/stages/DeployReadinessView";
import { getProjectStageData } from "@/data/project-stages";

export default function DeployReadinessPage() {
  const params = useParams();
  const projectId = params.id as string;
  const stageData = getProjectStageData(projectId);

  return <DeployReadinessView checklist={stageData.deployChecklist} />;
}
