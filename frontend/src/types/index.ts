export interface Repo {
  id: number;
  project_id: number;
  owner: string;
  repo_name: string;
  default_branch: string;
  ci_status: string;
  coverage_percent: number;
  last_synced: string | null;
}

export interface Project {
  id: number;
  name: string;
  description: string;
  team: string;
  status: string;
  current_stage: string;
  completion_percent: number;
  token_savings: number;
  risk_alerts: number;
  created_at: string;
  updated_at: string;
  repos: Repo[];
}

export interface Setting {
  id: number;
  key: string;
  value: string;
  setting_type: string;
  label: string;
  description: string;
  options: string;
}

export interface GitHubRepoInfo {
  full_name: string;
  name: string;
  owner: string;
  description: string | null;
  language: string | null;
  stars: number;
  forks: number;
  open_issues: number;
  default_branch: string;
  updated_at: string;
  html_url: string;
  private: boolean;
}

export interface GitHubPR {
  number: number;
  title: string;
  state: string;
  author: string;
  created_at: string;
  updated_at: string;
  merged_at: string | null;
  additions: number;
  deletions: number;
  changed_files: number;
  html_url: string;
  head_branch: string;
  base_branch: string;
  body: string | null;
}

export interface GitHubPRFile {
  filename: string;
  status: string;
  additions: number;
  deletions: number;
  changes: number;
  patch: string | null;
}

export interface GitHubCommit {
  sha: string;
  message: string;
  author: string;
  date: string;
  html_url: string;
  additions: number;
  deletions: number;
  files_changed: number;
}

export interface GitHubWorkflowRun {
  id: number;
  name: string;
  status: string;
  conclusion: string | null;
  head_branch: string;
  event: string;
  created_at: string;
  updated_at: string;
  html_url: string;
}

export interface AnalyticsOverview {
  total_projects: number;
  active_projects: number;
  completed_projects: number;
  avg_completion: number;
  avg_token_savings: number;
  total_risk_alerts: number;
  total_repos: number;
  stage_distribution: Record<string, number>;
}

export interface RepoAnalysisResult {
  owner: string;
  repo: string;
  full_name: string;
  description: string | null;
  language: string | null;
  default_branch: string;
  stars: number;
  forks: number;
  open_issues: number;
  tree: string[];
  readme_content: string | null;
  dependencies: Record<string, string[]>;
  architecture_notes: string[];
}

export interface BlueprintResult {
  prompt: string;
  token_estimate: number;
  repos_analyzed: number;
}

export interface FocusedBlueprintResult {
  prompt: string;
  token_estimate: number;
  focus_area: string;
  repo_name: string;
}

export interface TokenLogEntry {
  action: string;
  tokens: number;
  ts: number;
}

export interface TokenUsage {
  total_tokens: number;
  log: TokenLogEntry[];
}

export interface ApiKeyStatus {
  configured: boolean;
  scopes: string[];
  rate_limit_remaining: number;
  rate_limit_total: number;
}

export interface DocSection {
  title: string;
  content: string;
}

export interface DocGenResult {
  repo_name: string;
  sections: DocSection[];
  total_tokens: number;
}

// LLM Types
export interface AskResponse {
  answer: string;
  model: string;
  tokens_used: number;
}

export interface PlanResponse {
  plan: string;
  phases: string[];
  model: string;
  tokens_used: number;
}

export interface EnhanceBlueprintResponse {
  enhanced_prompt: string;
  model: string;
  tokens_used: number;
}

export interface LLMKeyStatus {
  configured: boolean;
  model: string;
}

export type Stage = "ask" | "plan" | "build" | "review" | "deploy";

export const STAGES: { key: Stage; label: string }[] = [
  { key: "ask", label: "Ask Mode" },
  { key: "plan", label: "Plan Mode" },
  { key: "build", label: "Build Phase" },
  { key: "review", label: "Review" },
  { key: "deploy", label: "Deploy" },
];
