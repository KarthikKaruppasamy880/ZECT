"use client";

import { RequirementItem } from "@/types";
import Card from "@/components/shared/Card";

interface AskModeViewProps {
  requirements: RequirementItem[];
}

const priorityColors: Record<string, string> = {
  must: "bg-red-100 text-red-700",
  should: "bg-amber-100 text-amber-700",
  could: "bg-blue-100 text-blue-700",
  wont: "bg-slate-100 text-slate-500",
};

const statusColors: Record<string, string> = {
  defined: "bg-slate-100 text-slate-600",
  approved: "bg-emerald-100 text-emerald-700",
  "in-progress": "bg-blue-100 text-blue-700",
  done: "bg-emerald-100 text-emerald-700",
};

export default function AskModeView({ requirements }: AskModeViewProps) {
  const mustHave = requirements.filter((r) => r.priority === "must");
  const shouldHave = requirements.filter((r) => r.priority === "should");
  const couldHave = requirements.filter((r) => r.priority === "could");

  return (
    <div className="space-y-6">
      <Card>
        <h3 className="text-lg font-semibold text-slate-900 mb-1">
          Requirement Summary
        </h3>
        <p className="text-sm text-slate-500 mb-4">
          Business goals, user needs, constraints, and dependencies gathered
          during the Ask phase.
        </p>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-slate-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-slate-900">
              {requirements.length}
            </div>
            <div className="text-xs text-slate-500 mt-1">Total Requirements</div>
          </div>
          <div className="bg-red-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-red-700">
              {mustHave.length}
            </div>
            <div className="text-xs text-slate-500 mt-1">Must Have</div>
          </div>
          <div className="bg-amber-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-amber-700">
              {shouldHave.length}
            </div>
            <div className="text-xs text-slate-500 mt-1">Should Have</div>
          </div>
          <div className="bg-blue-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-blue-700">
              {couldHave.length}
            </div>
            <div className="text-xs text-slate-500 mt-1">Could Have</div>
          </div>
        </div>
      </Card>

      <Card>
        <h3 className="text-lg font-semibold text-slate-900 mb-4">
          Requirements Breakdown
        </h3>
        <div className="space-y-3">
          {requirements.map((req) => (
            <div
              key={req.id}
              className="border border-slate-200 rounded-xl p-4 hover:border-slate-300 transition-colors"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-slate-900 text-sm">
                      {req.title}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${priorityColors[req.priority]}`}
                    >
                      {req.priority.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-sm text-slate-600">{req.description}</p>
                </div>
                <span
                  className={`px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap ${statusColors[req.status]}`}
                >
                  {req.status === "in-progress" ? "In Progress" : req.status.charAt(0).toUpperCase() + req.status.slice(1)}
                </span>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
