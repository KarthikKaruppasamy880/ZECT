"use client";

import { ProjectOrchestration } from "@/types";
import Card from "@/components/shared/Card";

interface OrchestrationSummaryProps {
  orchestration: ProjectOrchestration;
}

export default function OrchestrationSummary({ orchestration }: OrchestrationSummaryProps) {
  const { repositories, dependencies, events } = orchestration;

  const ciPassing = repositories.filter((r) => r.ciStatus === "passing").length;
  const ciFailing = repositories.filter((r) => r.ciStatus === "failing").length;
  const syncedRepos = repositories.filter((r) => r.syncStatus === "synced").length;
  const healthyDeps = dependencies.filter((d) => d.status === "healthy").length;
  const brokenDeps = dependencies.filter((d) => d.status === "broken").length;
  const warningDeps = dependencies.filter((d) => d.status === "warning").length;
  const criticalEvents = events.filter((e) => e.severity === "critical").length;

  const stats = [
    {
      label: "Repositories",
      value: repositories.length,
      sub: `${syncedRepos} synced`,
      color: "text-slate-900",
    },
    {
      label: "CI Status",
      value: `${ciPassing}/${repositories.length}`,
      sub: ciFailing > 0 ? `${ciFailing} failing` : "All passing",
      color: ciFailing > 0 ? "text-red-600" : "text-emerald-600",
    },
    {
      label: "Dependencies",
      value: dependencies.length,
      sub:
        brokenDeps > 0
          ? `${brokenDeps} broken`
          : warningDeps > 0
            ? `${warningDeps} warning`
            : `${healthyDeps} healthy`,
      color: brokenDeps > 0 ? "text-red-600" : warningDeps > 0 ? "text-amber-600" : "text-emerald-600",
    },
    {
      label: "Recent Events",
      value: events.length,
      sub: criticalEvents > 0 ? `${criticalEvents} critical` : "No critical",
      color: criticalEvents > 0 ? "text-red-600" : "text-slate-600",
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {stats.map((stat) => (
        <Card key={stat.label} className="text-center">
          <div className={`text-2xl font-bold ${stat.color}`}>{stat.value}</div>
          <div className="text-xs text-slate-500 mt-1">{stat.label}</div>
          <div className={`text-xs mt-0.5 ${stat.color}`}>{stat.sub}</div>
        </Card>
      ))}
    </div>
  );
}
