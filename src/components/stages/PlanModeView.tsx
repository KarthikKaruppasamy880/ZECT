"use client";

import { PlanSection } from "@/types";
import Card from "@/components/shared/Card";

interface PlanModeViewProps {
  sections: PlanSection[];
}

const statusStyles: Record<string, string> = {
  draft: "bg-amber-100 text-amber-700",
  approved: "bg-emerald-100 text-emerald-700",
  revised: "bg-blue-100 text-blue-700",
};

export default function PlanModeView({ sections }: PlanModeViewProps) {
  return (
    <div className="space-y-6">
      <Card>
        <h3 className="text-lg font-semibold text-slate-900 mb-1">
          Implementation Plan
        </h3>
        <p className="text-sm text-slate-500 mb-4">
          Architecture decisions, API design, database schema, and deployment
          strategy defined during the Plan phase.
        </p>
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-emerald-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-emerald-700">
              {sections.filter((s) => s.status === "approved").length}
            </div>
            <div className="text-xs text-slate-500 mt-1">Approved</div>
          </div>
          <div className="bg-amber-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-amber-700">
              {sections.filter((s) => s.status === "draft").length}
            </div>
            <div className="text-xs text-slate-500 mt-1">Draft</div>
          </div>
          <div className="bg-blue-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-blue-700">
              {sections.filter((s) => s.status === "revised").length}
            </div>
            <div className="text-xs text-slate-500 mt-1">Revised</div>
          </div>
        </div>
      </Card>

      {sections.map((section) => (
        <Card key={section.id}>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-base font-semibold text-slate-900">
              {section.title}
            </h3>
            <span
              className={`px-2.5 py-1 rounded-full text-xs font-medium ${statusStyles[section.status]}`}
            >
              {section.status.charAt(0).toUpperCase() + section.status.slice(1)}
            </span>
          </div>
          <div className="prose prose-sm prose-slate max-w-none">
            {section.content.split("\n").map((line, i) => {
              if (line.startsWith("**") && line.endsWith("**")) {
                return (
                  <h4 key={i} className="text-sm font-semibold text-slate-800 mt-3 mb-1">
                    {line.replace(/\*\*/g, "")}
                  </h4>
                );
              }
              if (line.startsWith("**")) {
                const parts = line.split("**");
                return (
                  <p key={i} className="text-sm text-slate-600 my-0.5">
                    <strong className="text-slate-800">{parts[1]}</strong>
                    {parts[2]}
                  </p>
                );
              }
              if (line.startsWith("- ")) {
                return (
                  <p key={i} className="text-sm text-slate-600 my-0.5 pl-4">
                    <span className="text-slate-400 mr-2">&bull;</span>
                    {line.slice(2)}
                  </p>
                );
              }
              if (line.trim() === "") return <div key={i} className="h-2" />;
              return (
                <p key={i} className="text-sm text-slate-600 my-0.5">
                  {line}
                </p>
              );
            })}
          </div>
        </Card>
      ))}
    </div>
  );
}
