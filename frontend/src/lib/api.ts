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
