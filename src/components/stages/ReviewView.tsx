"use client";

import { ReviewFinding } from "@/types";
import Card from "@/components/shared/Card";
import SeverityBadge from "@/components/shared/SeverityBadge";

interface ReviewViewProps {
  findings: ReviewFinding[];
}

const findingStatusStyles: Record<string, string> = {
  open: "bg-amber-100 text-amber-700",
  resolved: "bg-emerald-100 text-emerald-700",
  dismissed: "bg-slate-100 text-slate-500",
};

export default function ReviewView({ findings }: ReviewViewProps) {
  const open = findings.filter((f) => f.status === "open").length;
  const resolved = findings.filter((f) => f.status === "resolved").length;
  const critical = findings.filter(
    (f) => f.severity === "critical" && f.status === "open"
  ).length;
  const high = findings.filter(
    (f) => f.severity === "high" && f.status === "open"
  ).length;

  return (
    <div className="space-y-6">
      <Card>
        <h3 className="text-lg font-semibold text-slate-900 mb-1">
          Review Summary
        </h3>
        <p className="text-sm text-slate-500 mb-4">
          Automated code analysis findings including defect checks, missing
          tests, security issues, and configuration review.
        </p>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-slate-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-slate-900">
              {findings.length}
            </div>
            <div className="text-xs text-slate-500 mt-1">Total Findings</div>
          </div>
          <div className="bg-amber-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-amber-700">{open}</div>
            <div className="text-xs text-slate-500 mt-1">Open</div>
          </div>
          <div className="bg-emerald-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-emerald-700">{resolved}</div>
            <div className="text-xs text-slate-500 mt-1">Resolved</div>
          </div>
          <div className="bg-red-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-red-700">{critical}</div>
            <div className="text-xs text-slate-500 mt-1">Critical</div>
          </div>
          <div className="bg-orange-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-orange-700">{high}</div>
            <div className="text-xs text-slate-500 mt-1">High</div>
          </div>
        </div>

        {(critical > 0 || high > 0) && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-xl">
            <p className="text-sm text-red-700 font-medium">
              {critical + high} critical/high severity finding
              {critical + high !== 1 ? "s" : ""} must be resolved before
              deployment.
            </p>
          </div>
        )}
      </Card>

      <Card>
        <h3 className="text-lg font-semibold text-slate-900 mb-4">
          All Findings
        </h3>
        {findings.length === 0 ? (
          <div className="text-center py-8">
            <div className="text-slate-400 text-sm">No review findings yet. Code review has not started for this project.</div>
          </div>
        ) : (
        <div className="space-y-3">
          {findings.map((finding) => (
            <div
              key={finding.id}
              className="border border-slate-200 rounded-xl p-4 hover:border-slate-300 transition-colors"
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="flex items-center gap-2">
                  <SeverityBadge severity={finding.severity} />
                  <span className="font-medium text-sm text-slate-900">
                    {finding.title}
                  </span>
                </div>
                <span
                  className={`px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap ${findingStatusStyles[finding.status]}`}
                >
                  {finding.status.charAt(0).toUpperCase() + finding.status.slice(1)}
                </span>
              </div>
              <p className="text-sm text-slate-600 mb-2">
                {finding.description}
              </p>
              <div className="text-xs text-slate-400 font-mono">
                {finding.file}:{finding.line}
              </div>
            </div>
          ))}
        </div>
        )}
      </Card>
    </div>
  );
}
