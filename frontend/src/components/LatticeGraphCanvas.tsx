import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import cytoscape from "cytoscape";
import coseBilkent from "cytoscape-cose-bilkent";
import { Maximize2, Minimize2 } from "lucide-react";

cytoscape.use(coseBilkent);

export type GraphNode = {
  id: string;
  name?: string;
  kind?: string;
  path?: string;
  group?: string;
};

type GraphEdge = {
  source: string;
  target: string;
  kind?: string;
};

export const KIND_COLORS: Record<string, string> = {
  doc: "#34d399",
  folder: "#60a5fa",
  vault: "#a78bfa",
  wikilink_stub: "#64748b",
  file: "#94a3b8",
  class: "#fbbf24",
  function: "#f472b6",
  endpoint: "#fb923c",
  default: "#475569",
};

type Props = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  width?: number;
  height?: number;
  /** Controlled selection id (optional). */
  selectedId?: string | null;
  onSelect?: (node: GraphNode | null, neighborCount: number) => void;
};

// cose-bilkent is a real force-directed layout (vs. the previous hand-rolled
// repulsion/spring simulation) — applied once per data change, not every
// animation frame, since react-cytoscapejs only runs `layout` on mount.
const LAYOUT = {
  name: "cose-bilkent",
  quality: "default",
  animate: false,
  fit: true,
  padding: 30,
  nodeRepulsion: 9000,
  idealEdgeLength: 90,
  gravity: 0.3,
  numIter: 2500,
  tile: true,
};

const STYLESHEET: cytoscape.Stylesheet[] = [
  {
    selector: "node",
    style: {
      "background-color": "data(color)",
      label: "data(label)",
      color: "#e2e8f0",
      "font-size": 10,
      "text-valign": "bottom",
      "text-margin-y": 4,
      width: "data(size)",
      height: "data(size)",
      "border-width": 0,
    },
  },
  { selector: "node:selected", style: { "border-width": 2, "border-color": "#fbbf24" } },
  { selector: "node.highlighted", style: { "border-width": 2, "border-color": "#fbbf24" } },
  { selector: "node.dim", style: { opacity: 0.2 } },
  {
    selector: "edge",
    style: {
      width: 1,
      "line-color": "rgba(45,212,191,0.35)",
      "curve-style": "haystack",
      "target-arrow-shape": "none",
    },
  },
  { selector: "edge.dim", style: { opacity: 0.1 } },
  { selector: "edge.highlighted", style: { "line-color": "#2dd4bf", width: 1.5 } },
];

export default function LatticeGraphCanvas({
  nodes,
  edges,
  height = 420,
  selectedId = null,
  onSelect,
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [search, setSearch] = useState("");
  const [isFullscreen, setIsFullscreen] = useState(false);

  const elements = useMemo(() => {
    const capped = nodes.slice(0, 400);
    const nodeIds = new Set(capped.map((n) => n.id));
    const els: Record<string, unknown>[] = capped.map((n) => ({
      data: {
        id: n.id,
        label: (n.name || n.id).slice(0, 30),
        color: KIND_COLORS[n.kind || "default"] || KIND_COLORS.default,
        size: n.kind === "vault" ? 26 : n.kind === "folder" ? 20 : 14,
      },
    }));
    let i = 0;
    for (const e of edges) {
      if (!nodeIds.has(e.source) || !nodeIds.has(e.target)) continue;
      els.push({ data: { id: `e${i++}`, source: e.source, target: e.target } });
    }
    return els;
  }, [nodes, edges]);

  const legendKinds = useMemo(
    () => [...new Set(nodes.map((n) => n.kind || "default"))].filter((k) => KIND_COLORS[k]),
    [nodes],
  );

  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const nodesRef = useRef(nodes);
  nodesRef.current = nodes;

  /** Visual-only — highlight a node's neighborhood and dim the rest. Does
   * not call onSelect; used both by real user interaction (via emitSelect)
   * and by syncing an externally-controlled selectedId. */
  const applyHighlight = useCallback((id: string | null) => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().removeClass("highlighted").removeClass("dim");
    if (!id) return;
    const node = cy.getElementById(id);
    if (node.empty()) return;
    const neighborhood = node.closedNeighborhood();
    cy.elements().difference(neighborhood).addClass("dim");
    neighborhood.addClass("highlighted");
  }, []);

  const emitSelect = useCallback(
    (id: string | null) => {
      applyHighlight(id);
      if (!id) {
        onSelectRef.current?.(null, 0);
        return;
      }
      const cy = cyRef.current;
      const node = cy?.getElementById(id);
      const neighborCount = node && !node.empty() ? node.closedNeighborhood().nodes().size() - 1 : 0;
      const orig = nodesRef.current.find((n) => n.id === id) || null;
      onSelectRef.current?.(orig, neighborCount);
    },
    [applyHighlight],
  );

  useEffect(() => {
    applyHighlight(selectedId);
  }, [selectedId, applyHighlight]);

  useEffect(() => {
    const onChange = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  }, []);

  // Re-fit (not a full re-layout) whenever the container is resized, e.g.
  // entering/exiting fullscreen.
  useEffect(() => {
    const cy = cyRef.current;
    const el = containerRef.current;
    if (!cy || !el) return;
    const refit = () => {
      cy.resize();
      cy.fit(undefined, 30);
    };
    const observer = new ResizeObserver(refit);
    observer.observe(el);
    return () => observer.disconnect();
  }, [isFullscreen]);

  // react-cytoscapejs only runs `layout` once, on mount — re-run it
  // explicitly whenever the actual graph data changes.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.layout(LAYOUT).run();
  }, [elements]);

  const handleCyInit = useCallback(
    (cy: cytoscape.Core) => {
      if (cyRef.current === cy) return;
      cyRef.current = cy;
      cy.on("tap", "node", (evt) => emitSelect(String(evt.target.id())));
      cy.on("tap", (evt) => {
        if (evt.target === cy) emitSelect(null);
      });
    },
    [emitSelect],
  );

  const flyToSearch = () => {
    const q = search.trim().toLowerCase();
    if (!q) return;
    const hit = nodes.find(
      (n) =>
        (n.name || "").toLowerCase().includes(q) ||
        (n.path || "").toLowerCase().includes(q) ||
        (n.id || "").toLowerCase().includes(q),
    );
    if (!hit) return;
    emitSelect(hit.id);
    const cy = cyRef.current;
    const el = cy?.getElementById(hit.id);
    if (cy && el && !el.empty()) {
      cy.animate({ center: { eles: el }, zoom: Math.max(cy.zoom(), 1) }, { duration: 300 });
    }
  };

  return (
    <div
      ref={containerRef}
      className={isFullscreen ? "space-y-2 bg-slate-950 p-3" : "space-y-2"}
      data-testid="lattice-force-graph"
    >
      <div className="flex gap-2">
        <input
          data-testid="lattice-graph-search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && flyToSearch()}
          placeholder="Search node…"
          className="flex-1 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-white"
        />
        <button type="button" className="rounded bg-teal-700 px-2 py-1 text-xs text-white" onClick={flyToSearch}>
          Fly to
        </button>
        <button
          type="button"
          className="rounded border border-slate-600 px-2 py-1 text-xs"
          onClick={() => emitSelect(null)}
        >
          Reset
        </button>
        <button
          type="button"
          data-testid="lattice-graph-fullscreen"
          className="ml-auto flex items-center gap-1 rounded border border-slate-600 px-2 py-1 text-xs text-slate-200 hover:bg-slate-800"
          onClick={toggleFullscreen}
          title={isFullscreen ? "Exit fullscreen" : "Maximize graph"}
        >
          {isFullscreen ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
          {isFullscreen ? "Exit" : "Maximize"}
        </button>
      </div>
      <CytoscapeComponent
        elements={elements}
        layout={LAYOUT}
        stylesheet={STYLESHEET}
        style={{ width: "100%", height: isFullscreen ? "calc(100vh - 160px)" : height }}
        className="rounded-lg border border-slate-700"
        cy={handleCyInit}
      />
      <p className="text-xs text-slate-400">
        Click a node to select and highlight its neighborhood. Drag to rearrange. Fly to search by name/path.
      </p>
      {legendKinds.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 border-t border-slate-800 pt-2" data-testid="lattice-graph-legend">
          {legendKinds.map((kind) => (
            <span key={kind} className="flex items-center gap-1.5 text-[11px] text-slate-400">
              <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: KIND_COLORS[kind] }} />
              {kind}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
