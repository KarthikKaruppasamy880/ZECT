"use client";

import { useParams } from "next/navigation";
import ReviewView from "@/components/stages/ReviewView";
import { getProjectStageData } from "@/data/project-stages";

export default function ReviewPage() {
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

  return <ReviewView findings={stageData.reviewFindings} />;
}
