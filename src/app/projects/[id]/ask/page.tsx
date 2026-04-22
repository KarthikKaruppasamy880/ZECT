"use client";

import { useParams } from "next/navigation";
import AskModeView from "@/components/stages/AskModeView";
import { getProjectStageData } from "@/data/project-stages";

export default function AskModePage() {
  const params = useParams();
  const projectId = params.id as string;
  const stageData = getProjectStageData(projectId);

  return <AskModeView requirements={stageData.requirements} />;
}
