import { useEffect, useState } from "react";
import { authHeaders } from "@/lib/api";

const API = import.meta.env.VITE_API_URL || "";

export default function ProjectIntelligencePage() {
  const [snap, setSnap] = useState<Record<string, unknown> | null>(null);
  const [query, setQuery] = useState("project");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const qs = new URLSearchParams({ query });
      const res = await fetch(`${API}/api/mentrix/developer/project-intelligence?${qs}`, {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error(await res.text());
      setSnap(await res.json());
    } catch (e: any) {
      setError(e?.message || "Failed to load Project Intelligence");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="p-6 max-w-5xl mx-auto" data-testid="project-intelligence-page">
      <h1 className="text-2xl font-semibold text-slate-900">Project Intelligence</h1>
      <p className="mt-1 text-sm text-slate-600">
        Lattice, Blueprint, Knowledge, Memory, Skills, and Playbooks — fed into Mentrix Ask/Plan/Agent.
      </p>
      <div className="mt-4 flex gap-2">
        <input
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Query"
          data-testid="pi-query"
        />
        <button
          type="button"
          className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white"
          onClick={() => void load()}
          data-testid="pi-refresh"
        >
          Refresh
        </button>
      </div>
      {loading && <p className="mt-4 text-sm text-slate-500">Loading…</p>}
      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      {snap && (
        <pre className="mt-6 overflow-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-100" data-testid="pi-snapshot">
          {JSON.stringify(snap, null, 2)}
        </pre>
      )}
    </div>
  );
}
