"use client";

import { OrchestrationEvent, Repository } from "@/types";
import Card from "@/components/shared/Card";
import { formatRelativeTime } from "@/lib/utils";

interface OrchestrationTimelineProps {
  events: OrchestrationEvent[];
  repositories: Repository[];
}

const eventTypeIcons: Record<string, { bg: string; label: string }> = {
  deploy: { bg: "bg-blue-100 text-blue-700", label: "Deploy" },
  "pr-merged": { bg: "bg-emerald-100 text-emerald-700", label: "PR Merged" },
  "ci-fail": { bg: "bg-red-100 text-red-700", label: "CI Failed" },
  "schema-change": { bg: "bg-amber-100 text-amber-700", label: "Schema" },
  "breaking-change": { bg: "bg-red-100 text-red-700", label: "Breaking" },
  sync: { bg: "bg-purple-100 text-purple-700", label: "Sync" },
};

const severityStyles: Record<string, string> = {
  info: "border-l-blue-400",
  warning: "border-l-amber-400",
  critical: "border-l-red-400",
};

export default function OrchestrationTimeline({ events, repositories }: OrchestrationTimelineProps) {
  const repoMap = new Map(repositories.map((r) => [r.id, r]));
  const sorted = [...events].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  return (
    <Card>
      <h3 className="text-lg font-semibold text-slate-900 mb-1">Orchestration Timeline</h3>
      <p className="text-sm text-slate-500 mb-4">
        Cross-repo events, deployments, breaking changes, and CI status updates.
      </p>

      <div className="space-y-3">
        {sorted.map((event) => {
          const repo = repoMap.get(event.repoId);
          const typeStyle = eventTypeIcons[event.type] || { bg: "bg-slate-100 text-slate-600", label: event.type };
          const severity = severityStyles[event.severity] || "border-l-slate-300";

          return (
            <div
              key={event.id}
              className={`border-l-4 ${severity} bg-white rounded-r-xl p-3 border border-slate-100`}
            >
              <div className="flex items-start justify-between gap-2 mb-1">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${typeStyle.bg}`}>
                    {typeStyle.label}
                  </span>
                  <span className="font-mono text-xs text-slate-500">
                    {repo?.name || event.repoId}
                  </span>
                </div>
                <span className="text-xs text-slate-400 whitespace-nowrap">
                  {formatRelativeTime(event.timestamp)}
                </span>
              </div>
              <p className="text-sm text-slate-700">{event.message}</p>
              {event.impactedRepoIds.length > 0 && (
                <div className="mt-2 flex items-center gap-1 flex-wrap">
                  <span className="text-xs text-slate-400">Impacts:</span>
                  {event.impactedRepoIds.map((id) => (
                    <span
                      key={id}
                      className="px-2 py-0.5 rounded-full text-xs font-mono bg-slate-100 text-slate-600"
                    >
                      {repoMap.get(id)?.name || id}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {events.length === 0 && (
        <div className="text-center py-8 text-slate-400 text-sm">
          No orchestration events recorded yet.
        </div>
      )}
    </Card>
  );
}
