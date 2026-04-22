"use client";

import { DeployCheckItem } from "@/types";
import Card from "@/components/shared/Card";

interface DeployReadinessViewProps {
  checklist: DeployCheckItem[];
}

export default function DeployReadinessView({
  checklist,
}: DeployReadinessViewProps) {
  const categories = Array.from(new Set(checklist.map((c) => c.category)));
  const checked = checklist.filter((c) => c.checked).length;
  const total = checklist.length;
  const readyPercent = total > 0 ? Math.round((checked / total) * 100) : 0;
  const isReady = checked === total;

  return (
    <div className="space-y-6">
      <Card>
        <h3 className="text-lg font-semibold text-slate-900 mb-1">
          Deployment Readiness
        </h3>
        <p className="text-sm text-slate-500 mb-4">
          Pre-deployment checklist covering infrastructure, CI/CD, security,
          monitoring, and communication requirements.
        </p>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
          <div
            className={`rounded-xl p-4 text-center ${isReady ? "bg-emerald-50" : "bg-amber-50"}`}
          >
            <div
              className={`text-2xl font-bold ${isReady ? "text-emerald-700" : "text-amber-700"}`}
            >
              {readyPercent}%
            </div>
            <div className="text-xs text-slate-500 mt-1">Ready</div>
          </div>
          <div className="bg-emerald-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-emerald-700">{checked}</div>
            <div className="text-xs text-slate-500 mt-1">Passed</div>
          </div>
          <div className="bg-red-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-red-700">
              {total - checked}
            </div>
            <div className="text-xs text-slate-500 mt-1">Remaining</div>
          </div>
        </div>

        <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${isReady ? "bg-emerald-500" : "bg-amber-500"}`}
            style={{ width: `${readyPercent}%` }}
          />
        </div>
      </Card>

      {categories.map((category) => {
        const items = checklist.filter((c) => c.category === category);
        const catChecked = items.filter((c) => c.checked).length;

        return (
          <Card key={category}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold text-slate-900">
                {category}
              </h3>
              <span className="text-xs text-slate-500">
                {catChecked}/{items.length} complete
              </span>
            </div>
            <div className="space-y-3">
              {items.map((item) => (
                <div
                  key={item.id}
                  className={`flex items-start gap-3 p-3 rounded-xl border transition-colors ${
                    item.checked
                      ? "bg-emerald-50/50 border-emerald-200"
                      : "bg-red-50/50 border-red-200"
                  }`}
                >
                  <div
                    className={`w-5 h-5 rounded-md flex items-center justify-center shrink-0 mt-0.5 ${
                      item.checked
                        ? "bg-emerald-500 text-white"
                        : "bg-white border-2 border-slate-300"
                    }`}
                  >
                    {item.checked && (
                      <svg
                        className="w-3 h-3"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={3}
                      >
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    )}
                  </div>
                  <div className="flex-1">
                    <div
                      className={`text-sm font-medium ${item.checked ? "text-slate-600" : "text-slate-900"}`}
                    >
                      {item.item}
                    </div>
                    {item.notes && (
                      <div className="text-xs text-slate-500 mt-0.5">
                        {item.notes}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        );
      })}
    </div>
  );
}
