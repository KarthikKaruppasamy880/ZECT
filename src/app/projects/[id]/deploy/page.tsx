"use client";

import DeployReadinessView from "@/components/stages/DeployReadinessView";
import { sampleDeployChecklist } from "@/data/stage-details";

export default function DeployReadinessPage() {
  return <DeployReadinessView checklist={sampleDeployChecklist} />;
}
