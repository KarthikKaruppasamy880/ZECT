import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { authHeaders, getApiBase, indexClonedRepo, latticeIngest } from "@/lib/api";
import { useActiveProject } from "@/contexts/ActiveProjectContext";

type LatticeHit = {
  id?: string;
  text?: string;
  summary?: string;
  content?: string;
};

type LatticeSnap = {
  state?: string;
  status?: string;
  action?: string | null;
  action_label?: string;
  repository_id?: number | null;
  project_key?: string;
  local_path?: string;
  hits?: LatticeHit[];
  detail?: { indexed_at?: string | null; files_indexed?: number; reason?: string; local_path?: string };
};

export default function ProjectIntelligencePage() {
  const { activeProjectId, activeRepoId, activeProjectKey, activeLocalPath, activeRepo } = useActiveProject();
  const [snap, setSnap] = useState<Record<string, unknown> | null>(null);
  const [query, setQuery] = useState("project");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [indexNote, setIndexNote] = useState("");

  const repoLabel = activeRepo
    ? `${activeRepo.owner}/${activeRepo.repo_name}`
    : "";

  const load = useCallback(
    async (q: string) => {
      setLoading(true);
      setError("");
      try {
        const qs = new URLSearchParams({ query: q });
        if (activeProjectId) qs.set("project_id", String(activeProjectId));
        if (activeProjectKey) qs.set("project_key", activeProjectKey);
        if (activeRepoId) qs.set("repository_id", String(activeRepoId));
        const res = await fetch(`${getApiBase()}/api/mentrix/developer/project-intelligence?${qs}`, {
          headers: authHeaders(),
        });
        if (!res.ok) throw new Error(await res.text());
        setSnap(await res.json());
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load Project Intelligence");
      } finally {
        setLoading(false);
      }
    },
    [activeProjectId, activeProjectKey, activeRepoId],
  );

  useEffect(() => {
    void load(query);
    // query is applied on Refresh / project change (current query value on bind)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeProjectId, activeProjectKey, activeRepoId, load]);

  const lattice = (snap?.lattice || {}) as LatticeSnap;
  const state = String(lattice.state || lattice.status || "NOT_APPLICABLE");
  const repoId = Number(lattice.repository_id || activeRepoId || 0);
  const hits = Array.isArray(lattice.hits) ? lattice.hits : [];

  const handleIndex = async () => {
    const boundId = repoId || Number(activeRepoId || 0);
    if (!boundId && !activeLocalPath) {
      setIndexNote("Select a project and cloned repository in the header, then Index.");
      return;
    }
    setIndexNote("Indexing…");
    try {
      const localPath = String(activeLocalPath || lattice.local_path || lattice.detail?.local_path || "").trim();
      const projectKey = String(activeProjectKey || lattice.project_key || "").trim();
      if (localPath) {
        await latticeIngest(localPath, projectKey || localPath, true, true);
        setIndexNote("Lattice ingest requested. Refresh to see READY or STALE.");
      } else if (boundId) {
        await indexClonedRepo(boundId);
        setIndexNote("Symbol index requested (no local path). Bind a clone for Lattice ingest.");
      }
      await load(query);
    } catch (e: unknown) {
      setIndexNote(e instanceof Error ? e.message : "Index failed");
    }
  };

  return (
    <div className="zect-page p-6 max-w-5xl mx-auto" data-testid="project-intelligence-page">
      <h1 className="text-2xl font-semibold text-slate-900">Project Intelligence</h1>
      <p className="mt-1 text-sm text-slate-600">
        Lattice, Blueprint, Knowledge, Memory, Skills, and Playbooks — fed into Mentrix Ask/Plan/Agent.
      </p>
      <div
        className="mt-4 zect-panel flex flex-wrap items-center gap-3"
        data-testid="pi-lattice-state"
      >
        <span className="zect-chip bg-slate-100 text-slate-800">{state}</span>
        <span className="text-sm text-slate-600" data-testid="pi-bound-repo">
          {lattice.action_label ||
            lattice.detail?.reason ||
            (repoLabel ? `Bound to ${repoLabel}` : "Select a project or repository in the header")}
        </span>
        {lattice.detail?.indexed_at ? (
          <span className="text-xs text-slate-500">Indexed {lattice.detail.indexed_at}</span>
        ) : null}
        <button
          type="button"
          className="zect-btn zect-btn-secondary text-xs min-h-11"
          data-testid="pi-index-repository"
          onClick={() => void handleIndex()}
        >
          {state === "READY" || state === "STALE" ? "Re-index" : "Index Repository"}
        </button>
        <Link to="/lattice" className="zect-btn zect-btn-primary text-xs min-h-11 inline-flex items-center">
          View Intelligence
        </Link>
        {state === "STALE" || state === "NOT_APPLICABLE" ? (
          <p className="w-full text-xs text-amber-800" data-testid="pi-reindex-hint">
            Lattice is {state}
            {repoLabel ? ` for ${repoLabel}` : ""}. Re-index the cloned root on this page or open Lattice — this
            view is empty until ingest runs. Raw JSON below is not a substitute for an index.
          </p>
        ) : null}
        {indexNote ? <p className="w-full text-xs text-slate-500">{indexNote}</p> : null}
      </div>
      {hits.length > 0 ? (
        <ul className="mt-4 space-y-2" data-testid="pi-lattice-hits">
          {hits.slice(0, 12).map((hit, i) => (
            <li
              key={hit.id || `${i}`}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800"
            >
              <p className="font-medium">{hit.text || hit.id || "Hit"}</p>
              {hit.summary || hit.content ? (
                <p className="mt-0.5 text-xs text-slate-600 line-clamp-3">{hit.summary || hit.content}</p>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
      <div className="mt-4 flex gap-2">
        <input
          className="zect-input flex-1"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Query"
          aria-label="Project intelligence query"
          data-testid="pi-query"
        />
        <button
          type="button"
          className="zect-btn zect-btn-primary min-h-11"
          onClick={() => void load(query)}
          data-testid="pi-refresh"
        >
          Refresh
        </button>
      </div>
      {loading && (
        <p className="mt-4 text-sm text-slate-500" role="status">
          Loading…
        </p>
      )}
      {error && (
        <p className="mt-4 text-sm text-red-600" role="alert" data-testid="pi-error">
          {error}
        </p>
      )}
      {snap && (
        <pre className="mt-6 overflow-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-100" data-testid="pi-snapshot">
          {JSON.stringify(snap, null, 2)}
        </pre>
      )}
    </div>
  );
}
