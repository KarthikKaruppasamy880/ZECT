"use client";

import { useParams } from "next/navigation";
import ReviewView from "@/components/stages/ReviewView";
import { getProjectStageData } from "@/data/project-stages";

export default function ReviewPage() {
  const params = useParams();
  const projectId = params.id as string;
  const stageData = getProjectStageData(projectId);

  return <ReviewView findings={stageData.reviewFindings} />;
}
