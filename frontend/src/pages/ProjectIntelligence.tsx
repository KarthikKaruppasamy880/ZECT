import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { authHeaders, getApiBase, indexClonedRepo, latticeIngest } from "@/lib/api";

type LatticeSnap = {
  state?: string;
  status?: string;
  action?: string | null;
  action_label?: string;
  repository_id?: number | null;
  project_key?: string;
  local_path?: string;
  detail?: { indexed_at?: string | null; files_indexed?: number; reason?: string; local_path?: string };
};

export default function ProjectIntelligencePage() {
  const [snap, setSnap] = useState<Record<string, unknown> | null>(null);
  const [query, setQuery] = useState("project");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [indexNote, setIndexNote] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const qs = new URLSearchParams({ query });
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
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const lattice = (snap?.lattice || {}) as LatticeSnap;
  const state = String(lattice.state || lattice.status || "NOT_APPLICABLE");
  const repoId = Number(lattice.repository_id || 0);

  const handleIndex = async () => {
    if (!repoId) {
      setIndexNote("Select a cloned repository in Developer, then Index.");
      return;
    }
    setIndexNote("Indexing…");
    try {
      const localPath = String(lattice.local_path || lattice.detail?.local_path || "").trim();
      const projectKey = String(lattice.project_key || "").trim();
      if (localPath) {
        await latticeIngest(localPath, projectKey || localPath, true, true);
        setIndexNote("Lattice ingest requested. Refresh to see READY or STALE.");
      } else {
        await indexClonedRepo(repoId);
        setIndexNote("Symbol index requested (no local path). Bind a clone for Lattice ingest.");
      }
      await load();
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
        <span className="text-sm text-slate-600">
          {lattice.action_label || lattice.detail?.reason || "No project key bound"}
        </span>
        {lattice.detail?.indexed_at ? (
          <span className="text-xs text-slate-500">Indexed {lattice.detail.indexed_at}</span>
        ) : null}
        <button
          type="button"
          className="zect-btn zect-btn-secondary text-xs"
          data-testid="pi-index-repository"
          onClick={() => void handleIndex()}
        >
          {state === "READY" || state === "STALE" ? "Re-index" : "Index Repository"}
        </button>
        <Link to="/lattice" className="zect-btn zect-btn-primary text-xs">
          View Intelligence
        </Link>
        {indexNote ? <p className="w-full text-xs text-slate-500">{indexNote}</p> : null}
      </div>
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
          className="zect-btn zect-btn-primary"
          onClick={() => void load()}
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
