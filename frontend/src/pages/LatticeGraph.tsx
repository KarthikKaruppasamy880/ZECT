import { useState, useEffect, useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { Network, Search, Upload } from "lucide-react";
import {
  latticeBlueprint,
  latticeExplain,
  latticeGraph,
  latticeIngest,
  latticeNeighbors,
  latticePath,
  latticeQuery,
  latticeRagSearch,
} from "@/lib/api";
import { useWorkspaceRepoContext } from "@/hooks/useWorkspaceRepoContext";
import { readMentrixWorkspace } from "@/lib/workspaceContext";
import LatticeGraphCanvas, { KIND_COLORS, type GraphNode } from "@/components/LatticeGraphCanvas";

export default function LatticeGraph() {
  const [searchParams] = useSearchParams();
  const { latticeStatus: idxStatus, projectKey: wsKey } = useWorkspaceRepoContext();
  const [path, setPath] = useState("");
  const [projectKey, setProjectKey] = useState("");
  const [layer, setLayer] = useState<"combined" | "code" | "docs">(
    (searchParams.get("layer") as "combined" | "code" | "docs") || "combined",
  );
  const [query, setQuery] = useState("");
  const [pathSource, setPathSource] = useState("");
  const [pathTarget, setPathTarget] = useState("");
  const [explainNode, setExplainNode] = useState("");
  const [graph, setGraph] = useState<any>(null);
  const [blueprint, setBlueprint] = useState<any>(null);
  const [hits, setHits] = useState<any[]>([]);
  const [rag, setRag] = useState<any[]>([]);
  const [pathResult, setPathResult] = useState<any>(null);
  const [explainResult, setExplainResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [neighborCount, setNeighborCount] = useState(0);

  const key = projectKey || path;

  const loadBlueprint = async (pk: string) => {
    try {
      setBlueprint(await latticeBlueprint(pk));
    } catch {
      setBlueprint(null);
    }
  };

  const ingest = async () => {
    setError("");
    setLoading(true);
    try {
      const res = await latticeIngest(path, key, true);
      setGraph(res.graph);
      const pk = res.graph?.project_key || key;
      setProjectKey(pk);
      if (path.trim()) {
        localStorage.setItem(
          "zect_mentrix_workspace",
          JSON.stringify({
            path: path.trim(),
            workspace: path.trim(),
            project_key: pk,
            projectKey: pk,
          }),
        );
        localStorage.setItem("zect_lattice_key", pk);
      }
      if (res.blueprint && !res.blueprint.error) {
        setBlueprint({ stats: res.blueprint.stats, tech_stack: res.blueprint.tech_stack, ...res.blueprint });
      }
      await loadBlueprint(pk);
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
      const res = await latticeGraph(key, layer);
      setGraph(res);
      await loadBlueprint(key);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Load failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const l = searchParams.get("layer");
    if (l === "code" || l === "docs" || l === "combined") setLayer(l);
  }, [searchParams]);

  useEffect(() => {
    const ws = readMentrixWorkspace();
    const pk = ws?.projectKey || localStorage.getItem("zect_lattice_key") || "";
    if (pk && !projectKey) setProjectKey(pk);
    if (ws?.path && !path) setPath(ws.path);
  }, []);

  useEffect(() => {
    const pk = projectKey || wsKey;
    if (!pk || graph) return;
    void (async () => {
      try {
        const res = await latticeGraph(pk, layer);
        setGraph(res);
        await loadBlueprint(pk);
      } catch {
        /* not indexed yet — user can ingest manually */
      }
    })();
  }, [projectKey, wsKey, layer]);

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

  const runPath = async () => {
    setError("");
    setLoading(true);
    try {
      const res = await latticePath(key, pathSource, pathTarget);
      setPathResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Path failed");
    } finally {
      setLoading(false);
    }
  };

  const runExplain = useCallback(
    async (nodeOverride?: string) => {
      setError("");
      setLoading(true);
      try {
        const nodeArg = nodeOverride || explainNode || pathSource || query;
        if (pathSource && pathTarget && !nodeOverride) {
          setExplainResult(await latticeExplain(key, { source: pathSource, target: pathTarget }));
        } else {
          const node = nodeArg;
          const [exp, nb] = await Promise.all([
            latticeExplain(key, { node }),
            latticeNeighbors(key, node),
          ]);
          setExplainResult({ ...exp, neighbors: nb });
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Explain failed");
      } finally {
        setLoading(false);
      }
    },
    [explainNode, key, pathSource, pathTarget, query],
  );

  const onGraphSelect = useCallback(
    (node: GraphNode | null, neighbors: number) => {
      setSelectedNode(node);
      setNeighborCount(neighbors);
      if (!node) return;
      const label = node.name || node.id;
      setExplainNode(label);
      setPathSource(label);
      if (key) void runExplain(label);
    },
    [key, runExplain],
  );

  const nodeConnections = useMemo(() => {
    if (!selectedNode) return [];
    const byId = new Map((graph?.nodes || []).map((n: any) => [n.id, n]));
    const rows: { id: string; name: string; kind: string; relation: string }[] = [];
    for (const e of graph?.edges || []) {
      let otherId: string | null = null;
      if (e.source === selectedNode.id) otherId = e.target;
      else if (e.target === selectedNode.id) otherId = e.source;
      if (!otherId) continue;
      const other = byId.get(otherId) as { name?: string; kind?: string } | undefined;
      rows.push({
        id: otherId,
        name: other?.name || otherId,
        kind: other?.kind || "unknown",
        relation: e.kind || "related",
      });
    }
    return rows.slice(0, 40);
  }, [selectedNode, graph]);

  const nodes = graph?.nodes?.slice(0, 80) || [];
  const edges = graph?.edges || [];
  const edgePreview = edges.slice(0, 120);
  const endpoints = (graph?.nodes || []).filter((n: any) => n.kind === "endpoint").length;
  const docNodes = (graph?.nodes || []).filter((n: any) =>
    ["doc", "folder", "vault", "wikilink_stub"].includes(n.kind),
  ).length;
  const wikilinks = edges.filter((e: any) =>
    ["wikilink", "md_link", "references"].includes(e.kind),
  ).length;

  return (
    <div className="max-w-6xl mx-auto space-y-6 p-1 zect-page" data-testid="lattice-page">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-slate-800 border border-slate-700">
          <Network className="h-6 w-6 text-teal-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Lattice</h1>
          <p className="text-sm text-slate-600" data-testid="lattice-graphify-copy">
            Graphify = Lattice ingest. Mentrix code intelligence — symbols, imports, calls, path/explain
            + RAG (ZECT-native Lattice, not a second knowledge base).
          </p>
          <p className="text-xs text-slate-500 mt-2 max-w-3xl">
            <strong>Ingest + RAG</strong> indexes a path; <strong>Load graph</strong> reloads an
            existing key; <strong>layers</strong> switch code/docs/combined; <strong>Query</strong>{" "}
            searches symbols + RAG; click the graph for the inspector + Explain; use{" "}
            <strong>Path / Explain</strong> for A→B routes. Prefer Lattice for relationships; use{" "}
            <strong>Code Index</strong> for flat symbol lookup.
          </p>
          {(projectKey || wsKey) && (
            <p className="text-xs mt-1" data-testid="lattice-index-badge">
              <span className="zect-chip bg-slate-100 text-slate-800 mr-2">
                {idxStatus?.state || (idxStatus?.indexed ? "READY" : "NOT_INDEXED")}
              </span>
              {idxStatus?.indexed ? (
                <span className="text-teal-700">
                  Graph loaded for {projectKey || wsKey}
                  {idxStatus.action_label ? ` · ${idxStatus.action_label}` : ""}
                </span>
              ) : (
                <span className="text-amber-700">
                  {idxStatus?.action_label || `Key ${projectKey || wsKey} — ingest or Load graph`}
                </span>
              )}
            </p>
          )}
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

      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-sm text-slate-600">Layer:</span>
        {(["combined", "code", "docs"] as const).map((l) => (
          <button
            key={l}
            type="button"
            data-testid={`lattice-layer-${l}`}
            onClick={() => {
              setLayer(l);
              if (key) void latticeGraph(key, l).then(setGraph).catch(() => {});
            }}
            className={`rounded-lg px-3 py-1 text-sm capitalize ${
              layer === l ? "bg-teal-700 text-white" : "border border-slate-300"
            }`}
          >
            {l}
          </button>
        ))}
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
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert" data-testid="lattice-error">
          {error}
        </div>
      )}

      {graph && (
        <div className="grid gap-4 md:grid-cols-7">
          <Stat label="Files" value={graph.files_indexed ?? "—"} />
          <Stat label="Docs" value={graph.doc_files_indexed ?? docNodes ?? "—"} />
          <Stat label="Wikilinks" value={graph.wikilinks_resolved ?? wikilinks ?? "—"} />
          <Stat label="Broken" value={graph.wikilinks_unresolved ?? "—"} />
          <Stat label="Symbols" value={graph.symbols ?? nodes.length} />
          <Stat label="Edges" value={edges.length} />
          <Stat label="Endpoints" value={endpoints} />
        </div>
      )}

      {graph && nodes.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-slate-900 p-3 space-y-3">
          <h2 className="mb-2 text-sm font-semibold text-teal-200">Interactive graph</h2>
          <LatticeGraphCanvas
            nodes={graph.nodes || []}
            edges={edges}
            selectedId={selectedNode?.id ?? null}
            onSelect={onGraphSelect}
          />
          {selectedNode && (
            <div
              data-testid="lattice-node-inspector"
              className="rounded-lg border border-teal-800/60 bg-slate-950/90 p-3 text-sm text-slate-200 space-y-2"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="font-semibold text-teal-200">Node details</h3>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    data-testid="lattice-inspector-explain"
                    className="rounded bg-teal-700 px-2 py-1 text-xs text-white"
                    onClick={() => void runExplain(selectedNode.name || selectedNode.id)}
                    disabled={!key || loading}
                  >
                    Explain
                  </button>
                  <button
                    type="button"
                    data-testid="lattice-inspector-copy"
                    className="rounded border border-slate-600 px-2 py-1 text-xs"
                    onClick={() => {
                      void navigator.clipboard.writeText(selectedNode.id);
                    }}
                  >
                    Copy id
                  </button>
                </div>
              </div>
              <dl className="grid gap-1 text-xs sm:grid-cols-2">
                <div>
                  <dt className="text-slate-500">Name</dt>
                  <dd className="font-mono text-amber-100">{selectedNode.name || "—"}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Kind</dt>
                  <dd>{selectedNode.kind || "—"}</dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="text-slate-500">Path</dt>
                  <dd className="font-mono break-all text-slate-300">{selectedNode.path || "—"}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Id</dt>
                  <dd className="font-mono break-all text-slate-400">{selectedNode.id}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Neighbors</dt>
                  <dd>{neighborCount}</dd>
                </div>
              </dl>
              {explainResult?.summary && (
                <p className="text-xs text-slate-300 border-t border-slate-800 pt-2" data-testid="lattice-inspector-summary">
                  {explainResult.summary}
                </p>
              )}
              <div className="border-t border-slate-800 pt-2" data-testid="lattice-inspector-connections">
                <p className="text-slate-500 text-xs mb-1">Connections ({nodeConnections.length})</p>
                {nodeConnections.length === 0 ? (
                  <p className="text-xs text-slate-500">No connections in the loaded graph — try Explain for API/file/mention context.</p>
                ) : (
                  <ul className="space-y-1 max-h-40 overflow-auto text-xs">
                    {nodeConnections.map((c, i) => (
                      <li key={`${c.id}-${i}`} className="flex items-center justify-between gap-2">
                        <span className="flex items-center gap-1.5 min-w-0">
                          <span
                            className="inline-block h-2 w-2 rounded-full shrink-0"
                            style={{ backgroundColor: KIND_COLORS[c.kind] || KIND_COLORS.default }}
                          />
                          <span className="truncate font-mono text-slate-200">{c.name}</span>
                          <span className="text-slate-500 shrink-0">({c.kind})</span>
                        </span>
                        <span className="text-teal-400 shrink-0">{c.relation}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {(blueprint || graph?.god_nodes) && (
        <div
          className="rounded-xl border border-teal-200 bg-teal-50/40 p-4 space-y-3"
          data-testid="lattice-blueprint-stats"
        >
          <h2 className="font-semibold text-slate-900">Structural blueprint</h2>
          <div className="grid gap-3 md:grid-cols-4 text-sm">
            <Stat
              label="Tech stack"
              value={(blueprint?.tech_stack || []).slice(0, 4).join(", ") || "—"}
            />
            <Stat
              label="Functions"
              value={blueprint?.stats?.functions ?? blueprint?.functions?.length ?? "—"}
            />
            <Stat
              label="API endpoints"
              value={
                blueprint?.stats?.api_endpoints ??
                blueprint?.api_endpoints?.length ??
                endpoints
              }
            />
            <Stat
              label="God nodes"
              value={(graph?.god_nodes || blueprint?.god_nodes || []).length || "—"}
            />
          </div>
          {(graph?.god_nodes || blueprint?.god_nodes)?.length > 0 && (
            <ul className="text-xs text-slate-600 space-y-1 max-h-28 overflow-auto">
              {(graph?.god_nodes || blueprint?.god_nodes || []).slice(0, 8).map((n: any, i: number) => (
                <li key={i}>
                  {n.kind} <code className="font-mono">{n.name}</code> (degree={n.degree})
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div
        className="rounded-xl border border-slate-200 bg-white p-4 space-y-3"
        data-testid="lattice-path-explain"
      >
        <h2 className="font-semibold text-slate-900">Path / Explain</h2>
        <div className="grid gap-2 md:grid-cols-3">
          <input
            data-testid="lattice-path-source"
            value={pathSource}
            onChange={(e) => setPathSource(e.target.value)}
            placeholder="Source symbol or file"
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
          <input
            data-testid="lattice-path-target"
            value={pathTarget}
            onChange={(e) => setPathTarget(e.target.value)}
            placeholder="Target symbol or file"
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
          <input
            data-testid="lattice-explain-node"
            value={explainNode}
            onChange={(e) => setExplainNode(e.target.value)}
            placeholder="Or single node to explain"
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            data-testid="lattice-run-path"
            onClick={runPath}
            disabled={!key || !pathSource || !pathTarget || loading}
            className="rounded-lg bg-teal-700 px-3 py-1.5 text-sm text-white disabled:opacity-50"
          >
            Find path
          </button>
          <button
            data-testid="lattice-run-explain"
            onClick={() => void runExplain()}
            disabled={!key || loading || (!explainNode && !pathSource && !query)}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm disabled:opacity-50"
          >
            Explain
          </button>
        </div>
        {pathResult && (
          <pre className="text-xs bg-slate-50 border border-slate-100 rounded p-2 overflow-auto max-h-40">
            {JSON.stringify(pathResult, null, 2)}
          </pre>
        )}
        {explainResult && (
          <p className="text-sm text-slate-700" data-testid="lattice-explain-summary">
            {explainResult.summary}
          </p>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Graph nodes">
          {nodes.length === 0 ? (
            <p className="text-sm text-slate-500">Ingest a path to see symbols.</p>
          ) : (
            <ul className="space-y-1 text-sm max-h-80 overflow-auto">
              {nodes.map((n: any) => (
                <li key={n.id}>
                  <button
                    type="button"
                    className={`w-full text-left font-mono rounded px-1 py-0.5 hover:bg-slate-100 ${
                      selectedNode?.id === n.id ? "bg-teal-50 text-teal-900" : "text-slate-700"
                    }`}
                    onClick={() => onGraphSelect(n, 0)}
                  >
                    <span className="text-teal-700">{n.kind}</span> {n.name}
                    <span className="text-slate-400"> — {n.path}</span>
                  </button>
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
          <p className="text-xs uppercase text-slate-500 mt-3 mb-1">Edge sample</p>
          <ul className="text-xs font-mono text-slate-600 max-h-24 overflow-auto">
            {edgePreview.slice(0, 30).map((e: any, i: number) => (
              <li key={i}>
                {e.kind}: {e.source?.slice?.(0, 8)} → {e.target?.slice?.(0, 8)}
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  const long = typeof value === "string" && value.length > 18;
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`${long ? "text-sm font-semibold" : "text-2xl font-semibold"} text-slate-900 break-words`}>
        {value}
      </p>
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
