export type StageStatus = "complete" | "in-progress" | "pending" | "blocked";

export type StageName = "ask" | "plan" | "build" | "review" | "deploy";

export type ProjectStatus = "active" | "completed" | "on-hold" | "archived";

export type Severity = "critical" | "high" | "medium" | "low" | "info";

export type TrendDirection = "up" | "down" | "neutral";

export interface Stage {
  id: StageName;
  name: string;
  description: string;
  status: StageStatus;
  startedAt: string | null;
  completedAt: string | null;
}

export interface Metric {
  label: string;
  value: string | number;
  trend: string;
  trendDirection: TrendDirection;
}

export interface ReviewFinding {
  id: string;
  severity: Severity;
  title: string;
  description: string;
  file: string;
  line: number;
  status: "open" | "resolved" | "dismissed";
}

export interface DeployCheckItem {
  id: string;
  category: string;
  item: string;
  checked: boolean;
  notes: string;
}

export interface RequirementItem {
  id: string;
  title: string;
  description: string;
  priority: "must" | "should" | "could" | "wont";
  status: "defined" | "approved" | "in-progress" | "done";
}

export interface PlanSection {
  id: string;
  title: string;
  content: string;
  status: "draft" | "approved" | "revised";
}

export interface BuildTask {
  id: string;
  title: string;
  assignee: string;
  status: "todo" | "in-progress" | "done" | "blocked";
  progress: number;
}

export interface ActivityItem {
  id: string;
  projectName: string;
  action: string;
  user: string;
  timestamp: string;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  team: string;
  status: ProjectStatus;
  currentStage: StageName;
  stages: Stage[];
  metrics: {
    tokenSavings: number;
    riskAlerts: number;
    completionPercent: number;
  };
  createdAt: string;
  updatedAt: string;
}

export interface DocItem {
  id: string;
  title: string;
  category: string;
  description: string;
  lastUpdated: string;
}
