/**
 * Mentrix Artifacts host — markdown, mermaid, table, chart, note, image, progress, record.
 */
import { useEffect, useId, useRef } from "react";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { mentrixMediaUrl } from "@/lib/api";

export type ArtifactItem = {
  type?: string;
  title?: string;
  body?: string;
  data?: Record<string, unknown>;
};

type Props = {
  items: ArtifactItem[];
  displayMode?: boolean;
};

function MermaidBlock({ body }: { body: string }) {
  const id = useId().replace(/:/g, "");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({ startOnLoad: false, theme: "dark", securityLevel: "loose" });
        const { svg } = await mermaid.render(`mmd-${id}-${Date.now()}`, body || "flowchart LR\n  a[Mentrix]");
        if (!cancelled && ref.current) ref.current.innerHTML = svg;
      } catch (e) {
        if (!cancelled && ref.current) {
          ref.current.innerHTML = `<pre class="text-xs text-amber-200 whitespace-pre-wrap">${String(body || e)}</pre>`;
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [body, id]);

  return <div ref={ref} className="overflow-auto rounded-lg bg-slate-950/80 p-3" />;
}

function TableBlock({ data }: { data?: Record<string, unknown> }) {
  const columns = (data?.columns as string[]) || [];
  const rows = (data?.rows as unknown[][]) || [];
  if (!columns.length) return <p className="text-xs text-slate-400">Empty table</p>;
  return (
    <div className="overflow-auto">
      <table className="w-full text-left text-xs text-slate-200">
        <thead>
          <tr className="border-b border-slate-700 text-teal-300">
            {columns.map((c) => (
              <th key={c} className="px-2 py-1 font-medium">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-slate-800/80">
              {row.map((cell, j) => (
                <td key={j} className="px-2 py-1 align-top">
                  {String(cell ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ChartBlock({ data }: { data?: Record<string, unknown> }) {
  const series = (data?.series as { name: string; value: number }[]) || [
    { name: "A", value: 40 },
    { name: "B", value: 65 },
    { name: "C", value: 30 },
  ];
  // Fixed pixel height (not % alone) avoids Recharts ResponsiveContainer / YAxis defaultProps warnings
  return (
    <div className="w-full" style={{ width: "100%", minHeight: 160, height: 160 }}>
      <ResponsiveContainer width="100%" height={160} minHeight={160}>
        <BarChart data={series} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <XAxis dataKey="name" stroke="#94a3b8" fontSize={10} />
          <YAxis stroke="#94a3b8" fontSize={10} width={32} allowDecimals={false} />
          <Tooltip />
          <Bar dataKey="value" fill="#14b8a6" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function ProgressBlock({ data }: { data?: Record<string, unknown> }) {
  const percent = Number(data?.percent ?? 0);
  return (
    <div className="space-y-2 text-xs text-slate-300">
      <div className="flex justify-between">
        <span>{String(data?.status || "running")}</span>
        <span>{percent}%</span>
      </div>
      <div className="h-2 rounded-full bg-slate-800">
        <div className="h-2 rounded-full bg-teal-500 transition-all" style={{ width: `${Math.min(100, percent)}%` }} />
      </div>
      {data?.next_step ? <p className="text-slate-400">Next: {String(data.next_step)}</p> : null}
    </div>
  );
}

function RecordBlock({ data }: { data?: Record<string, unknown> }) {
  const records = (data?.records as { id?: string; text?: string; tags?: string[]; createdAt?: string }[]) || [];
  if (!records.length) return <p className="text-xs text-slate-400">No records</p>;
  return (
    <ul className="space-y-2 text-xs">
      {records.map((r) => (
        <li key={r.id || r.createdAt} className="rounded border border-slate-700 bg-slate-900/60 px-2 py-1.5">
          <div className="text-slate-100">{r.text}</div>
          <div className="mt-1 text-[10px] text-slate-500">
            {(r.tags || []).join(", ")} · {r.createdAt || ""}
          </div>
        </li>
      ))}
    </ul>
  );
}

export default function MentrixArtifacts({ items, displayMode }: Props) {
  return (
    <div
      className={`space-y-3 overflow-auto ${displayMode ? "max-h-[calc(100vh-8rem)]" : "max-h-[520px]"}`}
      data-testid="mentrix-board"
    >
      {!items.length && (
        <p className="text-sm text-slate-400" data-testid="mentrix-board-empty">
          Artifacts appear here — briefs, Mermaid workflows, notes, research, Delivery progress.
        </p>
      )}
      {items.map((item, i) => (
        <article
          key={`${item.title}-${i}`}
          className="rounded-xl border border-teal-900/50 bg-slate-900/70 p-3 shadow-lg shadow-teal-950/30"
          data-testid={`mentrix-artifact-${item.type || "markdown"}`}
        >
          <h3 className="mb-2 text-sm font-semibold text-teal-200">{item.title || "Artifact"}</h3>
          {item.type === "mermaid" && <MermaidBlock body={item.body || ""} />}
          {item.type === "table" && <TableBlock data={item.data} />}
          {item.type === "chart" && <ChartBlock data={item.data} />}
          {item.type === "progress" && <ProgressBlock data={item.data} />}
          {item.type === "record" && <RecordBlock data={item.data} />}
          {item.type === "note" && (
            <p className="whitespace-pre-wrap text-sm text-slate-200">{item.body}</p>
          )}
          {item.type === "image" && (
            <div className="space-y-2" data-testid="mentrix-image-board-item">
              {typeof item.data?.number === "number" && (
                <p className="text-[10px] uppercase tracking-wider text-teal-500/80">
                  Mentrix Image #{String(item.data.number).padStart(3, "0")}
                </p>
              )}
              {typeof item.data?.number === "number" ? (
                <img
                  src={mentrixMediaUrl(item.data.number as number)}
                  alt={item.title || "Mentrix image"}
                  className="max-h-64 w-full rounded-lg object-contain bg-slate-950"
                />
              ) : null}
              <p className="text-xs text-slate-400">{item.body || ""}</p>
            </div>
          )}
          {(!item.type || item.type === "markdown") && (
            <pre className="whitespace-pre-wrap font-sans text-[11px] text-slate-300">{item.body || ""}</pre>
          )}
        </article>
      ))}
    </div>
  );
}
