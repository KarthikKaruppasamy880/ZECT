import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { Maximize2, Minimize2 } from "lucide-react";

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

type SimNode = GraphNode & {
  x: number;
  y: number;
  vx: number;
  vy: number;
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

export default function LatticeForceGraph({
  nodes,
  edges,
  width = 720,
  height = 420,
  selectedId = null,
  onSelect,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const simRef = useRef<SimNode[]>([]);
  const [selected, setSelected] = useState<string | null>(selectedId);
  const [search, setSearch] = useState("");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [size, setSize] = useState({ width, height });
  const dragRef = useRef<{ id: string; ox: number; oy: number } | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const { width: canvasWidth, height: canvasHeight } = size;

  useEffect(() => {
    setSelected(selectedId);
  }, [selectedId]);

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

  // Fill the container when fullscreen; otherwise use the configured/default size.
  useEffect(() => {
    if (!isFullscreen) {
      setSize({ width, height });
      return;
    }
    const el = containerRef.current;
    if (!el) return;
    const update = () => setSize({ width: el.clientWidth, height: el.clientHeight });
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, [isFullscreen, width, height]);

  const legendKinds = useMemo(
    () => [...new Set(nodes.map((n) => n.kind || "default"))].filter((k) => KIND_COLORS[k]),
    [nodes],
  );

  const emitSelect = useCallback((id: string | null) => {
    setSelected(id);
    if (!id) {
      onSelectRef.current?.(null, 0);
      return;
    }
    const node = simRef.current.find((n) => n.id === id) || nodes.find((n) => n.id === id) || null;
    let neighborCount = 0;
    if (node) {
      const seen = new Set<string>();
      for (const e of edges) {
        if (e.source === id) seen.add(e.target);
        if (e.target === id) seen.add(e.source);
      }
      neighborCount = seen.size;
      onSelectRef.current?.(node, neighborCount);
    } else {
      onSelectRef.current?.(null, 0);
    }
  }, [edges, nodes]);

  useEffect(() => {
    const cx = canvasWidth / 2;
    const cy = canvasHeight / 2;
    simRef.current = nodes.slice(0, 180).map((n, i) => ({
      ...n,
      x: cx + Math.cos(i) * 120 + (Math.random() - 0.5) * 40,
      y: cy + Math.sin(i) * 120 + (Math.random() - 0.5) * 40,
      vx: 0,
      vy: 0,
    }));
  }, [nodes, canvasWidth, canvasHeight]);

  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const sim = simRef.current;
      for (let i = 0; i < sim.length; i++) {
        for (let j = i + 1; j < sim.length; j++) {
          const dx = sim[j].x - sim[i].x;
          const dy = sim[j].y - sim[i].y;
          const dist = Math.max(8, Math.hypot(dx, dy));
          const rep = 800 / (dist * dist);
          sim[i].vx -= (dx / dist) * rep;
          sim[i].vy -= (dy / dist) * rep;
          sim[j].vx += (dx / dist) * rep;
          sim[j].vy += (dy / dist) * rep;
        }
      }
      for (const e of edges) {
        const a = sim.find((n) => n.id === e.source);
        const b = sim.find((n) => n.id === e.target);
        if (!a || !b) continue;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.max(1, Math.hypot(dx, dy));
        const pull = (dist - 90) * 0.004;
        a.vx += (dx / dist) * pull;
        a.vy += (dy / dist) * pull;
        b.vx -= (dx / dist) * pull;
        b.vy -= (dy / dist) * pull;
      }
      for (const n of sim) {
        n.vx += (canvasWidth / 2 - n.x) * 0.0008;
        n.vy += (canvasHeight / 2 - n.y) * 0.0008;
        n.vx *= 0.86;
        n.vy *= 0.86;
        n.x += n.vx;
        n.y += n.vy;
      }
      const canvas = canvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext("2d");
        if (ctx) {
          ctx.clearRect(0, 0, canvasWidth, canvasHeight);
          ctx.fillStyle = "#0f172a";
          ctx.fillRect(0, 0, canvasWidth, canvasHeight);
          const sel = selected;
          const neighborIds = new Set<string>();
          if (sel) {
            neighborIds.add(sel);
            for (const e of edges) {
              if (e.source === sel) neighborIds.add(e.target);
              if (e.target === sel) neighborIds.add(e.source);
            }
          }
          for (const e of edges) {
            const a = sim.find((n) => n.id === e.source);
            const b = sim.find((n) => n.id === e.target);
            if (!a || !b) continue;
            const dim = sel && !neighborIds.has(a.id) && !neighborIds.has(b.id);
            ctx.strokeStyle = dim ? "rgba(51,65,85,0.25)" : "rgba(45,212,191,0.35)";
            ctx.lineWidth = dim ? 0.5 : 1;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
          for (const n of sim) {
            const dim = sel && !neighborIds.has(n.id);
            const r = n.kind === "vault" ? 10 : n.kind === "folder" ? 7 : 5;
            ctx.beginPath();
            ctx.fillStyle = dim ? "rgba(71,85,105,0.5)" : KIND_COLORS[n.kind || "default"] || KIND_COLORS.default;
            ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
            ctx.fill();
            if (n.id === sel) {
              ctx.strokeStyle = "#fbbf24";
              ctx.lineWidth = 2;
              ctx.stroke();
              const label = (n.name || n.id || "").slice(0, 40);
              if (label) {
                ctx.font = "11px ui-sans-serif, system-ui, sans-serif";
                ctx.fillStyle = "#fef3c7";
                ctx.fillText(label, n.x + r + 4, n.y + 4);
              }
            }
          }
        }
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [edges, selected, canvasWidth, canvasHeight]);

  const pickNode = useCallback(
    (clientX: number, clientY: number) => {
      const canvas = canvasRef.current;
      if (!canvas) return null;
      const rect = canvas.getBoundingClientRect();
      const x = clientX - rect.left;
      const y = clientY - rect.top;
      let best: SimNode | null = null;
      let bestD = 999;
      for (const n of simRef.current) {
        const d = Math.hypot(n.x - x, n.y - y);
        if (d < 14 && d < bestD) {
          best = n;
          bestD = d;
        }
      }
      return best;
    },
    [],
  );

  const flyToSearch = () => {
    const q = search.trim().toLowerCase();
    if (!q) return;
    const hit = simRef.current.find(
      (n) =>
        (n.name || "").toLowerCase().includes(q) ||
        (n.path || "").toLowerCase().includes(q) ||
        (n.id || "").toLowerCase().includes(q),
    );
    if (hit) {
      emitSelect(hit.id);
      hit.x = canvasWidth / 2;
      hit.y = canvasHeight / 2;
      hit.vx = 0;
      hit.vy = 0;
    }
  };

  return (
    <div ref={containerRef} className={isFullscreen ? "space-y-2 bg-slate-950 p-3" : "space-y-2"} data-testid="lattice-force-graph">
      <div className="flex gap-2">
        <input
          data-testid="lattice-graph-search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && flyToSearch()}
          placeholder="Search node…"
          className="flex-1 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-white"
        />
        <button
          type="button"
          className="rounded bg-teal-700 px-2 py-1 text-xs text-white"
          onClick={flyToSearch}
        >
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
      <canvas
        ref={canvasRef}
        width={canvasWidth}
        height={canvasHeight}
        style={isFullscreen ? { width: canvasWidth, height: canvasHeight } : undefined}
        className={
          isFullscreen
            ? "rounded-lg border border-slate-700 cursor-grab active:cursor-grabbing"
            : "w-full rounded-lg border border-slate-700 cursor-grab active:cursor-grabbing"
        }
        onMouseDown={(e) => {
          const n = pickNode(e.clientX, e.clientY);
          if (n) {
            emitSelect(n.id);
            dragRef.current = { id: n.id, ox: e.clientX, oy: e.clientY };
          }
        }}
        onMouseMove={(e) => {
          if (!dragRef.current) return;
          const n = simRef.current.find((x) => x.id === dragRef.current!.id);
          if (!n) return;
          n.x += e.movementX;
          n.y += e.movementY;
        }}
        onMouseUp={() => {
          dragRef.current = null;
        }}
      />
      <p className="text-xs text-slate-400">
        Click a node to select and open details. Drag to rearrange. Fly to search by name/path.
      </p>
      {legendKinds.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 border-t border-slate-800 pt-2" data-testid="lattice-graph-legend">
          {legendKinds.map((kind) => (
            <span key={kind} className="flex items-center gap-1.5 text-[11px] text-slate-400">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: KIND_COLORS[kind] }}
              />
              {kind}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
