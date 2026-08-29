/**
 * Companion orchestration strip — active Project, authorized roots, WorkItem, provenance.
 * Does not duplicate Developer Context Used; this is the HUD/dock identity chip.
 */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useActiveProject } from "@/contexts/ActiveProjectContext";
import { mentrixCompanionScope, type CompanionScopeEnvelope, type CompanionProvenanceRow } from "@/lib/api";

type Props = {
  compact?: boolean;
  provenance?: CompanionProvenanceRow[];
  progress?: {
    task?: string;
    stage?: string;
    blocker?: string;
    affected_repos?: number[];
  } | null;
};

export default function CompanionScopeStrip({ compact = false, provenance = [], progress = null }: Props) {
  const { activeProjectId, activeRepoId, activeProject } = useActiveProject();
  const [scope, setScope] = useState<CompanionScopeEnvelope | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const next = await mentrixCompanionScope({
        projectId: activeProjectId,
      });
      setScope(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scope unavailable");
    }
  }, [activeProjectId, activeRepoId]);

  useEffect(() => {
    void load();
  }, [load]);

  const roots = scope?.roots || [];
  const projectLabel = scope?.project_name || activeProject?.name || "No project";
  const workLabel = scope?.work_item_title
    ? `#${scope.work_item_id} ${scope.work_item_title}`
    : "No WorkItem";

  return (
    <div
      className={`rounded-lg border border-slate-800 bg-slate-900/80 ${compact ? "px-2 py-1" : "px-3 py-2"}`}
      data-testid="mentrix-companion-scope"
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-300">
        <span data-testid="mentrix-companion-scope-project" title={projectLabel}>
          Project <strong className="text-teal-200">{projectLabel}</strong>
        </span>
        <span data-testid="mentrix-companion-scope-roots">
          Roots{" "}
          {roots.length ? (
            roots.map((r) => (
              <span
                key={r.id}
                className={`ml-1 rounded border px-1 ${
                  r.id === (scope?.active_root_id || activeRepoId)
                    ? "border-teal-700 text-teal-200"
                    : "border-slate-700 text-slate-400"
                }`}
                data-testid={`mentrix-companion-root-${r.id}`}
                title={`${r.path} ${r.commit_sha || ""} ${r.lattice_state}`}
              >
                {r.label}
                {r.commit_sha ? ` @${r.commit_sha.slice(0, 7)}` : ""}
              </span>
            ))
          ) : (
            <span className="text-slate-500">none</span>
          )}
        </span>
        <span data-testid="mentrix-companion-scope-workitem">{workLabel}</span>
        <span className="text-slate-500" data-testid="mentrix-companion-semantic-cross-repo">
          Semantic cross-repo refs: not implemented
        </span>
        {error ? <span className="text-amber-400">{error}</span> : null}
      </div>
      {!compact ? (
        <div className="mt-1.5 flex flex-wrap gap-1.5 text-[10px]">
          <Link className="rounded border border-slate-700 px-1.5 py-0.5 text-teal-300" to={scope?.handoffs?.workspace || "/workspace"}>
            Developer
          </Link>
          <Link className="rounded border border-slate-700 px-1.5 py-0.5 text-teal-300" to={scope?.handoffs?.present || "/present"} data-testid="mentrix-scope-handoff-present">
            Present
          </Link>
          <Link className="rounded border border-slate-700 px-1.5 py-0.5 text-teal-300" to={scope?.handoffs?.work_items || "/work-items"}>
            Work Items
          </Link>
          <Link className="rounded border border-slate-700 px-1.5 py-0.5 text-teal-300" to="/projects">
            Projects
          </Link>
        </div>
      ) : null}
      {progress?.stage ? (
        <p className="mt-1 text-[10px] text-amber-200" data-testid="mentrix-companion-progress">
          {progress.task || "Task"} · {progress.stage}
          {progress.affected_repos?.length ? ` · repos ${progress.affected_repos.join(",")}` : ""}
          {progress.blocker ? ` · blocker ${progress.blocker}` : ""}
        </p>
      ) : null}
      {provenance.length > 0 ? (
        <div className="mt-1.5 flex flex-wrap gap-1" data-testid="mentrix-companion-provenance">
          {provenance.map((row) => (
            <span
              key={row.id}
              data-testid={`mentrix-provenance-${row.id}`}
              data-status={row.status}
              title={row.detail}
              className={`rounded px-1.5 py-0.5 text-[10px] ${
                row.status === "used"
                  ? "bg-teal-950 text-teal-200"
                  : row.status === "stale"
                    ? "bg-amber-950 text-amber-200"
                    : row.status === "missing"
                      ? "bg-rose-950 text-rose-200"
                      : "bg-slate-800 text-slate-400"
              }`}
            >
              {row.label}: {row.status}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}
