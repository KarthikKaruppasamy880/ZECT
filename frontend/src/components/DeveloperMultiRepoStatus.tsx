import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

type RepoRow = {
  repository_id?: number;
  label?: string;
  status?: string;
  worktree_path?: string;
  head_sha?: string;
  base_commit_sha?: string;
};

type PullRow = {
  repository_id?: number;
  branch?: string;
  pr_status?: string;
  pr_url?: string | null;
  pr_number?: number | null;
  head_sha?: string;
  worktree_path?: string;
  review?: string;
};

type MultiRepoStatus = {
  work_item_id?: number;
  multi_repo?: boolean;
  aggregate_status?: string;
  ready_to_ship?: boolean;
  work_item_status?: string;
  affected_repos?: RepoRow[];
  operations?: { id?: string; repository_id?: number; status?: string; worktree_path?: string }[];
  worktrees?: { repository_id?: number; worktree_path?: string; head_sha?: string }[];
  tests?: { ok?: boolean; by_repository?: Record<string, { ok?: boolean; status?: string; kind?: string }> };
  pull_requests?: PullRow[];
};

type Props = {
  workItemId?: number | null;
  projectId?: number | null;
};

function shaShort(sha?: string) {
  return sha ? sha.slice(0, 8) : "—";
}

export default function DeveloperMultiRepoStatus({ workItemId, projectId }: Props) {
  const [data, setData] = useState<MultiRepoStatus | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      let id = workItemId ?? null;
      if (!id && projectId != null) {
        const wr = await apiFetch(`/api/work-items?project_id=${projectId}&limit=8`);
        if (wr.ok) {
          const body = await wr.json();
          const items = Array.isArray(body) ? body : body.items || [];
          const hit = items.find((w: { id?: number }) => w?.id) || items[0];
          id = hit?.id ?? null;
        }
      }
      if (!id) {
        setData(null);
        return;
      }
      const res = await apiFetch(`/api/mentrix/developer/work-items/${id}/multi-repo-status`);
      if (!res.ok) {
        setData(null);
        return;
      }
      setData((await res.json()) as MultiRepoStatus);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load multi-repo status");
    }
  }, [workItemId, projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  const repos = data?.affected_repos || [];
  const testsBy = data?.tests?.by_repository || {};
  const prs = data?.pull_requests || [];
  const agg = data?.aggregate_status || (repos.length ? "pending" : "idle");
  const ready = Boolean(data?.ready_to_ship);

  return (
    <section
      className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700"
      data-testid="developer-multi-repo-status"
    >
      <div className="flex items-center justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Multi-repo agent</p>
        <span
          className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
            ready ? "bg-teal-100 text-teal-800" : "bg-amber-100 text-amber-900"
          }`}
          data-testid="developer-multi-repo-aggregate"
        >
          {ready ? "ready_to_ship" : agg}
        </span>
      </div>
      {error ? <p className="mt-1 text-[11px] text-rose-700">{error}</p> : null}
      {!repos.length ? (
        <p className="mt-1 text-[11px] text-slate-400">No affected repositories on this WorkItem yet.</p>
      ) : (
        <ul className="mt-2 space-y-1.5">
          {repos.map((repo) => {
            const id = Number(repo.repository_id);
            const t = testsBy[String(id)] || {};
            const pr = prs.find((p) => Number(p.repository_id) === id);
            return (
              <li
                key={id || repo.label}
                className="rounded border border-slate-100 px-2 py-1.5"
                data-testid={`developer-repo-row-${id}`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium text-slate-800">{repo.label || `repo ${id}`}</span>
                  <span className="uppercase text-[10px] text-slate-500">{repo.status || "pending"}</span>
                </div>
                <p className="mt-0.5 font-mono text-[10px] text-slate-500 truncate" title={repo.worktree_path}>
                  wt {repo.worktree_path || "—"} · {shaShort(repo.head_sha || repo.base_commit_sha)}
                </p>
                <p className="text-[10px] text-slate-500">
                  tests {t.ok === true ? "pass" : t.ok === false ? "fail" : "—"}
                  {t.kind ? ` (${t.kind})` : ""} · pr {pr?.pr_status || "—"}
                  {pr?.pr_url ? ` ${pr.pr_url}` : ""}
                  {pr?.branch ? ` · ${pr.branch}` : ""}
                </p>
              </li>
            );
          })}
        </ul>
      )}
      {data?.operations?.length ? (
        <p className="mt-1 text-[10px] text-slate-400" data-testid="developer-multi-repo-ops">
          {data.operations.length} operation{data.operations.length === 1 ? "" : "s"}
        </p>
      ) : null}
    </section>
  );
}
