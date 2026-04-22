"use client";

import PlanModeView from "@/components/stages/PlanModeView";
import { samplePlanSections } from "@/data/stage-details";

export default function PlanModePage() {
  return <PlanModeView sections={samplePlanSections} />;
}
