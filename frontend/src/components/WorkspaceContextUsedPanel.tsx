import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, RefreshCw } from "lucide-react";
import { apiFetch } from "@/lib/api";
import {
  buildContextUsedRows,
  type ContextUsedRow,
  type ContextUsedStatus,
  type ModelReadinessLite,
  type ProjectIntelligenceLite,
  type WorkItemLite,
} from "@/lib/contextUsed";

type Props = {
  projectId?: number | null;
  projectKey?: string;
  repositoryId?: number | null;
  activeRepoLabel?: string;
  workItemId?: number | null;
};

const STATUS_CLASS: Record<ContextUsedStatus, string> = {
  used: "bg-teal-100 text-teal-800",
  missing: "bg-rose-100 text-rose-800",
  stale: "bg-amber-100 text-amber-900",
  not_used: "bg-slate-100 text-slate-600",
  unverified: "bg-orange-100 text-orange-900",
};

/**
 * Context Used — reads P1 ProjectIntelligence + WorkItems + model-readiness.
 * Does not invent a second context engine.
 */
export default function WorkspaceContextUsedPanel({
  projectId,
  projectKey = "",
  repositoryId,
  activeRepoLabel = "",
  workItemId,
}: Props) {
  const [rows, setRows] = useState<ContextUsedRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeWiId, setActiveWiId] = useState<number | null>(workItemId ?? null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      let wi: WorkItemLite | null = null;
      if (workItemId) {
        const wr = await apiFetch(`/api/work-items/${workItemId}`);
        if (wr.ok) wi = (await wr.json()) as WorkItemLite;
      } else {
        const qs = new URLSearchParams({ limit: "5" });
        if (projectId != null) qs.set("project_id", String(projectId));
        const wr = await apiFetch(`/api/work-items?${qs}`);
        if (wr.ok) {
          const data = await wr.json();
          const items: WorkItemLite[] = Array.isArray(data) ? data : data.items || [];
          wi = items[0] || null;
        }
      }
      setActiveWiId(wi?.id ?? null);

      const piQs = new URLSearchParams({ query: projectKey || "workspace" });
      if (projectId != null) piQs.set("project_id", String(projectId));
      if (projectKey) piQs.set("project_key", projectKey);
      if (repositoryId != null) piQs.set("repository_id", String(repositoryId));
      const [piRes, modelRes] = await Promise.all([
        apiFetch(`/api/mentrix/developer/project-intelligence?${piQs}`),
        apiFetch(`/api/system/model-readiness`),
      ]);
      const pi: ProjectIntelligenceLite | null = piRes.ok ? await piRes.json() : null;
      const model: ModelReadinessLite | null = modelRes.ok ? await modelRes.json() : null;
      if (!piRes.ok && !modelRes.ok && !wi) {
        throw new Error("Could not load Project Intelligence or model readiness");
      }
      setRows(
        buildContextUsedRows({
          workItem: wi,
          pi,
          model,
          activeRepoLabel,
        }),
      );
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load Context Used");
      setRows(
        buildContextUsedRows({
          workItem: null,
          pi: null,
          model: null,
          activeRepoLabel,
        }),
      );
    } finally {
      setLoading(false);
    }
  }, [projectId, projectKey, repositoryId, activeRepoLabel, workItemId]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <aside
      className="w-full lg:w-72 shrink-0 flex flex-col min-h-0 rounded-lg border border-slate-200 bg-white"
      data-testid="workspace-context-used"
    >
      <div className="flex items-center justify-between gap-2 border-b border-slate-100 px-3 py-2">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Context Used</p>
          <p className="text-[10px] text-slate-400">Project Intelligence · WorkItem · model route</p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="inline-flex items-center gap-1 rounded border border-slate-200 px-1.5 py-1 text-[10px] text-slate-600"
          data-testid="workspace-context-used-refresh"
        >
          {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
          Refresh
        </button>
      </div>
      {error ? (
        <p className="px-3 py-2 text-[11px] text-rose-700" data-testid="workspace-context-used-error">
          {error}
        </p>
      ) : null}
      <ul className="flex-1 overflow-auto px-2 py-2 space-y-1.5" data-testid="workspace-context-used-rows">
        {rows.map((row) => (
          <li key={row.id} className="rounded-md border border-slate-100 px-2 py-1.5" data-testid={`context-used-${row.id}`}>
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] font-medium text-slate-800">{row.label}</span>
              <span className={`rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase ${STATUS_CLASS[row.status]}`}>
                {row.status.replace("_", " ")}
              </span>
            </div>
            <p className="mt-0.5 text-[10px] leading-snug text-slate-500">{row.detail}</p>
          </li>
        ))}
      </ul>
      <div className="border-t border-slate-100 px-3 py-2 text-[10px] text-slate-500">
        {activeWiId ? (
          <Link className="text-teal-700 hover:underline" to="/work-items">
            WorkItem #{activeWiId}
          </Link>
        ) : (
          <Link className="text-teal-700 hover:underline" to="/project-intelligence">
            Open Project Intelligence
          </Link>
        )}
      </div>
    </aside>
  );
}
