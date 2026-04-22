"use client";

import BuildPhaseView from "@/components/stages/BuildPhaseView";
import { sampleBuildTasks } from "@/data/stage-details";

export default function BuildPhasePage() {
  return <BuildPhaseView tasks={sampleBuildTasks} />;
}
