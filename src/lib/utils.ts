import { StageStatus, StageName, Severity } from "@/types";

export function stageStatusColor(status: StageStatus): string {
  switch (status) {
    case "complete":
      return "bg-emerald-100 text-emerald-700";
    case "in-progress":
      return "bg-blue-100 text-blue-700";
    case "pending":
      return "bg-slate-100 text-slate-500";
    case "blocked":
      return "bg-red-100 text-red-700";
  }
}

export function stageStatusLabel(status: StageStatus): string {
  switch (status) {
    case "complete":
      return "Complete";
    case "in-progress":
      return "In Progress";
    case "pending":
      return "Pending";
    case "blocked":
      return "Blocked";
  }
}

export function severityColor(severity: Severity): string {
  switch (severity) {
    case "critical":
      return "bg-red-100 text-red-700 border-red-200";
    case "high":
      return "bg-orange-100 text-orange-700 border-orange-200";
    case "medium":
      return "bg-amber-100 text-amber-700 border-amber-200";
    case "low":
      return "bg-blue-100 text-blue-700 border-blue-200";
    case "info":
      return "bg-slate-100 text-slate-600 border-slate-200";
  }
}

export function stageLabel(stage: StageName): string {
  switch (stage) {
    case "ask":
      return "Ask Mode";
    case "plan":
      return "Plan Mode";
    case "build":
      return "Build Phase";
    case "review":
      return "Review";
    case "deploy":
      return "Deployment";
  }
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function formatRelativeTime(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDate(dateStr);
}

export const STAGE_ORDER: StageName[] = [
  "ask",
  "plan",
  "build",
  "review",
  "deploy",
];
