"use client";

import Link from "next/link";
import { Stage } from "@/types";

interface StageTrackerProps {
  stages: Stage[];
  projectId: string;
  currentStage?: string;
}

export default function StageTracker({
  stages,
  projectId,
  currentStage,
}: StageTrackerProps) {
  return (
    <div className="flex items-center gap-0 overflow-x-auto pb-2">
      {stages.map((stage, index) => {
        const isActive = stage.id === currentStage;
        const isComplete = stage.status === "complete";
        const isLast = index === stages.length - 1;

        return (
          <div key={stage.id} className="flex items-center">
            <Link
              href={`/projects/${projectId}/${stage.id}`}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm whitespace-nowrap transition-all ${
                isActive
                  ? "bg-slate-900 text-white font-medium shadow-sm"
                  : isComplete
                    ? "bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                    : "bg-slate-50 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              }`}
            >
              <span
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                  isActive
                    ? "bg-white text-slate-900"
                    : isComplete
                      ? "bg-emerald-200 text-emerald-800"
                      : "bg-slate-200 text-slate-500"
                }`}
              >
                {isComplete ? (
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  index + 1
                )}
              </span>
              <span className="hidden sm:inline">{stage.name}</span>
            </Link>
            {!isLast && (
              <div
                className={`w-8 h-0.5 mx-1 ${
                  isComplete ? "bg-emerald-300" : "bg-slate-200"
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
