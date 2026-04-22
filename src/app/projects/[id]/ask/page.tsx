"use client";

import AskModeView from "@/components/stages/AskModeView";
import { sampleRequirements } from "@/data/stage-details";

export default function AskModePage() {
  return <AskModeView requirements={sampleRequirements} />;
}
