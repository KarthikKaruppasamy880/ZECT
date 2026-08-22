// Prefer 127.0.0.1 — Electron/Windows can hang on localhost → IPv6 (::1)
// Canonical packaged/default API port is :8000. Dev stacks may override via VITE_API_URL
// (e.g. scripts/start-local.ps1 writes :8020 into frontend/.env.local).
function bakedApiBase(): string {
  return import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
}

/** Runtime origin for controlled native headed proof. Loopback only. */
export function getApiBase(): string {
  const baked = bakedApiBase();
  if (typeof window === "undefined") return baked;
  try {
    const raw = sessionStorage.getItem("zect_api_origin") || "";
    if (!raw) return baked;
    const parsed = new URL(raw);
    if (!["127.0.0.1", "localhost"].includes(parsed.hostname)) return baked;
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return baked;
    return parsed.origin;
  } catch {
    return baked;
  }
}

const API = bakedApiBase();

/** Bearer + JSON headers for authenticated API calls. */
export function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...extra,
  };
  const token = typeof localStorage !== "undefined" ? localStorage.getItem("zect_token") : null;
  if (token && !headers.Authorization) {
    headers.Authorization = `Bearer ${token}`;
  }
  try {
    const key = "zect-correlation-id";
    let cid = typeof sessionStorage !== "undefined" ? sessionStorage.getItem(key) : null;
    if (!cid) {
      cid = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `zect-${Date.now()}`;
      if (typeof sessionStorage !== "undefined") sessionStorage.setItem(key, cid);
    }
    if (!headers["X-Correlation-Id"]) headers["X-Correlation-Id"] = cid;
  } catch {
    /* sessionStorage may be unavailable */
  }
  return headers;
}

/** Low-level fetch with auth — use when callers need res.ok / status handling. */
export async function apiFetch(path: string, opts?: RequestInit): Promise<Response> {
  const headers = authHeaders(opts?.headers as Record<string, string> | undefined);
  return fetch(`${getApiBase()}${path}`, { ...opts, headers });
}

export async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await apiFetch(path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = err.detail;
    if (detail && typeof detail === "object") {
      const msg =
        detail.hint ||
        detail.error ||
        detail.message ||
        detail.detail ||
        res.statusText;
      const e = new Error(typeof msg === "string" ? msg : res.statusText) as Error & {
        detail?: unknown;
      };
      e.detail = detail;
      throw e;
    }
    throw new Error(typeof detail === "string" ? detail : detail?.message || res.statusText);
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
export const createSampleProcess = () =>
  request<{
    ok: boolean;
    created: boolean;
    project_id: number;
    work_item: { id: number; title: string; source: string; project_id?: number };
    note?: string;
  }>("/api/work-items/sample-process", { method: "POST" });

export const ingestWorkItem = (body: {
  source: string;
  external_id: string;
  raw?: Record<string, unknown>;
  project_id?: number | null;
  repository_id?: number | null;
  repository_ref?: string;
  require_repo?: boolean;
}) =>
  request<{
    work_item: { id: number; title: string; source: string; status: string; project_id?: number };
    needs_human: boolean;
    missing_repository_identity: boolean;
  }>("/api/work-items/ingest", { method: "POST", body: JSON.stringify(body) });

export type WorkItemRecord = {
  id: number;
  title: string;
  status: string;
  source?: string;
  external_id?: string;
  project_id?: number | null;
  repository_id?: number | null;
  repository_ref?: string;
  base_commit_sha?: string;
  plan_hash?: string;
  plan_version?: number;
  approved_plan_hash?: string;
  mentrix_run_id?: number | null;
  worktree_path?: string;
  current_commit_sha?: string;
  description?: string;
};

export const getWorkItem = (id: number) => request<WorkItemRecord>(`/api/work-items/${id}`);

export const getWorkItemEvents = (id: number) =>
  request<{
    events: Array<{ id: number; event_type: string; payload?: Record<string, unknown>; created_at?: string | null }>;
  }>(`/api/work-items/${id}/events`);

export const developerAsk = (body: {
  question: string;
  work_item_id?: number;
  project_id?: number | null;
  repository_id?: number | null;
}) =>
  request<{ work_item_id: number; answer?: string; status?: string }>("/api/mentrix/developer/ask", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const developerPlan = (body: {
  goal: string;
  work_item_id?: number;
  project_id?: number | null;
  repository_id?: number | null;
}) =>
  request<{ work_item_id: number; plan_hash?: string; plan_version?: number; status?: string }>(
    "/api/mentrix/developer/plan",
    { method: "POST", body: JSON.stringify(body) },
  );
export const getProjects = (status?: string, opts?: { includeFixtures?: boolean }) => {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (!opts?.includeFixtures) params.set("exclude_fixtures", "1");
  const q = params.toString();
  return request<Project[]>(`/api/projects${q ? `?${q}` : ""}`);
};
export const getProject = (id: number) => request<Project>(`/api/projects/${id}`);
export const getProjectFixtureAudit = () =>
  request<{
    ok: boolean;
    proven_test: Array<{ id: number; name: string; provenance: string; test_run_id: string }>;
    name_candidates: Array<{ id: number; name: string; provenance: string; test_run_id: string }>;
    authorized: Array<{ id: number; name: string }>;
    note?: string;
  }>("/api/projects/fixtures/audit");
export const createProject = (data: Partial<Project>) =>
  request<Project>("/api/projects", { method: "POST", body: JSON.stringify(data) });
export const updateProject = (id: number, data: Partial<Project>) =>
  request<Project>(`/api/projects/${id}`, { method: "PUT", body: JSON.stringify(data) });
export const deleteProject = (id: number) =>
  request<void>(`/api/projects/${id}`, { method: "DELETE" });
export const keepCleanupProjects = (keepIds: number[], dryRun = true) =>
  request<{
    ok: boolean;
    dry_run: boolean;
    would_keep?: Array<{ id: number; name: string }>;
    would_delete?: Array<{ id: number; name: string }>;
    deleted_ids?: number[];
    kept_ids?: number[];
    count?: number;
    error?: string;
  }>("/api/projects/fixtures/keep-cleanup", {
    method: "POST",
    body: JSON.stringify({ keep_ids: keepIds, dry_run: dryRun }),
  });
export const addProjectRepo = (
  projectId: number,
  data: { owner?: string; repo_name?: string; default_branch?: string; repo_id?: number },
) =>
  request<Project>(`/api/projects/${projectId}/repos`, {
    method: "POST",
    body: JSON.stringify(data),
  });

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
export const askQuestion = (
  question: string,
  repo_context?: string,
  repo_id?: number,
  model?: string,
  project_id?: number,
) =>
  request<AskResponse>("/api/llm/ask", {
    method: "POST",
    body: JSON.stringify({
      question,
      ...(repo_context ? { repo_context } : {}),
      ...(repo_id != null ? { repo_id } : {}),
      ...(model ? { model } : {}),
      ...(project_id != null ? { project_id } : {}),
    }),
  });
export const generatePlan = (
  project_description: string,
  repo_context?: string,
  constraints?: string,
  repo_id?: number,
  model?: string,
  project_id?: number,
) =>
  request<PlanResponse>("/api/llm/plan", {
    method: "POST",
    body: JSON.stringify({
      project_description,
      ...(repo_context ? { repo_context } : {}),
      ...(constraints ? { constraints } : {}),
      ...(repo_id != null ? { repo_id } : {}),
      ...(model ? { model } : {}),
      ...(project_id != null ? { project_id } : {}),
    }),
  });
export const enhanceBlueprint = (raw_blueprint: string, instructions?: string) =>
  request<EnhanceBlueprintResponse>("/api/llm/enhance-blueprint", {
    method: "POST",
    body: JSON.stringify({ raw_blueprint, ...(instructions ? { instructions } : {}) }),
  });
export const configureLLMKey = (openai_api_key: string) =>
  request<LLMKeyStatus>("/api/llm/configure-key", { method: "POST", body: JSON.stringify({ openai_api_key }) });
export const getLLMStatus = () => request<LLMKeyStatus>("/api/llm/status");

export type MentrixLlmGatewayStatus = {
  configured: boolean;
  online: boolean;
  base_url?: string;
  models?: string[];
  label?: string;
  detail?: string;
  default_model?: string;
};

export const getMentrixLlmGateway = () =>
  request<MentrixLlmGatewayStatus>("/api/models/gateway");

// Context store (cross-page workflow persistence)
export type ContextEntry = { key: string; value: string; page: string; expires_at?: string | null };
export type SessionContext = { page: string; entries: ContextEntry[]; total_tokens_estimated: number };

export const saveContext = (page: string, key: string, value: string) =>
  request<{ saved: boolean; page: string; key: string }>("/api/context/save", {
    method: "POST",
    body: JSON.stringify({ page, key, value }),
  });

export const loadContext = (page: string, keys?: string[]) =>
  request<SessionContext>("/api/context/load", {
    method: "POST",
    body: JSON.stringify({ page, keys: keys ?? null }),
  });

export const clearContext = (page: string) =>
  request<{ cleared: boolean; page: string }>(`/api/context/clear/${encodeURIComponent(page)}`, {
    method: "DELETE",
  });

export const getContextRecommendations = (page: string) =>
  request<{ page: string; recommended_keys: string[]; currently_loaded: string[] }>(
    `/api/context/recommendations/${encodeURIComponent(page)}`,
  );

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

// Full Repo Scan
export const reviewRepo = (owner: string, repo: string, branch?: string, filePatterns?: string[]) =>
  request<any>("/api/review/repo", {
    method: "POST",
    body: JSON.stringify({ owner, repo, ...(branch ? { branch } : {}), ...(filePatterns ? { file_patterns: filePatterns } : {}) }),
  });

// Auto-Fix Loop
export const reviewAutoFixLoop = (owner: string, repo: string, prNumber: number, maxIterations = 3, autoComment = true) =>
  request<any>("/api/review/auto-fix-loop", {
    method: "POST",
    body: JSON.stringify({ owner, repo, pr_number: prNumber, max_iterations: maxIterations, auto_comment: autoComment }),
  });

// Review + Rules Engine
export const reviewEvaluateRules = (owner: string, repo: string, prNumber: number) =>
  request<any>("/api/review/evaluate-rules", {
    method: "POST",
    body: JSON.stringify({ owner, repo, pr_number: prNumber }),
  });

// Webhook Config
export const configureWebhook = (owner: string, repo: string, enabled: boolean, autoReview: boolean, autoComment: boolean, webhookSecret = "") =>
  request<any>("/api/review/webhook/configure", {
    method: "POST",
    body: JSON.stringify({ owner, repo, enabled, auto_review: autoReview, auto_comment: autoComment, webhook_secret: webhookSecret }),
  });
export const getWebhookConfig = (owner: string, repo: string) =>
  request<any>(`/api/review/webhook/configure/${owner}/${repo}`);
export const listWebhookConfigs = () =>
  request<any[]>("/api/review/webhook/configs");

// Build Phase
export const buildGenerate = (plan_step: string, tech_stack?: string, project_context?: string, file_path?: string, repo_id?: number) =>
  request<any>("/api/build/generate", {
    method: "POST",
    body: JSON.stringify({ plan_step, ...(tech_stack ? { tech_stack } : {}), ...(project_context ? { project_context } : {}), ...(file_path ? { file_path } : {}), ...(repo_id ? { repo_id } : {}) }),
  });
export const buildApply = (repo_id: number, file_path: string, code: string, commit_message?: string) =>
  request<any>("/api/build/apply", {
    method: "POST",
    body: JSON.stringify({ repo_id, file_path, code, ...(commit_message ? { commit_message } : {}) }),
  });
export const buildGenerateMulti = (plan_step: string, target_files: string[], repo_id?: number, tech_stack?: string) =>
  request<any>("/api/build/generate-multi", {
    method: "POST",
    body: JSON.stringify({ plan_step, target_files, ...(repo_id ? { repo_id } : {}), ...(tech_stack ? { tech_stack } : {}) }),
  });
export const buildApplyMulti = (repo_id: number, files: { file_path: string; code: string }[], commit_message?: string) =>
  request<any>("/api/build/apply-multi", {
    method: "POST",
    body: JSON.stringify({ repo_id, files, ...(commit_message ? { commit_message } : {}) }),
  });
export const buildVerifyAndFix = (repo_id: number, test_command: string, max_retries?: number) =>
  request<any>("/api/build/verify-and-fix", {
    method: "POST",
    body: JSON.stringify({ repo_id, test_command, ...(max_retries ? { max_retries } : {}) }),
  });
export const buildFromPlan = (full_plan: string, step_index: number, tech_stack?: string) =>
  request<any>("/api/build/from-plan", {
    method: "POST",
    body: JSON.stringify({ full_plan, step_index, ...(tech_stack ? { tech_stack } : {}) }),
  });

// Review Phase
export const reviewAnalyze = (code: string, language?: string, severity_threshold?: string) =>
  request<any>("/api/review-phase/analyze", {
    method: "POST",
    body: JSON.stringify({ code, language: language || "typescript", severity_threshold: severity_threshold || "medium" }),
  });
export const reviewFixPrompt = (code: string, findings: any[], language?: string) =>
  request<any>("/api/review-phase/fix-prompt", {
    method: "POST",
    body: JSON.stringify({ code, findings, language: language || "typescript" }),
  });

// Lattice
export const latticeIngest = (path: string, project_key?: string, index_rag = true, force = false) =>
  request<any>("/api/lattice/ingest", {
    method: "POST",
    body: JSON.stringify({ path, project_key: project_key || path, index_rag, force }),
  });
export const latticeSnapshot = (project_key: string, repository_id?: number) => {
  const qs = new URLSearchParams({ project_key });
  if (repository_id) qs.set("repository_id", String(repository_id));
  return request<any>(`/api/lattice/snapshot?${qs.toString()}`);
};
export const latticeGraph = (project_key: string, layer = "combined") =>
  request<any>(
    `/api/lattice/graph?project_key=${encodeURIComponent(project_key)}&layer=${encodeURIComponent(layer)}`,
  );
export const latticeBacklinks = (project_key: string, doc: string, limit = 50) =>
  request<any>(
    `/api/lattice/graph/backlinks?project_key=${encodeURIComponent(project_key)}&doc=${encodeURIComponent(doc)}&limit=${limit}`,
  );
export const latticeQuery = (
  project_key: string,
  q: string,
  limit = 50,
  kinds?: string[],
  include_backlinks = false,
) =>
  request<any>("/api/lattice/query", {
    method: "POST",
    body: JSON.stringify({ project_key, q, limit, kinds, include_backlinks }),
  });
export const latticeRagSearch = (query: string, project_key?: string, top_k = 8) =>
  request<any>("/api/lattice/rag/search", {
    method: "POST",
    body: JSON.stringify({ q: query, project_key: project_key || "", limit: top_k }),
  });
export const latticePath = (project_key: string, source: string, target: string, max_depth = 8) =>
  request<any>("/api/lattice/path", {
    method: "POST",
    body: JSON.stringify({ project_key, source, target, max_depth }),
  });
export const latticeNeighbors = (project_key: string, node: string, depth = 1, limit = 50) =>
  request<any>("/api/lattice/neighbors", {
    method: "POST",
    body: JSON.stringify({ project_key, node, depth, limit }),
  });
export const latticeExplain = (
  project_key: string,
  opts: { source?: string; target?: string; node?: string } = {},
) =>
  request<any>("/api/lattice/explain", {
    method: "POST",
    body: JSON.stringify({
      project_key,
      source: opts.source || "",
      target: opts.target || "",
      node: opts.node || "",
    }),
  });
export const latticeBlueprint = (project_key: string) =>
  request<any>(`/api/lattice/blueprint?project_key=${encodeURIComponent(project_key)}`);

export type LatticeStatusResponse = {
  indexed: boolean;
  state?: string;
  reason?: string;
  action?: string | null;
  action_label?: string;
  project_key: string;
  has_blueprint: boolean;
  graph_stats?: Record<string, unknown>;
  blueprint_updated_at?: string | null;
  errors?: string[];
  indexed_at?: string | null;
  repository_id?: number | null;
  indexed_commit_sha?: string;
  live_commit_sha?: string;
};

export const latticeStatus = (project_key: string, repositoryId?: number | null) => {
  const qs = new URLSearchParams({ project_key });
  if (repositoryId != null) qs.set("repository_id", String(repositoryId));
  return request<LatticeStatusResponse>(`/api/lattice/status?${qs}`);
};

export const latticeBlueprintPrompt = (
  project_key: string,
  path = "",
  rebuild = false,
) =>
  request<any>("/api/lattice/blueprint/prompt", {
    method: "POST",
    body: JSON.stringify({ project_key, path, rebuild }),
  });
export const latticeGodNodes = (project_key: string, limit = 20) =>
  request<any>(`/api/lattice/god-nodes?project_key=${encodeURIComponent(project_key)}&limit=${limit}`);

// Mentrix
export const mentrixAgents = () => request<any>("/api/mentrix/agents");
export type CompanionProvenanceRow = {
  id: string;
  label: string;
  status: string;
  detail: string;
};

export type CompanionScopeEnvelope = {
  project_id: number | null;
  project_name: string;
  workspace_id: string;
  work_item_id: number | null;
  work_item_title: string;
  repo_ids: number[];
  active_root_id: number | null;
  roots: Array<{
    id: number;
    label: string;
    path: string;
    commit_sha: string;
    lattice_state: string;
    authorized: boolean;
  }>;
  semantic_cross_repo_references: boolean;
  skipped_unauthorized_repo_ids: number[];
  handoffs: Record<string, string>;
};

export const mentrixCompanionScope = (opts?: {
  projectId?: number | null;
  workItemId?: number | null;
  repositoryId?: number | null;
  workspaceId?: string;
}) => {
  const params = new URLSearchParams();
  if (opts?.projectId) params.set("project_id", String(opts.projectId));
  if (opts?.workItemId) params.set("work_item_id", String(opts.workItemId));
  if (opts?.workspaceId) params.set("workspace_id", opts.workspaceId);
  if (opts?.repositoryId) params.set("repository_ids", String(opts.repositoryId));
  const qs = params.toString();
  return request<CompanionScopeEnvelope>(`/api/mentrix/companion/scope${qs ? `?${qs}` : ""}`);
};

export const mentrixCompanionTurn = (
  message: string,
  opts?: {
    project_key?: string;
    project_id?: number;
    confirmed_tools?: string[];
    history?: { role: string; content: string }[];
    agent_context?: string;
    skill_id?: number | string;
    model?: string;
    signal?: AbortSignal;
    repository_ids?: number[];
    work_item_id?: number;
    workspace_id?: string;
  },
) =>
  request<any>("/api/mentrix/companion/turn", {
    method: "POST",
    signal: opts?.signal,
    body: JSON.stringify({
      message,
      project_key: opts?.project_key || "",
      project_id: opts?.project_id ?? null,
      confirmed_tools: opts?.confirmed_tools || [],
      history: opts?.history || [],
      agent_context: opts?.agent_context || "",
      repository_ids: opts?.repository_ids || [],
      work_item_id: opts?.work_item_id ?? null,
      workspace_id: opts?.workspace_id || "",
      ...(opts?.skill_id != null && opts.skill_id !== ""
        ? { skill_id: Number(opts.skill_id) }
        : {}),
      ...(opts?.model ? { model: opts.model } : {}),
    }),
  });

export type MentrixStreamEvent = {
  event: string;
  turn_id?: string;
  data?: Record<string, any>;
};

/** SSE companion stream via fetch (supports Bearer). */
export async function mentrixCompanionStream(
  message: string,
  opts: {
    project_key?: string;
    project_id?: number;
    confirmed_tools?: string[];
    agent_context?: string;
    skill_id?: number | string;
    model?: string;
    signal?: AbortSignal;
    onEvent: (ev: MentrixStreamEvent) => void;
    repository_ids?: number[];
    work_item_id?: number;
    workspace_id?: string;
  },
): Promise<void> {
  const params = new URLSearchParams({
    message,
    project_key: opts.project_key || "",
  });
  if (opts.project_id) params.set("project_id", String(opts.project_id));
  if (opts.repository_ids?.length) params.set("repository_ids", opts.repository_ids.join(","));
  if (opts.work_item_id) params.set("work_item_id", String(opts.work_item_id));
  if (opts.workspace_id) params.set("workspace_id", opts.workspace_id);
  if (opts.confirmed_tools?.length) {
    params.set("confirmed_tools", opts.confirmed_tools.join(","));
  }
  if (opts.agent_context?.trim()) {
    params.set("agent_context", opts.agent_context.trim().slice(0, 4000));
  }
  if (opts.skill_id != null && opts.skill_id !== "") {
    params.set("skill_id", String(opts.skill_id));
  }
  if (opts.model?.trim()) {
    params.set("model", opts.model.trim());
  }
  const res = await apiFetch(`/api/mentrix/companion/stream?${params.toString()}`, {
    method: "GET",
    signal: opts.signal,
  });
  if (!res.ok || !res.body) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : "Companion stream failed");
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() || "";
    for (const block of parts) {
      const lines = block.split("\n");
      let dataLine = "";
      for (const line of lines) {
        if (line.startsWith("data:")) dataLine += line.slice(5).trim();
      }
      if (!dataLine) continue;
      try {
        opts.onEvent(JSON.parse(dataLine) as MentrixStreamEvent);
      } catch {
        /* ignore partial */
      }
    }
  }
}

export async function mentrixCompanionStreamResume(
  turnId: string,
  confirmedTools: string[],
  opts: {
    signal?: AbortSignal;
    onEvent: (ev: MentrixStreamEvent) => void;
  },
): Promise<void> {
  const res = await apiFetch("/api/mentrix/companion/stream/resume", {
    method: "POST",
    signal: opts.signal,
    body: JSON.stringify({ turn_id: turnId, confirmed_tools: confirmedTools }),
  });
  if (!res.ok || !res.body) {
    throw new Error("Companion stream resume failed");
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() || "";
    for (const block of parts) {
      const lines = block.split("\n");
      let dataLine = "";
      for (const line of lines) {
        if (line.startsWith("data:")) dataLine += line.slice(5).trim();
      }
      if (!dataLine) continue;
      try {
        opts.onEvent(JSON.parse(dataLine) as MentrixStreamEvent);
      } catch {
        /* ignore */
      }
    }
  }
}

export const mentrixCompanionPolicy = () => request<any>("/api/mentrix/companion/policy");
export const mentrixCompanionPolicyImport = (pack: Record<string, unknown>, replace = false) =>
  request<any>("/api/mentrix/companion/policy/import", {
    method: "POST",
    body: JSON.stringify({ pack, replace }),
  });
export const mentrixCompanionTools = () => request<any>("/api/mentrix/companion/tools");
export const mentrixPreferredName = () =>
  request<{ preferred_name: string; email?: string }>("/api/mentrix/companion/preferred-name");
export const mentrixSetPreferredName = (preferred_name: string) =>
  request<{ preferred_name: string; user_id: number }>("/api/mentrix/companion/preferred-name", {
    method: "PUT",
    body: JSON.stringify({ preferred_name }),
  });
export const mentrixDesktopBridgeHeartbeat = () =>
  request<{ ok?: boolean }>("/api/mentrix/companion/desktop-bridge/heartbeat", { method: "POST" });
export const mentrixDesktopBridgePoll = () =>
  request<{ items: { id: string; command: Record<string, unknown> }[] }>(
    "/api/mentrix/companion/desktop-bridge/poll",
  );
export const mentrixDesktopBridgeAck = (id: string, result: Record<string, unknown> = {}) =>
  request("/api/mentrix/companion/desktop-bridge/ack", {
    method: "POST",
    body: JSON.stringify({ id, result }),
  });
export const mentrixDesktopBridgeEnqueue = (command: Record<string, unknown>) =>
  request("/api/mentrix/companion/desktop-bridge/enqueue", {
    method: "POST",
    body: JSON.stringify({ command }),
  });
export const mentrixDesktopBridgeStatus = () =>
  request<{ online?: boolean; error?: string; hint?: string }>(
    "/api/mentrix/companion/desktop-bridge/status",
  );
export const mentrixCompanionIntegrations = () =>
  request<{
    slack: boolean;
    jira: boolean;
    openai: boolean;
    datadog?: boolean;
    github?: boolean;
    browser?: boolean;
    browser_label?: string;
    browser_hint?: string;
    browser_provider?: string;
    presenton?: boolean;
    presenton_configured?: boolean;
    presenton_reachable?: boolean;
    presenton_base_url?: string;
    zinnia_presenton_template_id?: string;
    zoom_join_url_configured?: boolean;
    zoom_desktop_path_configured?: boolean;
    slack_channel?: string;
  }>("/api/mentrix/companion/integrations");
export const mentrixPresentonStatus = () =>
  request<{
    configured: boolean;
    reachable?: boolean;
    base_url: string;
    hint?: string;
    lifecycle?: string;
    zinnia_ready?: boolean;
    canonical_template_id?: string;
    blocked_external?: boolean;
    block_code?: string;
    provider?: string;
  }>("/api/mentrix/presenton/status");
export type PresentonTemplate = { id: string; name: string; native_ready?: boolean; visual?: { ready?: boolean } };
export const mentrixPresentonTemplates = () =>
  request<{
    ok: boolean;
    source: "presenton" | "builtin";
    templates: PresentonTemplate[];
    reachable?: boolean;
    configured?: boolean;
    hint?: string;
  }>("/api/mentrix/presenton/templates");
export const mentrixPresentonGenerate = (data: {
  content: string;
  n_slides?: number;
  template?: string;
  ui_template_choice?: string;
  custom_id?: string;
  instructions?: string;
  filename?: string;
  asset_ids?: string[];
  language?: string;
  documents?: string[];
  fast_basic?: boolean;
  require_llm?: boolean;
}) => {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 600_000);
  return request<{
    ok: boolean;
    path: string;
    bytes?: number;
    presentation_id?: string;
    template_sent?: string;
    ui_template_choice?: string;
    zinnia_verified?: boolean;
    zinnia_note?: string;
    resolve_note?: string;
    lifecycle?: string;
    canonical_id?: string;
    mapping_source?: string;
    blocked_external?: boolean;
    planner_mode?: string;
    fallback?: boolean;
    fallback_reason?: string;
    degraded?: boolean;
    presenton_request?: { template?: string; n_slides?: number };
    provider?: string;
    final_quality_status?: string;
    repair_attempts?: number;
    overlap_count?: number;
    ungrounded_fact_count?: number;
    quality?: Record<string, unknown>;
  }>(
    "/api/mentrix/presenton/generate",
    { method: "POST", body: JSON.stringify(data), signal: controller.signal },
  ).finally(() => clearTimeout(timer));
};

export type PresentBlock = {
  id?: string;
  kind: string;
  slide_index?: number;
  layout_intent?: string;
  geometry?: { x?: number; y?: number; cx?: number; cy?: number } | null;
  content?: Record<string, unknown>;
  provenance?: { source?: string; generated?: boolean; note?: string };
  validation?: { ok?: boolean; errors?: string[] };
};

export type PresentSlide = {
  index: number;
  notes?: string;
  text?: string;
  blocks?: PresentBlock[];
};

export const mentrixParsePptxFromPath = (path: string) =>
  request<{
    ok: boolean;
    count: number;
    slides: PresentSlide[];
    filename: string;
    path?: string;
    visuals?: { has_image?: boolean; has_chart?: boolean; has_table?: boolean };
  }>("/api/mentrix/present/parse-pptx-path", {
    method: "POST",
    body: JSON.stringify({ path }),
  });

export const mentrixPresentSaveNotes = (path: string, slides: PresentSlide[]) =>
  request<{ ok: boolean; notes_path?: string; count?: number; ooxml_roundtrip?: boolean; ooxml_error?: string }>(
    "/api/mentrix/present/save-notes",
    {
      method: "POST",
      body: JSON.stringify({ path, slides }),
    },
  );

export async function mentrixPresentPptxDownload(path: string): Promise<{ blob: Blob; filename: string }> {
  const token = typeof localStorage !== "undefined" ? localStorage.getItem("zect_token") : null;
  const url = `${getApiBase()}/api/mentrix/present/pptx?path=${encodeURIComponent(path)}`;
  const res = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      const detail = err.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : detail?.hint || detail?.error || err.detail || "Export failed";
      throw new Error(String(msg));
    }
  const blob = await res.blob();
  const disp = res.headers.get("content-disposition") || "";
  const match = disp.match(/filename="?([^"]+)"?/i);
  return { blob, filename: match?.[1] || "zect-deck.pptx" };
}

export const mentrixPresentDecks = () =>
  request<{ ok: boolean; items: Array<{ id: string; name: string; path: string; slide_count: number; modified: number; bytes: number }> }>(
    "/api/mentrix/present/decks",
  );

export const mentrixPresentDeckDelete = (path: string) =>
  request<{ ok: boolean; path: string }>("/api/mentrix/present/decks/delete", {
    method: "POST",
    body: JSON.stringify({ path }),
  });

export const mentrixPresentDeckDuplicate = (path: string) =>
  request<{ ok: boolean; path: string; filename: string }>("/api/mentrix/present/decks/duplicate", {
    method: "POST",
    body: JSON.stringify({ path }),
  });

export const mentrixPresentBlank = () =>
  request<{ ok: boolean; path: string; filename: string }>("/api/mentrix/present/blank", { method: "POST" });

export async function mentrixPresentImport(file: File) {
  const token = typeof localStorage !== "undefined" ? localStorage.getItem("zect_token") : null;
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${getApiBase()}/api/mentrix/present/import`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: fd,
  });
  if (!res.ok) throw new Error("Import failed");
  return (await res.json()) as { ok: boolean; path: string; filename: string };
}

export async function mentrixPresentSlidePreview(path: string, index: number): Promise<string> {
  const token = typeof localStorage !== "undefined" ? localStorage.getItem("zect_token") : null;
  const url = `${getApiBase()}/api/mentrix/present/slide-preview?path=${encodeURIComponent(path)}&index=${index}`;
  const res = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!res.ok) throw new Error("preview_failed");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export const mentrixPresentQualityGate = (path: string) =>
  request<{
    ok: boolean;
    path: string;
    export_blocked: boolean;
    hard_blocked?: boolean;
    accept_warnings_allowed?: boolean;
    quality_passed: boolean;
    slide_count: number;
    overlap_count: number;
    clipped_text_count: number;
    covering_dump_count: number;
    broken_rel_count?: number;
    hard_findings?: string[];
    warnings?: string[];
    final_quality_status?: string;
  }>(`/api/mentrix/present/quality-gate?path=${encodeURIComponent(path)}`);

export function encodeDeckId(path: string): string {
  const b64 = btoa(unescape(encodeURIComponent(path)));
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function decodeDeckId(id: string): string {
  const pad = id.replace(/-/g, "+").replace(/_/g, "/");
  const padded = pad + "=".repeat((4 - (pad.length % 4)) % 4);
  return decodeURIComponent(escape(atob(padded)));
}

export const mentrixPresentationAudiences = () =>
  request<{ audiences: Array<{ id: string; label: string; slide_count_hint?: number }> }>(
    "/api/mentrix/presentation/audiences",
  );

export const mentrixAnalyzeDeck = (data: {
  slides?: Array<{ index?: number; notes?: string; text?: string }>;
  notes_blob?: string;
  audience_id?: string;
  sensitivity_hint?: string;
}) =>
  request<{
    ok: boolean;
    reason?: string;
    flow: string;
    sensitivity: { sensitivity: string; model_route?: Record<string, unknown> };
    audience: { id: string; label: string };
    claims: Array<{
      id: string;
      claim: string;
      verification_status: string;
      present_as_fact?: boolean;
      source?: string;
    }>;
    claims_markdown?: string;
    improved_notes?: Array<{ index: number; notes: string }>;
    rehearse_ready?: boolean;
  }>("/api/mentrix/presentation/analyze-deck", { method: "POST", body: JSON.stringify(data) });

export const mentrixPreparePromptDeck = (data: {
  prompt: string;
  audience_id?: string;
  sensitivity_hint?: string;
  documents?: string[];
}) =>
  request<{
    ok: boolean;
    reason?: string;
    adapted_prompt: string;
    outline: string[];
    n_slides_hint?: number;
    sensitivity: { sensitivity: string };
    claims: Array<{ id: string; claim: string; verification_status: string; present_as_fact?: boolean }>;
    claims_markdown?: string;
    requires_user_approval?: boolean;
    presenton_ready?: boolean;
  }>("/api/mentrix/presentation/prepare-prompt", { method: "POST", body: JSON.stringify(data) });

export type PresentTemplateVisual = {
  colors?: string[];
  fonts?: { major?: string; minor?: string };
  layout_names?: string[];
  layout_count?: number;
  ready?: boolean;
  readiness?: string;
  thumbnail_kind?: string;
  cover_url?: string;
  cover_data_url?: string;
  error?: string | null;
};

export type PresentTemplateCard = {
  id: string;
  name: string;
  scope?: string;
  kind?: string;
  preview?: string;
  visual?: PresentTemplateVisual;
  readiness?: string;
  native_ready?: boolean;
};

export const mentrixPresentationTemplates = () =>
  request<{
    ok: boolean;
    zinnia: Array<PresentTemplateCard>;
    organization: Array<PresentTemplateCard>;
    my_templates: Array<PresentTemplateCard>;
    lifecycle?: string;
    mappings_ready?: Record<string, boolean>;
    canonical_ids?: string[];
  }>("/api/mentrix/presentation/templates");

export const mentrixPresentationTemplateSlides = (templateId: string) =>
  request<{ ok: boolean; template_id?: string; slides?: string[]; count?: number }>(
    `/api/mentrix/presentation/templates/${encodeURIComponent(templateId)}/slides`,
  );

export const mentrixPresentationTemplatePreview = (template_id: string) =>
  request<{
    ok: boolean;
    template_id?: string;
    name?: string;
    preview?: string;
    error?: string;
    visual?: PresentTemplateVisual;
    readiness?: string;
    provider_uuid_hidden?: boolean;
    mapped?: boolean;
    lifecycle?: string;
    canonical_id?: string;
  }>("/api/mentrix/presentation/templates/preview", {
    method: "POST",
    body: JSON.stringify({ template_id }),
  });

export async function mentrixPresentationTemplateUpload(
  file: File,
  name?: string,
  scope: "USER" | "ORG" = "USER",
) {
  const form = new FormData();
  form.append("file", file);
  if (name) form.append("name", name);
  form.append("scope", scope);
  const token =
    typeof localStorage !== "undefined" ? localStorage.getItem("zect_token") : null;
  const res = await fetch(`${API}/api/mentrix/presentation/templates/upload`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  return (await res.json()) as {
    ok: boolean;
    template?: { id: string; name: string; preview?: string; scope?: string };
    error?: string;
  };
}

export const mentrixPresentationTemplateDelete = (template_id: string) =>
  request<{ ok: boolean; id?: string; error?: string; message?: string }>(
    "/api/mentrix/presentation/templates/delete",
    {
      method: "POST",
      body: JSON.stringify({ template_id }),
    },
  );

export const mentrixPresentationDeleteUnmapped = () =>
  request<{ ok: boolean; deleted?: string[]; count?: number; error?: string; message?: string }>(
    "/api/mentrix/presentation/templates/delete-unmapped",
    { method: "POST" },
  );

export const mentrixPresentationNarrateSlides = (slides: Array<Record<string, unknown>>, deck_context = "") =>
  request<{
    ok: boolean;
    count?: number;
    max_words?: number;
    slides?: Array<{ index: number; script: string; word_count?: number; visuals?: string[] }>;
    error?: string;
  }>("/api/mentrix/presentation/narrate-slides", {
    method: "POST",
    body: JSON.stringify({ slides, deck_context }),
  });

export type MentrixWorkbook = {
  sheets: Array<{ name: string; cells: Record<string, { v?: string; f?: string }> }>;
};

export const mentrixSheetsGenerate = (prompt: string, project_id?: number) =>
  request<{ ok: boolean; workbook: MentrixWorkbook }>("/api/mentrix/sheets/generate", {
    method: "POST",
    body: JSON.stringify({ prompt, ...(project_id != null ? { project_id } : {}) }),
  });

export async function mentrixSheetsImport(file: File) {
  const form = new FormData();
  form.append("file", file);
  const token = typeof localStorage !== "undefined" ? localStorage.getItem("zect_token") : null;
  const res = await fetch(`${API}/api/mentrix/sheets/import`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  const body = (await res.json()) as { ok?: boolean; workbook?: MentrixWorkbook; detail?: string };
  if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Import failed");
  return body;
}

export async function mentrixSheetsExport(workbook: MentrixWorkbook) {
  const token = typeof localStorage !== "undefined" ? localStorage.getItem("zect_token") : null;
  const res = await fetch(`${API}/api/mentrix/sheets/export`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ workbook }),
  });
  if (!res.ok) throw new Error("Export failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "mentrix-sheet.xlsx";
  a.click();
  URL.revokeObjectURL(url);
}

export async function mentrixPresentationAssetUpload(file: File) {
  const form = new FormData();
  form.append("file", file);
  const token = typeof localStorage !== "undefined" ? localStorage.getItem("zect_token") : null;
  const res = await fetch(`${API}/api/mentrix/presentation/assets`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  return (await res.json()) as {
    ok?: boolean;
    asset_id?: string;
    error?: string;
    mime?: string;
    width?: number;
    height?: number;
  };
}

export async function mentrixPresentationAssetBlob(assetId: string): Promise<string> {
  const token = typeof localStorage !== "undefined" ? localStorage.getItem("zect_token") : null;
  const res = await fetch(`${API}/api/mentrix/presentation/assets/${encodeURIComponent(assetId)}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("asset_not_found");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export const mentrixPresentationTemplateMapping = (zect_id: string, provider_template_id: string) =>
  request<{ ok: boolean; zect_id?: string; mapping?: Record<string, unknown>; error?: string }>(
    "/api/mentrix/presentation/templates/mapping",
    { method: "POST", body: JSON.stringify({ zect_id, provider_template_id }) },
  );

/** Upload .pptx → slide text + speaker notes (browser Present narration). */
export const mentrixParsePptx = async (
  file: File,
): Promise<{ ok: boolean; count: number; slides: { index: number; notes?: string; text?: string }[]; filename: string }> => {
  const form = new FormData();
  form.append("file", file);
  const token = typeof localStorage !== "undefined" ? localStorage.getItem("zect_token") : null;
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  const url = `${API}/api/mentrix/present/parse-pptx`;
  let res: Response;
  try {
    res = await fetch(url, { method: "POST", body: form, headers });
  } catch {
    throw new Error(`Cannot reach ZECT API at ${API}`);
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = err.detail;
    throw new Error(typeof detail === "string" ? detail : detail?.message || `Parse failed (${res.status})`);
  }
  return res.json();
};
export const mentrixRealtimeSession = () =>
  request<{
    ok: boolean;
    realtime_enabled?: boolean;
    client_secret?: string;
    model?: string;
    openai_ws_url?: string;
    fallback?: string;
    reason?: string;
  }>("/api/mentrix/companion/realtime/session", { method: "POST" });
export const mentrixRealtimeTool = (tool: string, args: Record<string, unknown>, confirmed = false) =>
  request<any>("/api/mentrix/companion/realtime/tool", {
    method: "POST",
    body: JSON.stringify({
      tool,
      args,
      confirmed,
      project_key: typeof localStorage !== "undefined" ? localStorage.getItem("zect_lattice_key") || "" : "",
    }),
  });
// Mentrix voice cloning — Realtime handles speech understanding unchanged;
// this is the hosted-TTS output swap once a voice is cloned.
export type ClonedVoiceInfo = {
  id?: number | null;
  voice_id: string;
  name: string;
  provider: string;
  is_default?: boolean;
  has_sample?: boolean;
  engine_ready?: boolean;
  sample_missing?: boolean;
};

export const cloneMyVoice = async (
  name: string,
  referenceText: string,
  file: File,
): Promise<ClonedVoiceInfo> => {
  const form = new FormData();
  form.append("name", name);
  form.append("reference_text", referenceText);
  form.append("sample", file);
  const token = typeof localStorage !== "undefined" ? localStorage.getItem("zect_token") : null;
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  // Deliberately not using apiFetch here — it hardcodes Content-Type: application/json,
  // which breaks multipart form uploads (the browser must set its own boundary).
  const url = `${API}/api/mentrix/voice/clone`;
  let res: Response;
  try {
    res = await fetch(url, { method: "POST", body: form, headers });
  } catch {
    throw new Error(`Cannot reach ZECT API at ${API} — is the backend running on :8000?`);
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = err.detail;
    throw new Error(
      typeof detail === "string" ? detail : detail?.message || res.statusText || `Clone failed (${res.status})`,
    );
  }
  return res.json();
};
export const getMyClonedVoice = () =>
  request<ClonedVoiceInfo | null>("/api/mentrix/voice/my-voice");
export const listMyClonedVoices = () =>
  request<ClonedVoiceInfo[]>("/api/mentrix/voice/voices");
export const setDefaultClonedVoice = (voiceId: string) =>
  request<ClonedVoiceInfo>(`/api/mentrix/voice/voices/${encodeURIComponent(voiceId)}/default`, {
    method: "POST",
  });
export const deleteClonedVoice = (voiceId: string) =>
  request<{ deleted: boolean }>(`/api/mentrix/voice/voices/${encodeURIComponent(voiceId)}`, {
    method: "DELETE",
  });
export const resetMyClonedVoice = () =>
  request<{ cleared: boolean }>("/api/mentrix/voice/my-voice", { method: "DELETE" });

export type MentrixNote = { id: string; text: string; tags: string[]; createdAt: string };

/** Browse notes — manual (note_add) and auto-logged Companion exchanges alike. */
export const listMentrixNotes = (limit = 200) =>
  request<{ notes: MentrixNote[] }>(`/api/mentrix/notes?limit=${limit}`);

export const createMentrixNote = (text: string, tags?: string[]) =>
  request<MentrixNote>("/api/mentrix/notes", {
    method: "POST",
    body: JSON.stringify({ text, tags }),
  });

export const deleteMentrixNote = (id: string) =>
  request<{ deleted: boolean; id: string }>(`/api/mentrix/notes/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });

/**
 * Auto-log a completed cloned-voice exchange to Mentrix Notes — personal-
 * assistant behavior, not gated behind a trigger phrase. Fire-and-forget:
 * callers should not await/block on this or let it interrupt the
 * conversation if logging fails.
 */
export function logMentrixExchange(userMessage: string, assistantReply: string): Promise<void> {
  return apiFetch("/api/mentrix/companion/log-exchange", {
    method: "POST",
    body: JSON.stringify({ user_message: userMessage, assistant_reply: assistantReply }),
  })
    .then(() => undefined)
    .catch(() => undefined);
}

/** Speak text via Mentrix TTS (Chatterbox clone or OpenAI fallback). Returns audio blob URL. */
export async function mentrixSpeakCloned(text: string, voiceOpts?: SpeakVoiceOptions): Promise<string> {
  const { url } = await mentrixSpeakClonedDetailed(text, voiceOpts);
  return url;
}

/**
 * Same call as mentrixSpeakCloned, but also surfaces which engine actually
 * produced the audio via X-Mentrix-TTS-Engine. Clone path defaults to
 * require_clone (no silent OpenAI fallback); stock_voice bypasses Chatterbox.
 */
export type SpeakVoiceOptions = {
  /** A specific saved cloned voice id — omit to use your default clone. */
  voiceId?: string;
  /** An OpenAI stock voice ("alloy"|"echo"|"fable"|"onyx"|"nova"|"shimmer") —
   * when set, bypasses Chatterbox/your clone entirely. */
  stockVoice?: string;
  /**
   * When true (default if no stockVoice), backend must use Chatterbox clone —
   * no OpenAI stock fallback. Present / Test speak should leave this on.
   */
  requireClone?: boolean;
};

export type VoiceEngineStatus = {
  online: boolean;
  base_url: string;
  default_voice: {
    voice_id: string;
    name: string;
    has_sample?: boolean;
    engine_ready?: boolean;
    sample_missing?: boolean;
    is_default?: boolean;
  } | null;
  hint: string;
};

/** Chatterbox local engine health (non-secret) for Present / Voice UI. */
export const mentrixVoiceEngineStatus = (opts?: { forceRefresh?: boolean }) =>
  request<VoiceEngineStatus>(
    `/api/mentrix/voice/engine-status${opts?.forceRefresh ? "?force_refresh=true" : ""}`,
  );

export async function mentrixSpeakClonedDetailed(
  text: string,
  voiceOpts?: SpeakVoiceOptions,
): Promise<{ url: string; engine: string }> {
  const token = typeof localStorage !== "undefined" ? localStorage.getItem("zect_token") : null;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const url = `${API}/api/mentrix/voice/speak`;
  const requireClone =
    voiceOpts?.stockVoice != null && voiceOpts.stockVoice !== ""
      ? false
      : voiceOpts?.requireClone !== false;
  const speakTimeoutMs = Number(import.meta.env.VITE_MENTRIX_SPEAK_TIMEOUT_MS || 180000);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), speakTimeoutMs);
  let res: Response;
  try {
    res = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify({
        text: text.slice(0, 4000),
        voice_id: voiceOpts?.voiceId,
        stock_voice: voiceOpts?.stockVoice,
        require_clone: requireClone,
      }),
      signal: controller.signal,
    });
  } catch (e: any) {
    if (e?.name === "AbortError") {
      throw new Error(`Speak timed out after ${speakTimeoutMs}ms — is ZECT Voicebox models_ready?`);
    }
    throw new Error(`Cannot reach ZECT API at ${API} — is the backend running?`);
  } finally {
    clearTimeout(timer);
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = err.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : detail?.message || res.statusText || `Speak failed (${res.status})`,
    );
  }
  const engine = res.headers.get("X-Mentrix-TTS-Engine") || "unknown";
  const declared =
    res.headers.get("X-Mentrix-TTS-Content-Type") ||
    res.headers.get("Content-Type") ||
    (engine.includes("voicebox") || engine === "zect_voicebox" || engine === "chatterbox"
      ? "audio/wav"
      : "audio/mpeg");
  const buf = await res.arrayBuffer();
  if (!buf.byteLength) throw new Error("Speak returned empty audio");
  const blob = new Blob([buf], { type: declared.split(";")[0].trim() || "audio/mpeg" });
  return { url: URL.createObjectURL(blob), engine };
}

/** Mint a short-lived CapabilityGrant after Mentrix Allow (session desktop/connector writes). */
export const createCapabilityGrant = (body: {
  capability: string;
  duration_minutes?: number;
  reason?: string;
}) =>
  request<{
    id: number;
    capability: string;
    expires_at?: string;
  }>("/api/permissions/grants/session", {
    method: "POST",
    body: JSON.stringify({
      capability: body.capability,
      duration_minutes: body.duration_minutes ?? 30,
      reason: body.reason || "Mentrix Companion Allow session",
    }),
  });


export const mcpExecute = (server_id: string, tool_name: string, arguments_: Record<string, unknown> = {}) =>
  request<{
    server_id: string;
    tool_name: string;
    status: string;
    result: any;
    execution_time_ms?: number;
  }>("/api/mcp/execute", {
    method: "POST",
    body: JSON.stringify({ server_id, tool_name, arguments: arguments_ }),
  });

export const mentrixMediaList = () => request<{ items: any[] }>("/api/mentrix/companion/media");
export const mentrixMediaUrl = (number: number) => {
  const token = typeof localStorage !== "undefined" ? localStorage.getItem("zect_token") : "";
  return `${getApiBase()}/api/mentrix/companion/media/${number}${token ? `?token=${encodeURIComponent(token)}` : ""}`;
};
export const mentrixStartRun = (
  goal: string,
  mode = "upgrade",
  project_key = "",
  workspace = "",
  opts?: {
    source_lang?: string;
    target_lang?: string;
    repo_id?: number;
    work_item_id?: number | null;
    coding_mission_id?: string;
  }
) =>
  request<any>("/api/mentrix/runs", {
    method: "POST",
    body: JSON.stringify({
      goal,
      mode,
      project_key,
      workspace,
      source_lang: opts?.source_lang || "",
      target_lang: opts?.target_lang || "",
      repo_id: opts?.repo_id ?? null,
      work_item_id: opts?.work_item_id ?? null,
      coding_mission_id: opts?.coding_mission_id || "",
    }),
  });
export const mentrixGetRun = (runId: number) => request<any>(`/api/mentrix/runs/${runId}`);
export const mentrixListRuns = (limit = 20) =>
  request<any[]>(`/api/mentrix/runs?limit=${limit}`);
export const mentrixCancelRun = (runId: number) =>
  request<any>(`/api/mentrix/runs/${runId}`, { method: "DELETE" });
export const mentrixRetryRun = (runId: number) =>
  request<any>(`/api/mentrix/runs/${runId}/retry`, { method: "POST" });
export const mentrixApproveRun = (runId: number, acknowledge_issues = false) =>
  request<any>(`/api/mentrix/runs/${runId}/approve`, {
    method: "POST",
    body: JSON.stringify({ acknowledge_issues }),
  });
export const mentrixGetRunPlan = (runId: number) =>
  request<any>(`/api/mentrix/runs/${runId}/plan`);
export const mentrixPatchRunPlan = (
  runId: number,
  data: { summary?: string; steps?: any[]; phases?: any[] },
) =>
  request<any>(`/api/mentrix/runs/${runId}/plan`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
export const mentrixConfirmPlan = (
  runId: number,
  data?: { summary?: string; steps?: any[]; phases?: any[]; files_expected?: string[] },
) =>
  request<any>(`/api/mentrix/runs/${runId}/confirm-plan`, {
    method: "POST",
    body: JSON.stringify(data || {}),
  });
export const mentrixConfirmBatch = (runId: number) =>
  request<any>(`/api/mentrix/runs/${runId}/confirm-batch`, {
    method: "POST",
    body: JSON.stringify({}),
  });
export const mentrixCreatePr = (
  runId: number,
  data?: {
    title?: string;
    body?: string;
    dry_run?: boolean;
    repo_path?: string;
    owner?: string;
    repo_name?: string;
    head_branch?: string;
    base_branch?: string;
  },
) =>
  request<any>(`/api/mentrix/runs/${runId}/create-pr`, {
    method: "POST",
    body: JSON.stringify({ dry_run: true, ...data }),
  });
export const mentrixSastStatus = (owner: string, repo: string, ref: string) =>
  request<any>(
    `/api/code-review/sast-status?owner=${encodeURIComponent(owner)}&repo=${encodeURIComponent(repo)}&ref=${encodeURIComponent(ref)}`,
  );
export const mentrixRefreshSast = (
  runId: number,
  params?: { owner?: string; repo?: string; ref?: string },
) => {
  const q = new URLSearchParams();
  if (params?.owner) q.set("owner", params.owner);
  if (params?.repo) q.set("repo", params.repo);
  if (params?.ref) q.set("ref", params.ref);
  const qs = q.toString();
  return request<any>(`/api/mentrix/runs/${runId}/refresh-sast${qs ? `?${qs}` : ""}`, {
    method: "POST",
  });
};
export const mentrixFineTuneExport = () =>
  request<any>("/api/mentrix/fine-tune/export");

// Legacy Agent Mode (/api/agent) — power-user path; prefer Mentrix Delivery
export interface AgentModeStep {
  id: number;
  stage: string;
  step_index: number;
  output: string;
  tokens_used: number;
  duration_ms: number;
  status: string;
  model: string;
  created_at: string | null;
}

export interface AgentModeRun {
  id: number;
  run_id: string;
  task: string;
  stages: string[];
  model: string;
  status: string;
  current_stage_index?: number;
  auto_advance?: boolean;
  total_tokens?: number;
  steps: AgentModeStep[];
  created_at?: string | null;
  completed_at?: string | null;
  mode?: string;
  engine?: string;
  warning?: string;
  workspace?: string;
  files_written?: string[];
  result?: Record<string, unknown>;
}

export const agentListRuns = () => request<AgentModeRun[]>("/api/agent/runs");

export const agentGetRun = (runId: string) =>
  request<AgentModeRun>(`/api/agent/run/${encodeURIComponent(runId)}`);

export const agentStartRun = (data: {
  task: string;
  stages: string[];
  model: string;
  repo_context?: string;
  auto_advance?: boolean;
  workspace?: string;
  project_key?: string;
  repo_id?: number;
}) =>
  request<AgentModeRun>("/api/agent/run", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const agentResumeRun = (runId: string, model?: string) =>
  request<AgentModeRun>(`/api/agent/run/${encodeURIComponent(runId)}/resume`, {
    method: "POST",
    body: JSON.stringify({ model }),
  });

export const agentCancelRun = (runId: string) =>
  request<void>(`/api/agent/run/${encodeURIComponent(runId)}`, { method: "DELETE" });

// Sandbox PR readiness
export const sandboxPrReadiness = (data: {
  code?: string;
  language?: string;
  quality_score?: number;
  critical_findings?: number;
  acknowledge_issues?: boolean;
}) =>
  request<any>("/api/sandbox/pr-readiness", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const getAuthConfig = () =>
  request<{ auth_mode: string; local_enabled: boolean; oidc_enabled: boolean; oidc_configured: boolean }>(
    "/api/auth/config"
  );

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
export const deployTriggerWorkflow = (
  owner: string,
  repo: string,
  workflow_file: string,
  ref?: string,
  environment?: string,
  inputs?: Record<string, string>,
  audit_id?: number,
) =>
  request<{ status: string; audit_id: number | null; message: string }>("/api/deploy/trigger-workflow", {
    method: "POST",
    body: JSON.stringify({
      owner,
      repo,
      workflow_file,
      ref: ref || "main",
      environment: environment || "production",
      inputs: inputs || {},
      ...(audit_id ? { audit_id } : {}),
    }),
  });
export const approvePermissionAudit = (auditId: number, approved: boolean, reason?: string) =>
  request<any>(`/api/permissions/audits/${auditId}/approve`, {
    method: "POST",
    body: JSON.stringify({ approved, reason: reason || "" }),
  });

// Skills
// Skill Library was merged into the Skills Engine — genuinely duplicate
// concepts (name/description/category/template/tags CRUD), and Skills
// Engine is the more complete system (versioning, trigger matching,
// execution logs). getSkills() is kept for the Mentrix "Active Skill"
// picker (MentrixSessionContext.tsx), now backed by the registry.
export const getSkills = (category?: string) => {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  const qs = params.toString();
  return request<any[]>(`/api/skills-engine/skills${qs ? `?${qs}` : ""}`);
};

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
export const runnerExecute = (command: string, cwd?: string, timeout?: number, boundRoot?: string) =>
  request<any>("/api/runner/execute", {
    method: "POST",
    body: JSON.stringify({
      command,
      ...(cwd ? { cwd } : {}),
      ...(boundRoot || cwd ? { bound_root: boundRoot || cwd } : {}),
      ...(timeout ? { timeout } : {}),
    }),
  });
export const runnerStart = (
  command: string,
  cwd?: string,
  label?: string,
  env_vars?: Record<string, string>,
  boundRoot?: string,
) =>
  request<any>("/api/runner/start", {
    method: "POST",
    body: JSON.stringify({
      command,
      ...(cwd ? { cwd } : {}),
      ...(boundRoot || cwd ? { bound_root: boundRoot || cwd } : {}),
      ...(label ? { label } : {}),
      ...(env_vars ? { env_vars } : {}),
    }),
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

// Mentrix Coding Agent (Cursor-class)
export type MentrixCodingAgentEvent = {
  sequence_id: number;
  event: string;
  message: string;
  phase?: string;
  data?: Record<string, any>;
};

export const codingAgentCreateSession = (body: {
  goal: string;
  workspace: string;
  model?: string;
  auto_approve_edits?: boolean;
  max_steps?: number;
  expected_files?: string[];
}) =>
  request<{ id: string; status: string; events?: MentrixCodingAgentEvent[] }>("/api/coding-agent/sessions", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const codingAgentGetSession = (sessionId: string) =>
  request<any>(`/api/coding-agent/sessions/${encodeURIComponent(sessionId)}`);

export const codingAgentCancel = (sessionId: string) =>
  request<any>(`/api/coding-agent/sessions/${encodeURIComponent(sessionId)}/cancel`, { method: "POST" });

export const codingAgentApprove = (sessionId: string, actionId: string, approve = true) =>
  request<any>(`/api/coding-agent/sessions/${encodeURIComponent(sessionId)}/approve`, {
    method: "POST",
    body: JSON.stringify({ action_id: actionId, approve }),
  });

export const codingAgentMessage = (sessionId: string, message: string) =>
  request<any>(`/api/coding-agent/sessions/${encodeURIComponent(sessionId)}/message`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });

/** SSE stream for Mentrix Coding Agent session events. */
export async function codingAgentStream(
  sessionId: string,
  opts: {
    after?: number;
    signal?: AbortSignal;
    onEvent: (ev: MentrixCodingAgentEvent) => void;
  },
): Promise<void> {
  const params = new URLSearchParams();
  if (opts.after != null) params.set("after", String(opts.after));
  const res = await apiFetch(
    `/api/coding-agent/sessions/${encodeURIComponent(sessionId)}/stream?${params.toString()}`,
    { method: "GET", signal: opts.signal },
  );
  if (!res.ok || !res.body) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : "Coding agent stream failed");
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() || "";
    for (const block of parts) {
      const lines = block.split("\n");
      let dataLine = "";
      for (const line of lines) {
        if (line.startsWith("data:")) dataLine += line.slice(5).trim();
      }
      if (!dataLine) continue;
      try {
        const parsed = JSON.parse(dataLine) as MentrixCodingAgentEvent;
        if (parsed.event === "ping" || (parsed as any).after != null && !parsed.sequence_id) continue;
        opts.onEvent(parsed);
      } catch {
        /* ignore */
      }
    }
  }
}

export type CodingAgentMissionRoot = {
  id: number;
  label: string;
  path: string;
};

export type CodingAgentMission = {
  id: string;
  goal: string;
  phase: string;
  status: string;
  plan: string;
  plan_approved: boolean;
  git_approved: boolean;
  repos: Array<{
    repository_id?: number;
    label?: string;
    worktree_path?: string;
    branch?: string;
    test_ok?: boolean;
    test_status?: string;
    files?: string[];
    commands?: string[];
    blocker?: string;
    committed_shas?: string[];
    diff?: string;
    push?: Record<string, unknown>;
    pr?: Record<string, unknown>;
  }>;
  files: string[];
  commands: string[];
  tests: Record<string, string | undefined>;
  blockers: string[];
  approvals: { plan: boolean; git: boolean };
  review: {
    passed?: boolean;
    summary?: string;
    critical_findings?: number;
    findings?: Array<{ severity?: string; message?: string }>;
  };
  pr: Record<string, unknown>;
  ci: Record<string, unknown>;
  sibling?: { blocked?: boolean; blocker?: string };
  ready_to_merge: boolean;
  no_auto_merge: boolean;
  events?: Array<{ event?: string; message?: string; at?: string }>;
  evidence?: Array<{ event?: string; message?: string; at?: string }>;
};

export const codingAgentCreateMission = (body: {
  goal: string;
  project_id?: number | null;
  work_item_id?: number | null;
  roots?: CodingAgentMissionRoot[];
  patches_by_repo?: Record<string, Array<Record<string, string>>>;
  plan?: string;
  workspace_parent?: string;
  propose_if_empty?: boolean;
}) =>
  request<CodingAgentMission>("/api/coding-agent/missions", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const codingAgentGetMission = (missionId: string) =>
  request<CodingAgentMission>(`/api/coding-agent/missions/${encodeURIComponent(missionId)}`);

export const codingAgentApprovePlan = (missionId: string) =>
  request<CodingAgentMission>(`/api/coding-agent/missions/${encodeURIComponent(missionId)}/approve-plan`, {
    method: "POST",
  });

export const codingAgentApproveGit = (missionId: string) =>
  request<CodingAgentMission>(`/api/coding-agent/missions/${encodeURIComponent(missionId)}/approve-git`, {
    method: "POST",
  });

export const codingAgentCancelMission = (missionId: string) =>
  request<CodingAgentMission>(`/api/coding-agent/missions/${encodeURIComponent(missionId)}/cancel`, {
    method: "POST",
  });

export const codingAgentResumeMission = (missionId: string) =>
  request<CodingAgentMission>(`/api/coding-agent/missions/${encodeURIComponent(missionId)}/resume`, {
    method: "POST",
  });

export const codingAgentRetryMission = (missionId: string) =>
  request<CodingAgentMission>(`/api/coding-agent/missions/${encodeURIComponent(missionId)}/retry`, {
    method: "POST",
  });

export const codingAgentListPlans = () =>
  request<{ ok: boolean; plans: Array<{ id: string; markdown?: string; title?: string; work_item_or_run?: string }> }>(
    "/api/coding-agent/plans",
  );

export const codingAgentSavePlan = (body: {
  work_item_or_run: string;
  title?: string;
  markdown: string;
  meta?: Record<string, unknown>;
}) =>
  request<{ ok: boolean; id: string; path?: string; markdown: string }>("/api/coding-agent/plans", {
    method: "POST",
    body: JSON.stringify(body),
  });

export type RuntimeRecipe = {
  id: string;
  kind: string;
  label?: string;
  command: string;
  cwdRel: string;
  port?: number;
  confirmRequired?: boolean;
  evidence?: string;
};

export const codingAgentRuntimeRecipes = (root: string) =>
  request<{ ok: boolean; default_id?: string; recipes: RuntimeRecipe[]; postgres_note?: string; error?: string }>(
    `/api/coding-agent/runtime-recipes?root=${encodeURIComponent(root)}`,
  );

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
export const gitRestore = (repoPath: string, files: string[]) =>
  request<any>("/api/git/restore", {
    method: "POST",
    body: JSON.stringify({ repo_path: repoPath, files }),
  });
export const gitWorktrees = (repoPath: string) =>
  request<any>(`/api/git/worktrees?repo_path=${encodeURIComponent(repoPath)}`);

/** Compare two strings via /api/diff/compare (unified + side_by_side + stats). */
export const diffCompare = (
  left: string,
  right: string,
  opts?: { left_label?: string; right_label?: string; context_lines?: number },
) =>
  request<any>("/api/diff/compare", {
    method: "POST",
    body: JSON.stringify({
      left,
      right,
      left_label: opts?.left_label ?? "baseline",
      right_label: opts?.right_label ?? "current",
      context_lines: opts?.context_lines ?? 3,
    }),
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

// Inline PR Review — default autoComment=false (Stage D gate)
export const reviewPRInline = (owner: string, repo: string, prNumber: number, autoComment = false) =>
  request<any>("/api/review/pr/inline", {
    method: "POST",
    body: JSON.stringify({ owner, repo, pr_number: prNumber, auto_comment: autoComment }),
  });

export const ultraReviewApprovePost = (
  sessionId: number,
  findingIds: number[],
  opts?: { owner?: string; repo?: string; pr_number?: number },
) =>
  request<any>(`/api/ultrareview/${sessionId}/approve-post`, {
    method: "POST",
    body: JSON.stringify({
      finding_ids: findingIds,
      ...(opts?.owner ? { owner: opts.owner } : {}),
      ...(opts?.repo ? { repo: opts.repo } : {}),
      ...(opts?.pr_number != null ? { pr_number: opts.pr_number } : {}),
    }),
  });

export const ultraReviewPostGithub = (sessionId: number, owner: string, repo: string, prNumber: number) =>
  request<any>(`/api/ultrareview/${sessionId}/post-github`, {
    method: "POST",
    body: JSON.stringify({ owner, repo, pr_number: prNumber }),
  });

export const ultraReviewStartFixRun = (
  sessionId: number,
  workspace: string,
  opts?: { project_key?: string; project_id?: number; repo_id?: number; owner?: string; repo?: string; pr_number?: number },
) =>
  request<any>(`/api/ultrareview/${sessionId}/start-fix-run`, {
    method: "POST",
    body: JSON.stringify({
      workspace,
      project_key: opts?.project_key || "",
      ...(opts?.project_id != null ? { project_id: opts.project_id } : {}),
      ...(opts?.repo_id != null ? { repo_id: opts.repo_id } : {}),
      ...(opts?.owner ? { owner: opts.owner } : {}),
      ...(opts?.repo ? { repo: opts.repo } : {}),
      ...(opts?.pr_number != null ? { pr_number: opts.pr_number } : {}),
    }),
  });

export const getUltraReview = (sessionId: number) =>
  request<any>(`/api/ultrareview/${sessionId}`);
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

// Conversations
export const getConversations = (mode?: string, isArchived = false, skip = 0, limit = 50) => {
  const params = new URLSearchParams();
  if (mode) params.set("mode", mode);
  params.set("is_archived", String(isArchived));
  params.set("skip", String(skip));
  params.set("limit", String(limit));
  return request<any>(`/api/conversations?${params}`);
};
export const createConversation = (title: string, mode = "ask", projectId?: number) =>
  request<any>("/api/conversations", {
    method: "POST",
    body: JSON.stringify({ title, mode, ...(projectId ? { project_id: projectId } : {}) }),
  });
export const getConversation = (id: number) => request<any>(`/api/conversations/${id}`);
export const updateConversation = (id: number, data: { title?: string; is_pinned?: boolean; is_archived?: boolean }) =>
  request<any>(`/api/conversations/${id}`, { method: "PUT", body: JSON.stringify(data) });
export const deleteConversation = (id: number) =>
  request<void>(`/api/conversations/${id}`, { method: "DELETE" });
export const addConversationMessage = (conversationId: number, role: string, content: string, model = "", tokensUsed = 0, costUsd = 0) =>
  request<any>(`/api/conversations/${conversationId}/messages`, {
    method: "POST",
    body: JSON.stringify({ role, content, model, tokens_used: tokensUsed, cost_usd: costUsd }),
  });
export const getConversationMessages = (conversationId: number, skip = 0, limit = 100) =>
  request<any>(`/api/conversations/${conversationId}/messages?skip=${skip}&limit=${limit}`);

// Knowledge Base
export const getKnowledgeEntries = (category?: string, search?: string, skip = 0, limit = 50) => {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  if (search) params.set("search", search);
  params.set("skip", String(skip));
  params.set("limit", String(limit));
  return request<any>(`/api/knowledge?${params}`);
};
export const createKnowledgeEntry = (data: { title: string; content: string; category?: string; tags?: string[] }) =>
  request<any>("/api/knowledge", { method: "POST", body: JSON.stringify(data) });
export const getKnowledgeEntry = (id: number) => request<any>(`/api/knowledge/${id}`);
export const updateKnowledgeEntry = (id: number, data: { title?: string; content?: string; category?: string; tags?: string[]; is_active?: boolean }) =>
  request<any>(`/api/knowledge/${id}`, { method: "PUT", body: JSON.stringify(data) });
export const deleteKnowledgeEntry = (id: number) =>
  request<void>(`/api/knowledge/${id}`, { method: "DELETE" });
export const getKnowledgeCategories = () => request<any[]>("/api/knowledge/categories");
export const searchKnowledge = (query: string, category?: string) =>
  request<any[]>("/api/knowledge/search", {
    method: "POST",
    body: JSON.stringify({ query, category: category || undefined }),
  });
export const knowledgeForContext = (data: {
  query?: string;
  project_id?: number;
  category?: string;
  tags?: string[];
  max_tokens?: number;
  limit?: number;
}) =>
  request<{
    context: string;
    entry_ids: number[];
    entry_count: number;
    chars: number;
    tokens_estimated: number;
    max_tokens: number;
  }>("/api/knowledge/context", { method: "POST", body: JSON.stringify(data) });

// Playbooks
export const getPlaybooks = (category?: string, skip = 0, limit = 50) => {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  params.set("skip", String(skip));
  params.set("limit", String(limit));
  return request<any>(`/api/playbooks?${params}`);
};
export const createPlaybook = (data: { name: string; description?: string; category?: string; steps?: any[]; variables?: any[] }) =>
  request<any>("/api/playbooks", { method: "POST", body: JSON.stringify(data) });
export const getPlaybook = (id: number) => request<any>(`/api/playbooks/${id}`);
export const updatePlaybook = (id: number, data: { name?: string; description?: string; category?: string; steps?: any[]; variables?: any[]; is_active?: boolean }) =>
  request<any>(`/api/playbooks/${id}`, { method: "PUT", body: JSON.stringify(data) });
export const deletePlaybook = (id: number) =>
  request<void>(`/api/playbooks/${id}`, { method: "DELETE" });
export const runPlaybook = (id: number, variablesUsed: Record<string, string> = {}) =>
  request<any>(`/api/playbooks/${id}/run`, { method: "POST", body: JSON.stringify({ variables_used: variablesUsed }) });
export const getPlaybookRuns = (id: number) => request<any>(`/api/playbooks/${id}/runs`);
export const getPlaybookCategories = () => request<any[]>("/api/playbooks/categories");

// Schedules
export const getSchedules = (taskType?: string, isActive?: boolean, skip = 0, limit = 50) => {
  const params = new URLSearchParams();
  if (taskType) params.set("task_type", taskType);
  if (isActive !== undefined) params.set("is_active", String(isActive));
  params.set("skip", String(skip));
  params.set("limit", String(limit));
  return request<any>(`/api/schedules?${params}`);
};
export const createSchedule = (data: {
  name: string;
  description?: string;
  schedule_type?: string;
  cron_expression?: string;
  interval_minutes?: number;
  task_type?: string;
  playbook_id?: number;
  task_config?: Record<string, any>;
  project_id?: number;
}) =>
  request<any>("/api/schedules", { method: "POST", body: JSON.stringify(data) });
export const getSchedule = (id: number) => request<any>(`/api/schedules/${id}`);
export const updateSchedule = (id: number, data: {
  name?: string;
  description?: string;
  cron_expression?: string;
  task_config?: Record<string, any>;
  is_active?: boolean;
  playbook_id?: number | null;
  task_type?: string;
}) =>
  request<any>(`/api/schedules/${id}`, { method: "PUT", body: JSON.stringify(data) });
export const deleteSchedule = (id: number) =>
  request<void>(`/api/schedules/${id}`, { method: "DELETE" });
export const toggleSchedule = (id: number) =>
  request<any>(`/api/schedules/${id}/toggle`, { method: "POST" });
export const triggerSchedule = (id: number) =>
  request<any>(`/api/schedules/${id}/trigger`, { method: "POST" });
export const getScheduleRuns = (id: number) => request<any>(`/api/schedules/${id}/runs`);

// Secrets
export const getSecrets = (scope?: string, projectId?: number) => {
  const params = new URLSearchParams();
  if (scope) params.set("scope", scope);
  if (projectId) params.set("project_id", String(projectId));
  return request<any[]>(`/api/secrets?${params}`);
};
export const createSecret = (data: { name: string; value: string; description?: string; secret_type?: string; scope?: string }) =>
  request<any>("/api/secrets", { method: "POST", body: JSON.stringify(data) });
export const getSecret = (id: number, reveal = false) =>
  request<any>(`/api/secrets/${id}?reveal=${reveal}`);
export const updateSecret = (id: number, data: { value?: string; description?: string; is_active?: boolean }) =>
  request<any>(`/api/secrets/${id}`, { method: "PUT", body: JSON.stringify(data) });
export const deleteSecret = (id: number) =>
  request<void>(`/api/secrets/${id}`, { method: "DELETE" });
export const rotateSecret = (id: number, newValue: string) =>
  request<any>(`/api/secrets/${id}/rotate?new_value=${encodeURIComponent(newValue)}`, { method: "POST" });

// Code Index
export const searchCodeSymbols = (
  query: string,
  symbolType?: string,
  language?: string,
  repoId?: number,
  limit = 50,
  repoIds?: number[],
) => {
  const params = new URLSearchParams();
  params.set("query", query);
  if (symbolType) params.set("symbol_type", symbolType);
  if (language) params.set("language", language);
  if (repoIds?.length) params.set("repo_ids", repoIds.join(","));
  else if (repoId) params.set("repo_id", String(repoId));
  params.set("limit", String(limit));
  return request<any[]>(`/api/code-index/search?${params}`);
};

export type WorkspaceSearchHit = {
  repo_id?: number;
  project_id?: number;
  workspace_id?: string;
  commit_sha?: string;
  path?: string;
  abs_path?: string;
  line?: number;
  content?: string;
  root_label?: string;
};

export const workspaceSearch = (body: {
  pattern: string;
  scope?: "file" | "root" | "workspace";
  repo_ids: number[];
  active_repo_id?: number | null;
  current_file?: string;
  max_results?: number;
}) =>
  request<{
    ok: boolean;
    hits: WorkspaceSearchHit[];
    skipped: { repo_id?: number; reason?: string }[];
    truncated?: boolean;
    limitation?: string;
  }>("/api/workspace/search", {
    method: "POST",
    body: JSON.stringify(body),
  });
export const indexRepo = (repoPath: string, repoId?: number, fileExtensions?: string[]) =>
  request<any>("/api/code-index/index", {
    method: "POST",
    body: JSON.stringify({ repo_path: repoPath, ...(repoId ? { repo_id: repoId } : {}), ...(fileExtensions ? { file_extensions: fileExtensions } : {}) }),
  });
export const getCodeIndexStats = (repoId?: number) =>
  request<any>(`/api/code-index/stats${repoId ? `?repo_id=${repoId}` : ""}`);
export const getFileSymbols = (filePath: string, repoId?: number) => {
  const params = new URLSearchParams();
  if (repoId) params.set("repo_id", String(repoId));
  const q = params.toString();
  const encoded = filePath
    .replace(/\\/g, "/")
    .split("/")
    .filter(Boolean)
    .map(encodeURIComponent)
    .join("/");
  // Preserve leading slash for absolute POSIX paths
  const prefix = filePath.replace(/\\/g, "/").startsWith("/") ? "/" : "";
  return request<any[]>(`/api/code-index/file/${prefix}${encoded}${q ? `?${q}` : ""}`);
};

// Session Insights
export const getSessionInsightsOverview = (days = 30) =>
  request<any>(`/api/session-insights/overview?days=${days}`);
export const getSessionDailyBreakdown = (days = 14) =>
  request<any[]>(`/api/session-insights/daily-breakdown?days=${days}`);
export const getSessionModelUsage = (days = 30) =>
  request<any[]>(`/api/session-insights/model-usage?days=${days}`);
export const getSessionFeatureUsage = (days = 30) =>
  request<any[]>(`/api/session-insights/feature-usage?days=${days}`);
export const getSessionList = (status?: string, sessionType?: string, skip = 0, limit = 50) => {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (sessionType) params.set("session_type", sessionType);
  params.set("skip", String(skip));
  params.set("limit", String(limit));
  return request<any>(`/api/session-insights/sessions?${params}`);
};

// =========================================================================
// Deep Repo Integration — Clone, Browse, Index
// =========================================================================

// Repo Clone
export const cloneRepo = (repoId: number, branch?: string, shallow = true) =>
  request<any>("/api/repos/clone", {
    method: "POST",
    body: JSON.stringify({ repo_id: repoId, branch, shallow }),
  });
export const pullRepo = (repoId: number) =>
  request<any>(`/api/repos/${repoId}/pull`, { method: "POST" });
export const indexClonedRepo = (repoId: number) =>
  request<any>(`/api/repos/${repoId}/index`, { method: "POST" });
export const getRepoCloneStatus = (repoId: number) =>
  request<any>(`/api/repos/${repoId}/status`);
export const getRepoBranches = (repoId: number) =>
  request<any>(`/api/repos/${repoId}/branches`);
export class CheckoutBlockedError extends Error {
  status: number;
  detail: Record<string, unknown>;
  constructor(status: number, detail: Record<string, unknown>) {
    super(
      typeof detail?.error === "string"
        ? String(detail.error)
        : "Checkout blocked",
    );
    this.name = "CheckoutBlockedError";
    this.status = status;
    this.detail = detail;
  }
}

export const checkoutRepoBranch = async (
  repoId: number,
  branch: string,
  dirtyAction: "require_clean" | "stash" | "force_discard" = "require_clean",
) => {
  const res = await apiFetch(`/api/repos/${repoId}/checkout`, {
    method: "POST",
    body: JSON.stringify({ branch, dirty_action: dirtyAction }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail =
      body && typeof body.detail === "object" && body.detail
        ? (body.detail as Record<string, unknown>)
        : { error: typeof body.detail === "string" ? body.detail : res.statusText };
    throw new CheckoutBlockedError(res.status, detail);
  }
  return body;
};
export const deleteRepoClone = (repoId: number) =>
  request<any>(`/api/repos/${repoId}/clone`, { method: "DELETE" });
export const getClonedRepos = () =>
  request<any[]>("/api/repos/cloned");

export const registerLocalRepo = (projectId: number, localPath: string, role = "") =>
  request<any>("/api/repos/register-local", {
    method: "POST",
    body: JSON.stringify({ project_id: projectId, local_path: localPath, role }),
  });

export const discoverLocalRepos = (root: string, maxDepth = 3) =>
  request<{ ok: boolean; root: string; repos: any[]; count: number }>(
    "/api/repos/discover",
    { method: "POST", body: JSON.stringify({ root, max_depth: maxDepth }) },
  );

export const cloneRepoFromUrl = (
  projectId: number,
  gitUrl: string,
  destination = "",
  branch = "",
) =>
  request<any>("/api/repos/clone-url", {
    method: "POST",
    body: JSON.stringify({
      project_id: projectId,
      git_url: gitUrl,
      destination,
      branch,
    }),
  });

export type RepoIdentity = {
  ok?: boolean;
  repo_id?: number;
  cloned?: boolean;
  root_state?: "READY" | "ROOT_UNAVAILABLE" | "ERROR" | string;
  error?: string;
  branch?: string;
  dirty?: boolean;
  origin_url?: string;
  local_path?: string | null;
  head_sha?: string;
  owner?: string;
  name?: string;
};

export const getRepoIdentity = (repoId: number) =>
  request<RepoIdentity>(`/api/repos/${repoId}/identity`);

export const openPrWorktree = (
  repoId: number,
  prNumber: number,
  headBranch: string,
  headSha = "",
) =>
  request<any>(`/api/repos/${repoId}/pr-worktree`, {
    method: "POST",
    body: JSON.stringify({
      pr_number: prNumber,
      head_branch: headBranch,
      head_sha: headSha,
    }),
  });

export const attachProjectRepoById = (projectId: number, repoId: number) =>
  request<Project>(`/api/projects/${projectId}/repos`, {
    method: "POST",
    body: JSON.stringify({ repo_id: repoId }),
  });

// Repo Browser
export const getRepoTree = (repoId: number, path = "", depth = 3) =>
  request<any[]>(`/api/repos/${repoId}/tree?path=${encodeURIComponent(path)}&depth=${depth}`);
export const getRepoFile = (repoId: number, path: string) =>
  request<any>(`/api/repos/${repoId}/file?path=${encodeURIComponent(path)}`);
export const searchRepoFiles = (repoId: number, pattern: string, fileExtensions?: string[], maxResults = 100) =>
  request<any[]>(`/api/repos/${repoId}/search`, {
    method: "POST",
    body: JSON.stringify({ pattern, file_extensions: fileExtensions, max_results: maxResults }),
  });
export const getRepoFileStats = (repoId: number) =>
  request<any>(`/api/repos/${repoId}/file-stats`);
export const writeRepoFile = (repoId: number, path: string, content: string) =>
  request<any>(`/api/repos/${repoId}/write-file`, {
    method: "POST",
    body: JSON.stringify({ path, content }),
  });

// Auth
export const login = (username: string, password: string) =>
  request<{ token: string; username: string }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
export const verifyToken = (token: string, opts?: RequestInit) =>
  request<{ valid: boolean; username: string }>(
    `/api/auth/verify?token=${encodeURIComponent(token)}`,
    opts,
  );
export const logout = (token: string) =>
  request<{ status: string }>(`/api/auth/logout?token=${token}`, { method: "POST" });

// Mentrix long-running engineering runtime
export const mentrixLongRunningStart = (data: {
  work_item_id: number;
  operation_count?: number;
  worktree_path?: string;
  base_commit_sha?: string;
  autonomy?: string;
  model_profile?: string;
  background?: boolean;
}) =>
  request<any>("/api/mentrix/long-running/start", {
    method: "POST",
    body: JSON.stringify(data),
  });
export const mentrixLongRunningGet = (runId: string) =>
  request<any>(`/api/mentrix/long-running/${encodeURIComponent(runId)}`);
export const mentrixLongRunningPause = (runId: string) =>
  request<any>(`/api/mentrix/long-running/${encodeURIComponent(runId)}/pause`, { method: "POST" });
export const mentrixLongRunningResume = (runId: string) =>
  request<any>(`/api/mentrix/long-running/${encodeURIComponent(runId)}/resume`, { method: "POST" });
export const mentrixLongRunningCancel = (runId: string) =>
  request<any>(`/api/mentrix/long-running/${encodeURIComponent(runId)}/cancel`, { method: "POST" });
export const mentrixLongRunningTick = (runId: string, data?: Record<string, unknown>) =>
  request<any>(`/api/mentrix/long-running/${encodeURIComponent(runId)}/tick`, {
    method: "POST",
    body: JSON.stringify(data || { worker_id: "ui", max_ops: 1 }),
  });

// Document Intelligence
export type DocumentArtifactInfo = {
  id: number;
  filename: string;
  scope: string;
  project_id?: number | null;
  content_sha256: string;
  content_version_id?: number | null;
  status: string;
  is_current: boolean;
  reused_shared_version?: boolean;
  partial_capabilities?: string[];
  page_count?: number;
  parser_name?: string;
  freshness?: string;
};

export const uploadDocument = async (opts: {
  file: File;
  projectId?: number | null;
  scope?: "USER_PRIVATE" | "PROJECT_SHARED";
  sensitivity?: string;
  replaceArtifactId?: number | null;
}): Promise<{ ok: boolean; artifact: DocumentArtifactInfo }> => {
  const form = new FormData();
  form.append("file", opts.file);
  if (opts.projectId != null) form.append("project_id", String(opts.projectId));
  form.append("scope", opts.scope || "USER_PRIVATE");
  form.append("sensitivity", opts.sensitivity || "INTERNAL");
  if (opts.replaceArtifactId != null) form.append("replace_artifact_id", String(opts.replaceArtifactId));
  const token = typeof localStorage !== "undefined" ? localStorage.getItem("zect_token") : null;
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API}/api/documents/upload`, { method: "POST", body: form, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = err.detail;
    throw new Error(typeof detail === "string" ? detail : detail?.message || `Upload failed (${res.status})`);
  }
  return res.json();
};

export const listDocuments = (projectId?: number | null) =>
  request<{ documents: DocumentArtifactInfo[] }>(
    `/api/documents${projectId != null ? `?project_id=${projectId}` : ""}`,
  );

export const getDocumentMarkdown = (artifactId: number) =>
  request<{
    artifact_id: number;
    content_version_id?: number | null;
    content_sha256: string;
    is_current: boolean;
    freshness: string;
    markdown: string;
    tag: string;
  }>(`/api/documents/${artifactId}/markdown`);

export const removeDocument = (artifactId: number) =>
  request<{ ok: boolean; id: number; status: string }>(`/api/documents/${artifactId}`, {
    method: "DELETE",
  });

export const retrieveDocumentContext = (data: {
  query?: string;
  project_id?: number | null;
  artifact_ids?: number[];
  max_tokens?: number;
  build_context_pack?: boolean;
}) =>
  request<{
    ok: boolean;
    meta: Record<string, unknown>;
    items: Array<Record<string, unknown>>;
    context_pack?: Record<string, unknown>;
  }>("/api/documents/retrieve", {
    method: "POST",
    body: JSON.stringify(data),
  });

// Web Intelligence
export type WebArtifactInfo = {
  id: number;
  source_url: string;
  title?: string;
  scope: string;
  project_id?: number | null;
  content_sha256: string;
  content_version_id?: number | null;
  status: string;
  is_current: boolean;
  adapter?: string;
  connector_id?: string;
  reused_shared_version?: boolean;
  partial_capabilities?: string[];
  tag?: string;
};

export const attachWebUrl = (opts: {
  url: string;
  projectId?: number | null;
  scope?: "USER_PRIVATE" | "PROJECT_SHARED";
  adapter?: string;
  confirmedBrowser?: boolean;
  replaceArtifactId?: number | null;
}) =>
  request<{ ok: boolean; artifact: WebArtifactInfo; tag: string }>("/api/web/attach", {
    method: "POST",
    body: JSON.stringify({
      url: opts.url,
      project_id: opts.projectId ?? null,
      scope: opts.scope || "USER_PRIVATE",
      adapter: opts.adapter || "url",
      confirmed_browser: !!opts.confirmedBrowser,
      replace_artifact_id: opts.replaceArtifactId ?? null,
    }),
  });

export const getWebMarkdown = (artifactId: number) =>
  request<{
    artifact_id: number;
    content_version_id?: number | null;
    content_sha256: string;
    source_url: string;
    is_current: boolean;
    freshness: string;
    markdown: string;
    tag: string;
  }>(`/api/web/${artifactId}/markdown`);

export const retrieveWebContext = (data: {
  query?: string;
  project_id?: number | null;
  artifact_ids?: number[];
  max_tokens?: number;
  build_context_pack?: boolean;
}) =>
  request<{
    ok: boolean;
    meta: Record<string, unknown>;
    items: Array<Record<string, unknown>>;
    context_pack?: Record<string, unknown>;
    tag: string;
  }>("/api/web/retrieve", {
    method: "POST",
    body: JSON.stringify(data),
  });
