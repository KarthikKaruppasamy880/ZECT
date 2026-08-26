import type { PresentBlock } from "@/lib/api";

const SERIES_COLORS = ["#00628B", "#FF7500", "#4CAF50", "#44546A", "#9C27B0"];

type Props = { block: PresentBlock; testId?: string };

export default function PresentChartPreview({ block, testId }: Props) {
  const chartType = String(block.content?.chart_type || "column");
  const cats = (block.content?.categories as string[]) || [];
  const series = (block.content?.series as Array<{ name?: string; values?: number[] }>) || [];
  const values = series[0]?.values || [];
  const title = String(block.content?.title || "");
  const max = Math.max(1, ...values.map((v) => Math.abs(Number(v) || 0)));

  if (!cats.length || !values.length) {
    return (
      <div className="flex h-full flex-col items-center justify-center bg-white/90 p-1" data-testid={testId}>
        <p className="truncate text-[9px] font-medium text-slate-700">{title || "Chart"}</p>
        <p className="text-[8px] text-slate-400">Double-click to edit data</p>
      </div>
    );
  }

  const isPie = chartType === "pie" || chartType === "donut";
  const isLine = chartType === "line" || chartType === "area";
  const isBar = chartType === "bar" || chartType === "stacked_horizontal";

  const w = 100;
  const h = 64;
  const pad = 6;

  return (
    <div className="flex h-full flex-col bg-white/95 p-0.5" data-testid={testId}>
      {title ? <p className="truncate px-1 text-[8px] font-medium text-slate-700">{title}</p> : null}
      <svg viewBox={`0 0 ${w} ${h}`} className="min-h-0 flex-1 w-full" aria-hidden>
        {isPie ? (
          (() => {
            const total = values.reduce((s, v) => s + Math.abs(Number(v) || 0), 0) || 1;
            let angle = -90;
            const cx = w / 2;
            const cy = h / 2 + 4;
            const r = Math.min(w, h) / 2 - pad;
            return values.slice(0, 8).map((v, i) => {
              const slice = (Math.abs(Number(v) || 0) / total) * 360;
              const start = angle;
              angle += slice;
              const x1 = cx + r * Math.cos((Math.PI * start) / 180);
              const y1 = cy + r * Math.sin((Math.PI * start) / 180);
              const x2 = cx + r * Math.cos((Math.PI * angle) / 180);
              const y2 = cy + r * Math.sin((Math.PI * angle) / 180);
              const large = slice > 180 ? 1 : 0;
              return (
                <path
                  key={`${cats[i] || i}`}
                  d={`M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`}
                  fill={SERIES_COLORS[i % SERIES_COLORS.length]}
                />
              );
            });
          })()
        ) : isLine ? (
          (() => {
            const innerW = w - pad * 2;
            const innerH = h - pad * 2;
            const pts = values.slice(0, 8).map((v, i) => {
              const x = pad + (innerW * i) / Math.max(1, values.length - 1);
              const y = pad + innerH - (innerH * Math.abs(Number(v) || 0)) / max;
              return `${x},${y}`;
            });
            return (
              <>
                <polyline points={pts.join(" ")} fill="none" stroke={SERIES_COLORS[0]} strokeWidth="1.5" />
                {pts.map((p, i) => {
                  const [x, y] = p.split(",").map(Number);
                  return <circle key={i} cx={x} cy={y} r="1.5" fill={SERIES_COLORS[0]} />;
                })}
              </>
            );
          })()
        ) : isBar ? (
          values.slice(0, 6).map((v, i) => {
            const barH = ((Math.abs(Number(v) || 0) / max) * (h - pad * 2)) / values.length;
            const y = pad + i * ((h - pad * 2) / values.length);
            const barW = (Math.abs(Number(v) || 0) / max) * (w - pad * 2);
            return (
              <rect
                key={`${cats[i] || i}`}
                x={pad}
                y={y}
                width={barW}
                height={Math.max(2, barH - 1)}
                fill={SERIES_COLORS[i % SERIES_COLORS.length]}
                rx="0.5"
              />
            );
          })
        ) : (
          values.slice(0, 8).map((v, i) => {
            const barW = (w - pad * 2) / values.length - 1;
            const x = pad + i * (barW + 1);
            const barH = (Math.abs(Number(v) || 0) / max) * (h - pad * 2);
            return (
              <rect
                key={`${cats[i] || i}`}
                x={x}
                y={h - pad - barH}
                width={barW}
                height={Math.max(2, barH)}
                fill={SERIES_COLORS[i % SERIES_COLORS.length]}
                rx="0.5"
              />
            );
          })
        )}
      </svg>
      <div className="flex gap-0.5 truncate px-0.5 text-[7px] text-slate-500">
        {cats.slice(0, 4).map((c) => (
          <span key={c} className="truncate">
            {c}
          </span>
        ))}
      </div>
    </div>
  );
}
