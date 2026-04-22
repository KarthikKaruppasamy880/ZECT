"use client";

import { useParams } from "next/navigation";
import BuildPhaseView from "@/components/stages/BuildPhaseView";
import { getProjectStageData } from "@/data/project-stages";

export default function BuildPhasePage() {
  const params = useParams();
  const projectId = params.id as string;
  const stageData = getProjectStageData(projectId);

  return <BuildPhaseView tasks={stageData.buildTasks} />;
}
