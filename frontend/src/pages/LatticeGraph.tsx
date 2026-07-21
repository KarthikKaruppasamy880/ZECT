import { useState } from "react";
import { Network, Search, Upload } from "lucide-react";
import { latticeGraph, latticeIngest, latticeQuery, latticeRagSearch } from "@/lib/api";

export default function LatticeGraph() {
  const [path, setPath] = useState("");
  const [projectKey, setProjectKey] = useState("");
  const [query, setQuery] = useState("");
  const [graph, setGraph] = useState<any>(null);
  const [hits, setHits] = useState<any[]>([]);
  const [rag, setRag] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const key = projectKey || path;

  const ingest = async () => {
    setError("");
    setLoading(true);
    try {
      const res = await latticeIngest(path, key, true);
      setGraph(res.graph);
      setProjectKey(res.graph?.project_key || key);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ingest failed");
    } finally {
      setLoading(false);
    }
  };

  const loadGraph = async () => {
    setError("");
    setLoading(true);
    try {
      const res = await latticeGraph(key);
      setGraph(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Load failed");
    } finally {
      setLoading(false);
    }
  };

  const runQuery = async () => {
    setError("");
    setLoading(true);
    try {
      const [g, r] = await Promise.all([
        latticeQuery(key, query),
        latticeRagSearch(query, key),
      ]);
      setHits(g.hits || []);
      setRag(r.hits || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Query failed");
    } finally {
      setLoading(false);
    }
  };

  const nodes = graph?.nodes?.slice(0, 80) || [];
  const edges = graph?.edges?.slice(0, 120) || [];

  return (
    <div className="max-w-6xl mx-auto space-y-6 p-1" data-testid="lattice-page">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-slate-800 border border-slate-700">
          <Network className="h-6 w-6 text-teal-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Lattice</h1>
          <p className="text-sm text-slate-600">
            Mentrix Understand — index local repos into a symbol graph + RAG chunks.
          </p>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <label className="block text-sm">
          <span className="text-slate-600">Local path</span>
          <input
            value={path}
            onChange={(e) => setPath(e.target.value)}
            placeholder="C:\\repos\\my-service"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
          />
        </label>
        <label className="block text-sm">
          <span className="text-slate-600">Project key</span>
          <input
            value={projectKey}
            onChange={(e) => setProjectKey(e.target.value)}
            placeholder="optional alias"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
          />
        </label>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          onClick={ingest}
          disabled={!path || loading}
          className="inline-flex items-center gap-2 rounded-lg bg-teal-700 px-4 py-2 text-white disabled:opacity-50"
        >
          <Upload className="h-4 w-4" />
          Ingest + RAG
        </button>
        <button
          onClick={loadGraph}
          disabled={!key || loading}
          className="rounded-lg border border-slate-300 px-4 py-2 disabled:opacity-50"
        >
          Load graph
        </button>
      </div>

      <div className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search symbols or ask Mentrix Scout…"
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2"
        />
        <button
          onClick={runQuery}
          disabled={!key || !query || loading}
          className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-white disabled:opacity-50"
        >
          <Search className="h-4 w-4" />
          Query
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {graph && (
        <div className="grid gap-4 md:grid-cols-3">
          <Stat label="Files" value={graph.files_indexed ?? "—"} />
          <Stat label="Symbols" value={graph.symbols ?? nodes.length} />
          <Stat label="Edges" value={edges.length} />
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Graph nodes">
          {nodes.length === 0 ? (
            <p className="text-sm text-slate-500">Ingest a path to see symbols.</p>
          ) : (
            <ul className="space-y-1 text-sm max-h-80 overflow-auto">
              {nodes.map((n: any) => (
                <li key={n.id} className="font-mono text-slate-700">
                  <span className="text-teal-700">{n.kind}</span> {n.name}
                  <span className="text-slate-400"> — {n.path}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>
        <Panel title="Query + RAG">
          <p className="text-xs uppercase text-slate-500 mb-2">Graph hits</p>
          <ul className="space-y-1 text-sm mb-4 max-h-36 overflow-auto">
            {(Array.isArray(hits) ? hits : []).slice(0, 20).map((h: any, i: number) => (
              <li key={i} className="font-mono text-slate-700">
                {h.name || h.path || JSON.stringify(h).slice(0, 80)}
              </li>
            ))}
          </ul>
          <p className="text-xs uppercase text-slate-500 mb-2">RAG citations</p>
          <ul className="space-y-2 text-sm max-h-40 overflow-auto">
            {(Array.isArray(rag) ? rag : []).slice(0, 12).map((h: any, i: number) => (
              <li key={i} className="rounded border border-slate-200 p-2">
                <div className="font-mono text-xs text-teal-800">{h.path || h.file_path || "chunk"}</div>
                <div className="text-slate-600 line-clamp-3">{h.content || h.text || ""}</div>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="text-2xl font-semibold text-slate-900">{value}</p>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <h2 className="font-semibold text-slate-900 mb-3">{title}</h2>
      {children}
    </div>
  );
}
