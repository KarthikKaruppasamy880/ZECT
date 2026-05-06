const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

import type {
  Project,
  Setting,
  AnalyticsOverview,
  GitHubRepoInfo,
  GitHubPR,
  GitHubPRFile,
  GitHubCommit,
  GitHubWorkflowRun,
  RepoAnalysisResult,
  BlueprintResult,
  FocusedBlueprintResult,
  TokenUsage,
  ApiKeyStatus,
  DocGenResult,
  AskResponse,
  PlanResponse,
  EnhanceBlueprintResponse,
  LLMKeyStatus,
  TokenDashboard,
  ReviewResponse,
} from "@/types";

// Projects
export const getProjects = (status?: string) =>
  request<Project[]>(`/api/projects${status ? `?status=${status}` : ""}`);
export const getProject = (id: number) => request<Project>(`/api/projects/${id}`);
export const createProject = (data: Partial<Project>) =>
  request<Project>("/api/projects", { method: "POST", body: JSON.stringify(data) });
export const updateProject = (id: number, data: Partial<Project>) =>
  request<Project>(`/api/projects/${id}`, { method: "PUT", body: JSON.stringify(data) });
export const deleteProject = (id: number) =>
  request<void>(`/api/projects/${id}`, { method: "DELETE" });

// Settings
export const getSettings = () => request<Setting[]>("/api/settings");
export const updateSetting = (key: string, value: string) =>
  request<Setting>(`/api/settings/${key}`, { method: "PUT", body: JSON.stringify({ value }) });

// Analytics
export const getAnalytics = () => request<AnalyticsOverview>("/api/analytics/overview");
export const getTokenDashboard = () => request<TokenDashboard>("/api/analytics/token-dashboard");

// GitHub
export const getGitHubRepos = (owner: string) =>
  request<GitHubRepoInfo[]>(`/api/github/repos/${owner}`);
export const getGitHubRepo = (owner: string, repo: string) =>
  request<GitHubRepoInfo>(`/api/github/repos/${owner}/${repo}`);
export const getGitHubPulls = (owner: string, repo: string, state = "all") =>
  request<GitHubPR[]>(`/api/github/repos/${owner}/${repo}/pulls?state=${state}`);
export const getGitHubPull = (owner: string, repo: string, number: number) =>
  request<GitHubPR>(`/api/github/repos/${owner}/${repo}/pulls/${number}`);
export const getGitHubPullFiles = (owner: string, repo: string, number: number) =>
  request<GitHubPRFile[]>(`/api/github/repos/${owner}/${repo}/pulls/${number}/files`);
export const getGitHubCommits = (owner: string, repo: string) =>
  request<GitHubCommit[]>(`/api/github/repos/${owner}/${repo}/commits`);
export const getGitHubWorkflowRuns = (owner: string, repo: string) =>
  request<GitHubWorkflowRun[]>(`/api/github/repos/${owner}/${repo}/actions/runs`);

// Repo Analysis
export const analyzeRepo = (owner: string, repo: string) =>
  request<RepoAnalysisResult>("/api/analysis/repo", { method: "POST", body: JSON.stringify({ owner, repo }) });
export const analyzeMultiRepo = (repos: { owner: string; repo: string }[]) =>
  request<RepoAnalysisResult[]>("/api/analysis/multi-repo", { method: "POST", body: JSON.stringify({ repos }) });
export const generateBlueprint = (repos: { owner: string; repo: string }[]) =>
  request<BlueprintResult>("/api/analysis/blueprint", { method: "POST", body: JSON.stringify({ repos }) });
export const generateFocusedBlueprint = (owner: string, repo: string, focus_area: string, goal?: string) =>
  request<FocusedBlueprintResult>("/api/analysis/blueprint/focused", {
    method: "POST",
    body: JSON.stringify({ owner, repo, focus_area, ...(goal ? { goal } : {}) }),
  });
export const getTokenUsage = () => request<TokenUsage>("/api/analysis/tokens");
export const configureApiKey = (github_token: string) =>
  request<ApiKeyStatus>("/api/analysis/api-key", { method: "POST", body: JSON.stringify({ github_token }) });
export const getApiKeyStatus = () => request<ApiKeyStatus>("/api/analysis/api-key/status");

// Documentation Generation
export const generateDocs = (owner: string, repo: string, sections?: string[]) =>
  request<DocGenResult>("/api/analysis/docs/generate", {
    method: "POST",
    body: JSON.stringify({ owner, repo, ...(sections ? { sections } : {}) }),
  });

// LLM
export const askQuestion = (question: string, repo_context?: string) =>
  request<AskResponse>("/api/llm/ask", {
    method: "POST",
    body: JSON.stringify({ question, ...(repo_context ? { repo_context } : {}) }),
  });
export const generatePlan = (project_description: string, repo_context?: string, constraints?: string) =>
  request<PlanResponse>("/api/llm/plan", {
    method: "POST",
    body: JSON.stringify({ project_description, ...(repo_context ? { repo_context } : {}), ...(constraints ? { constraints } : {}) }),
  });
export const enhanceBlueprint = (raw_blueprint: string, instructions?: string) =>
  request<EnhanceBlueprintResponse>("/api/llm/enhance-blueprint", {
    method: "POST",
    body: JSON.stringify({ raw_blueprint, ...(instructions ? { instructions } : {}) }),
  });
export const configureLLMKey = (openai_api_key: string) =>
  request<LLMKeyStatus>("/api/llm/configure-key", { method: "POST", body: JSON.stringify({ openai_api_key }) });
export const getLLMStatus = () => request<LLMKeyStatus>("/api/llm/status");

// Code Review
export const reviewPR = (owner: string, repo: string, pr_number: number) =>
  request<ReviewResponse>("/api/review/pr", {
    method: "POST",
    body: JSON.stringify({ owner, repo, pr_number }),
  });
export const reviewSnippet = (code: string, language?: string) =>
  request<ReviewResponse>("/api/review/snippet", {
    method: "POST",
    body: JSON.stringify({ code, ...(language ? { language } : {}) }),
  });

// Build Phase
export const buildGenerate = (plan_step: string, tech_stack?: string, project_context?: string, file_path?: string) =>
  request<any>("/api/build/generate", {
    method: "POST",
    body: JSON.stringify({ plan_step, ...(tech_stack ? { tech_stack } : {}), ...(project_context ? { project_context } : {}), ...(file_path ? { file_path } : {}) }),
  });
export const buildFromPlan = (full_plan: string, step_index: number, tech_stack?: string) =>
  request<any>("/api/build/from-plan", {
    method: "POST",
    body: JSON.stringify({ full_plan, step_index, ...(tech_stack ? { tech_stack } : {}) }),
  });

// Review Phase
export const reviewAnalyze = (code: string, language?: string, severity_threshold?: string) =>
  request<any>("/api/review/analyze", {
    method: "POST",
    body: JSON.stringify({ code, language: language || "typescript", severity_threshold: severity_threshold || "medium" }),
  });
export const reviewFixPrompt = (code: string, findings: any[], language?: string) =>
  request<any>("/api/review/fix-prompt", {
    method: "POST",
    body: JSON.stringify({ code, findings, language: language || "typescript" }),
  });

// Deploy Phase
export const deployChecklist = (project_name: string, tech_stack?: string, environment?: string, deployment_type?: string) =>
  request<any>("/api/deploy/checklist", {
    method: "POST",
    body: JSON.stringify({ project_name, ...(tech_stack ? { tech_stack } : {}), environment: environment || "production", deployment_type: deployment_type || "standard" }),
  });
export const deployRunbook = (project_name: string, tech_stack?: string, infrastructure?: string, services?: string[]) =>
  request<any>("/api/deploy/runbook", {
    method: "POST",
    body: JSON.stringify({ project_name, ...(tech_stack ? { tech_stack } : {}), ...(infrastructure ? { infrastructure } : {}), ...(services ? { services } : {}) }),
  });

// Skills
export const getSkills = (category?: string, repoId?: number, scope?: string) => {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  if (repoId) params.set("repo_id", String(repoId));
  if (scope) params.set("scope", scope);
  const qs = params.toString();
  return request<any[]>(`/api/skills${qs ? `?${qs}` : ""}`);
};
export const createSkill = (data: any) =>
  request<any>("/api/skills", { method: "POST", body: JSON.stringify(data) });
export const updateSkill = (id: number, data: any) =>
  request<any>(`/api/skills/${id}`, { method: "PUT", body: JSON.stringify(data) });
export const deleteSkill = (id: number) =>
  request<void>(`/api/skills/${id}`, { method: "DELETE" });
export const detectSkillPatterns = (code: string, context?: string) =>
  request<any>("/api/skills/detect", {
    method: "POST",
    body: JSON.stringify({ code, ...(context ? { context } : {}) }),
  });

// Repos (for skill scoping)
export const getRepos = () => request<any[]>("/api/projects").then((projects: any[]) =>
  projects.flatMap((p: any) => (p.repos || []).map((r: any) => ({ ...r, project_name: p.name })))
);

// Token Controls
export const getTokenUsageFull = () => request<any>("/api/tokens/usage");
export const getTokenBudget = (userId?: number) =>
  request<any>(`/api/tokens/budget${userId ? `?user_id=${userId}` : ""}`);
export const updateTokenBudget = (config: any, userId?: number) =>
  request<any>(`/api/tokens/budget${userId ? `?user_id=${userId}` : ""}`, { method: "PUT", body: JSON.stringify(config) });
export const getModelBreakdown = (userId?: number) =>
  request<any[]>(`/api/tokens/models${userId ? `?user_id=${userId}` : ""}`);
export const getUsersActivity = () => request<any[]>("/api/tokens/users");
export const getUserActivityDetail = (userId: number) => request<any>(`/api/tokens/users/${userId}`);
export const getTeamUsage = () => request<any[]>("/api/tokens/teams");
export const getUsageTrends = (days?: number, userId?: number) => {
  const params = new URLSearchParams();
  if (days) params.set("days", String(days));
  if (userId) params.set("user_id", String(userId));
  const qs = params.toString();
  return request<any[]>(`/api/tokens/trends${qs ? `?${qs}` : ""}`);
};
export const checkTokenLimit = (userId?: number) =>
  request<any>(`/api/tokens/check-limit${userId ? `?user_id=${userId}` : ""}`);

// App Runner
export const runnerExecute = (command: string, cwd?: string, timeout?: number) =>
  request<any>("/api/runner/execute", {
    method: "POST",
    body: JSON.stringify({ command, ...(cwd ? { cwd } : {}), ...(timeout ? { timeout } : {}) }),
  });
export const runnerStart = (command: string, cwd?: string, label?: string, env_vars?: Record<string, string>) =>
  request<any>("/api/runner/start", {
    method: "POST",
    body: JSON.stringify({ command, ...(cwd ? { cwd } : {}), ...(label ? { label } : {}), ...(env_vars ? { env_vars } : {}) }),
  });
export const runnerStop = (processId: string) =>
  request<any>(`/api/runner/stop/${processId}`, { method: "POST" });
export const runnerProcesses = () => request<any[]>("/api/runner/processes");
export const runnerOutput = (processId: string, offset?: number, limit?: number) => {
  const params = new URLSearchParams();
  if (offset !== undefined) params.set("offset", String(offset));
  if (limit !== undefined) params.set("limit", String(limit));
  const qs = params.toString();
  return request<any>(`/api/runner/output/${processId}${qs ? `?${qs}` : ""}`);
};
export const runnerRemoveProcess = (processId: string) =>
  request<any>(`/api/runner/processes/${processId}`, { method: "DELETE" });
export const runnerConfigure = (repo_path: string, opts?: { env_vars?: Record<string, string>; startup_command?: string; install_command?: string; preview_port?: number }) =>
  request<any>("/api/runner/configure", {
    method: "POST",
    body: JSON.stringify({ repo_path, ...opts }),
  });

// File Explorer
export const fileList = (path: string, showHidden = false) =>
  request<any[]>(`/api/files/list?path=${encodeURIComponent(path)}&show_hidden=${showHidden}`);
export const fileRead = (path: string) =>
  request<any>(`/api/files/read?path=${encodeURIComponent(path)}`);
export const fileWrite = (path: string, content: string, createDirs = true) =>
  request<any>("/api/files/write", {
    method: "POST",
    body: JSON.stringify({ path, content, create_dirs: createDirs }),
  });
export const fileCreate = (path: string, content = "", createDirs = true) =>
  request<any>("/api/files/create", {
    method: "POST",
    body: JSON.stringify({ path, content, create_dirs: createDirs }),
  });
export const fileDelete = (path: string) =>
  request<any>(`/api/files/delete?path=${encodeURIComponent(path)}`, { method: "DELETE" });
export const fileRename = (oldPath: string, newPath: string) =>
  request<any>("/api/files/rename", {
    method: "POST",
    body: JSON.stringify({ old_path: oldPath, new_path: newPath }),
  });
export const fileSearch = (directory: string, pattern: string, fileExtensions?: string[], maxResults = 50) =>
  request<any[]>("/api/files/search", {
    method: "POST",
    body: JSON.stringify({ directory, pattern, ...(fileExtensions ? { file_extensions: fileExtensions } : {}), max_results: maxResults }),
  });
export const fileTree = (path: string, depth = 3) =>
  request<any[]>(`/api/files/tree?path=${encodeURIComponent(path)}&depth=${depth}`);

// Git Operations
export const gitStatus = (repoPath: string) =>
  request<any>(`/api/git/status?repo_path=${encodeURIComponent(repoPath)}`);
export const gitAdd = (repoPath: string, files?: string[]) =>
  request<any>(`/api/git/add?repo_path=${encodeURIComponent(repoPath)}`, {
    method: "POST",
    ...(files ? { body: JSON.stringify(files) } : {}),
  });
export const gitCommit = (repoPath: string, message: string, files?: string[]) =>
  request<any>("/api/git/commit", {
    method: "POST",
    body: JSON.stringify({ repo_path: repoPath, message, ...(files ? { files } : {}) }),
  });
export const gitPush = (repoPath: string, remote = "origin", branch?: string) =>
  request<any>("/api/git/push", {
    method: "POST",
    body: JSON.stringify({ repo_path: repoPath, remote, ...(branch ? { branch } : {}) }),
  });
export const gitBranch = (repoPath: string, branchName: string, checkout = true, fromBranch?: string) =>
  request<any>("/api/git/branch", {
    method: "POST",
    body: JSON.stringify({ repo_path: repoPath, branch_name: branchName, checkout, ...(fromBranch ? { from_branch: fromBranch } : {}) }),
  });
export const gitCheckout = (repoPath: string, branch: string) =>
  request<any>("/api/git/checkout", {
    method: "POST",
    body: JSON.stringify({ repo_path: repoPath, branch }),
  });
export const gitDiff = (repoPath: string, staged = false) =>
  request<any>(`/api/git/diff?repo_path=${encodeURIComponent(repoPath)}&staged=${staged}`);
export const gitLog = (repoPath: string, limit = 20) =>
  request<any[]>(`/api/git/log?repo_path=${encodeURIComponent(repoPath)}&limit=${limit}`);
export const gitBranches = (repoPath: string) =>
  request<any>(`/api/git/branches?repo_path=${encodeURIComponent(repoPath)}`);
export const gitPull = (repoPath: string) =>
  request<any>(`/api/git/pull?repo_path=${encodeURIComponent(repoPath)}`, { method: "POST" });
export const gitCreatePR = (repoPath: string, title: string, body = "", baseBranch = "main", headBranch?: string) =>
  request<any>("/api/git/create-pr", {
    method: "POST",
    body: JSON.stringify({ repo_path: repoPath, title, body, base_branch: baseBranch, ...(headBranch ? { head_branch: headBranch } : {}) }),
  });

// CI/CD Monitor
export const ciRuns = (owner: string, repo: string, branch?: string, limit = 10) =>
  request<any[]>(`/api/ci/runs/${owner}/${repo}?limit=${limit}${branch ? `&branch=${branch}` : ""}`);
export const ciJobs = (owner: string, repo: string, runId: number) =>
  request<any[]>(`/api/ci/runs/${owner}/${repo}/${runId}/jobs`);
export const ciLogs = (owner: string, repo: string, runId: number) =>
  request<any>(`/api/ci/runs/${owner}/${repo}/${runId}/logs`);
export const ciAnalyzeFailure = (owner: string, repo: string, runId: number) =>
  request<any[]>("/api/ci/analyze-failure", {
    method: "POST",
    body: JSON.stringify({ owner, repo, run_id: runId }),
  });
export const ciStatusBadge = (owner: string, repo: string, branch = "main") =>
  request<any>(`/api/ci/status/${owner}/${repo}?branch=${branch}`);

// Auto-Fix
export const autofixAnalyze = (errorOutput: string, command?: string, filePath?: string, fileContent?: string, language?: string) =>
  request<any>("/api/autofix/analyze", {
    method: "POST",
    body: JSON.stringify({
      error_output: errorOutput,
      ...(command ? { command } : {}),
      ...(filePath ? { file_path: filePath } : {}),
      ...(fileContent ? { file_content: fileContent } : {}),
      ...(language ? { language } : {}),
    }),
  });
export const autofixRunAndFix = (command: string, cwd?: string, errorOutput?: string, filePath?: string, maxRetries = 3) =>
  request<any>("/api/autofix/run-and-fix", {
    method: "POST",
    body: JSON.stringify({
      command,
      ...(cwd ? { cwd } : {}),
      ...(errorOutput ? { error_output: errorOutput } : {}),
      ...(filePath ? { file_path: filePath } : {}),
      max_retries: maxRetries,
    }),
  });
export const autofixApply = (filePath: string, originalContent: string, fixCode: string, fixType: string, lineNumber?: number) =>
  request<any>("/api/autofix/apply-fix", {
    method: "POST",
    body: JSON.stringify({
      file_path: filePath,
      original_content: originalContent,
      fix_code: fixCode,
      fix_type: fixType,
      ...(lineNumber ? { line_number: lineNumber } : {}),
    }),
  });

// Inline PR Review
export const reviewPRInline = (owner: string, repo: string, prNumber: number, autoComment = true) =>
  request<any>("/api/review/pr/inline", {
    method: "POST",
    body: JSON.stringify({ owner, repo, pr_number: prNumber, auto_comment: autoComment }),
  });
export const postPRComment = (owner: string, repo: string, prNumber: number, body: string, commitSha?: string, path?: string, line?: number) =>
  request<any>("/api/review/pr/comment", {
    method: "POST",
    body: JSON.stringify({
      owner, repo, pr_number: prNumber, body,
      ...(commitSha ? { commit_sha: commitSha } : {}),
      ...(path ? { path } : {}),
      ...(line ? { line } : {}),
    }),
  });
export const getPRComments = (owner: string, repo: string, prNumber: number) =>
  request<any[]>(`/api/review/pr/${owner}/${repo}/${prNumber}/comments`);

// Auth
export const login = (username: string, password: string) =>
  request<{ token: string; username: string }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
export const verifyToken = (token: string) =>
  request<{ valid: boolean; username: string }>(`/api/auth/verify?token=${token}`);
export const logout = (token: string) =>
  request<{ status: string }>(`/api/auth/logout?token=${token}`, { method: "POST" });
