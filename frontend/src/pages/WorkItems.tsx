import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { authHeaders, createSampleProcess, getApiBase } from "@/lib/api";
import LongRunningRunPanel from "@/components/LongRunningRunPanel";

type WorkItem = {
  id: number;
  title: string;
  status: string;
  source?: string;
  external_id?: string;
  repository_ref?: string;
  project_id?: number;
  created_by?: string;
  updated_at?: string;
};


export default function WorkItems() {
  const [items, setItems] = useState<WorkItem[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [sourceFilter, setSourceFilter] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${getApiBase()}/api/work-items?limit=50`, { headers: authHeaders() });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        if (!cancelled) {
          const list = Array.isArray(data) ? data : data.items || [];
          setItems(list);
          if (list[0]?.id) setSelectedId(list[0].id);
        }
      } catch (e: any) {
        if (!cancelled) setError(e?.message || "Failed to load work items");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const selected = items.find((w) => w.id === selectedId) || null;
  const visible = sourceFilter
    ? items.filter((w) => (w.source || "user") === sourceFilter)
    : items;

  return (
    <div className="p-6 max-w-5xl mx-auto" data-testid="work-items-page">
      <h1 className="text-2xl font-semibold text-slate-900">Work Items</h1>
      <p className="mt-1 text-sm text-slate-600">
        Project → WorkItem → ASK/PLAN/AGENT. Sources: user, Jira, Camunda, GitHub, sample.
      </p>
      <button
        type="button"
        data-testid="work-items-sample"
        className="mt-3 rounded-lg border border-teal-200 bg-teal-50 px-3 py-1.5 text-xs text-teal-900"
        onClick={async () => {
          const out = await createSampleProcess();
          setItems((prev) => {
            const wi = out.work_item;
            if (prev.some((p) => p.id === wi.id)) return prev;
            return [wi as WorkItem, ...prev];
          });
        }}
      >
        Create sample process WorkItem
      </button>
      <div className="mt-3 flex flex-wrap gap-2">
        {["", "user", "jira", "camunda", "github"].map((src) => (
          <button
            key={src || "all"}
            type="button"
            data-testid={src ? `work-items-filter-${src}` : "work-items-filter-all"}
            onClick={() => setSourceFilter(src)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
              sourceFilter === src ? "bg-teal-700 text-white" : "border border-slate-200 bg-white text-slate-600"
            }`}
          >
            {src || "All sources"}
          </button>
        ))}
      </div>
      {loading && <p className="mt-6 text-sm text-slate-500">Loading…</p>}
      {error && <p className="mt-6 text-sm text-red-600">{error}</p>}
      {!loading && !error && items.length === 0 && (
        <p className="mt-6 text-sm text-slate-500">No work items yet. Ingest from Jira/Camunda or create via Mentrix Developer.</p>
      )}
      <ul className="mt-6 space-y-2">
        {visible.map((wi) => (
          <li key={wi.id} className="rounded-lg border border-slate-200 px-4 py-3 flex items-center justify-between gap-4">
            <button type="button" className="text-left" onClick={() => setSelectedId(wi.id)}>
              <p className="font-medium text-slate-900">#{wi.id} {wi.title}</p>
              <p className="text-xs text-slate-500">
                {wi.source || "user"}
                {wi.project_id ? ` · project ${wi.project_id}` : ""}
                {wi.external_id ? ` · ${wi.external_id}` : ""}
                {wi.repository_ref ? ` · ${wi.repository_ref}` : ""}
                {wi.updated_at ? ` · ${wi.updated_at}` : ""}
              </p>
            </button>
            <span className="text-xs font-medium uppercase tracking-wide text-slate-600">{wi.status}</span>
          </li>
        ))}
      </ul>
      {selected && <LongRunningRunPanel workItemId={selected.id} title={selected.title} />}
      <p className="mt-8 text-sm">
        <Link className="text-teal-700 hover:underline" to="/workspace">Open Developer Workspace</Link>
        {" · "}
        <Link className="text-teal-700 hover:underline" to="/project-intelligence">Project Intelligence</Link>
      </p>
    </div>
  );
}
