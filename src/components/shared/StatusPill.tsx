"use client";

import { StageStatus } from "@/types";
import { stageStatusColor, stageStatusLabel } from "@/lib/utils";

interface StatusPillProps {
  status: StageStatus;
  className?: string;
}

export default function StatusPill({ status, className = "" }: StatusPillProps) {
  return (
    <span
      className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${stageStatusColor(status)} ${className}`}
    >
      {stageStatusLabel(status)}
    </span>
  );
}
