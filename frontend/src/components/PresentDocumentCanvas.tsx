import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import type { PresentBlock, PresentSlide } from "@/lib/api";
import { mentrixPresentationAssetBlob } from "@/lib/api";
import { geometryPercentStyle, geometryValid } from "@/lib/presentGeometry";
import { documentBlocks, slideSize } from "@/lib/presentDocument";

type Props = {
  slide: PresentSlide;
  slideEmu: { cx: number; cy: number };
  selectedId?: string | null;
  interactive?: boolean;
  testId?: string;
  className?: string;
  onSelect?: (id: string | null) => void;
  onChangeText?: (id: string, text: string) => void;
  onDoubleClick?: (block: PresentBlock) => void;
  onGeometry?: (id: string, geo: { x: number; y: number; cx: number; cy: number }, opts?: { skipHistory?: boolean }) => void;
};

function ChartGlyph({ block, testId }: { block: PresentBlock; testId?: string }) {
  const cats = (block.content?.categories as string[]) || [];
  const series = (block.content?.series as Array<{ name?: string; values?: number[] }>) || [];
  const values = series[0]?.values || [];
  const max = Math.max(1, ...values.map((v) => Math.abs(Number(v) || 0)));
  if (!cats.length || !values.length) {
    return <p className="truncate px-1 text-[10px] uppercase">Chart</p>;
  }
  return (
    <div className="flex h-full items-end gap-0.5 px-1 py-0.5" data-testid={testId}>
      {values.slice(0, 8).map((v, i) => (
        <span
          key={`${cats[i] || i}`}
          className="flex-1 bg-teal-700/80"
          style={{ height: `${Math.max(8, (100 * Math.abs(Number(v) || 0)) / max)}%` }}
          title={`${cats[i] || ""} ${v}`}
        />
      ))}
    </div>
  );
}

function ImageGlyph({ block, testId }: { block: PresentBlock; testId?: string }) {
  const dataUrl = String(block.content?.data_url || "");
  const assetId = String(block.content?.asset_id || "");
  const alt = String(block.content?.alt || "Image");
  const fit = String(block.content?.fit || "contain");
  const [src, setSrc] = useState(dataUrl);
  useEffect(() => {
    if (dataUrl) {
      setSrc(dataUrl);
      return;
    }
    if (!assetId) return;
    let alive = true;
    void mentrixPresentationAssetBlob(assetId)
      .then((url) => {
        if (alive) setSrc(url);
      })
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [dataUrl, assetId]);
  if (!src) {
    return <p className="truncate px-1 text-[10px]">{alt}</p>;
  }
  return (
    <img
      src={src}
      alt={alt}
      data-testid={testId}
      className={`h-full w-full ${fit === "cover" ? "object-cover" : fit === "stretch" ? "object-fill" : "object-contain"}`}
    />
  );
}

export default function PresentDocumentCanvas({
  slide,
  slideEmu,
  selectedId,
  interactive = true,
  testId = "present-editor-document-canvas",
  className = "",
  onSelect,
  onChangeText,
  onDoubleClick,
  onGeometry,
}: Props) {
  const size = slideSize(slideEmu);
  const blocks = documentBlocks(slide, size);
  const drag = useRef<null | {
    id: string;
    startX: number;
    startY: number;
    orig: { x: number; y: number; cx: number; cy: number };
    mode: "move" | "resize";
  }>(null);

  return (
    <div
      className={`relative aspect-video w-full overflow-hidden bg-white ${className}`}
      data-testid={testId}
      data-canvas="document"
      data-slide-index={slide.index}
    >
      {blocks.map((block, i) => {
        const geo = block.geometry;
        const hasGeo = geometryValid(geo);
        if (!hasGeo) return null;
        const style = geometryPercentStyle(geo, size);
        const selected = Boolean(block.id && block.id === selectedId);
        const kind = String(block.kind);
        const locked = Boolean(block.content?.locked);
        const fill = String(block.content?.fill || "");
        const shape = String(block.content?.shape || "rect");
        const text = String(block.content?.text || block.content?.alt || block.content?.value || "");
        const editable = interactive && !locked && (kind === "text" || kind === "quote" || kind === "metric" || kind === "shape");
        const startDrag = (mode: "move" | "resize") => (e: ReactPointerEvent) => {
          if (!interactive || locked || !block.id) return;
          if ((e.target as HTMLElement).isContentEditable) return;
          e.stopPropagation();
          e.currentTarget.setPointerCapture(e.pointerId);
          drag.current = {
            id: block.id,
            startX: e.clientX,
            startY: e.clientY,
            orig: { x: geo?.x || 0, y: geo?.y || 0, cx: geo?.cx || 1, cy: geo?.cy || 1 },
            mode,
          };
          onSelect?.(block.id);
        };
        const onMove = (e: ReactPointerEvent) => {
          const d = drag.current;
          if (!d || d.id !== block.id) return;
          const rect = (e.currentTarget.parentElement as HTMLElement | null)?.getBoundingClientRect();
          if (!rect?.width || !rect.height) return;
          const dx = ((e.clientX - d.startX) / rect.width) * size.cx;
          const dy = ((e.clientY - d.startY) / rect.height) * size.cy;
          const next =
            d.mode === "resize"
              ? { x: d.orig.x, y: d.orig.y, cx: Math.max(1, Math.round(d.orig.cx + dx)), cy: Math.max(1, Math.round(d.orig.cy + dy)) }
              : { x: Math.round(d.orig.x + dx), y: Math.round(d.orig.y + dy), cx: d.orig.cx, cy: d.orig.cy };
          onGeometry?.(d.id, next, { skipHistory: true });
        };
        const body =
          kind === "chart" ? (
            <ChartGlyph block={block} testId={interactive ? "present-editor-chart-glyph" : undefined} />
          ) : kind === "table" ? (
            <table className="h-full w-full table-fixed border-collapse text-[8px]" data-testid={interactive ? "present-editor-table-glyph" : undefined}>
              <thead>
                <tr>
                  {((block.content?.headers as string[]) || ["A", "B"]).map((h) => (
                    <th key={h} className="truncate border border-slate-300 bg-slate-50 px-0.5 text-left">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(((block.content?.rows as string[][]) || []) as string[][]).slice(0, 6).map((row, ri) => (
                  <tr key={ri}>
                    {row.map((cell, ci) => (
                      <td key={ci} className="truncate border border-slate-200 px-0.5">
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          ) : kind === "diagram" || kind === "group" ? (
            <div className="flex h-full gap-0.5 p-0.5" data-testid={interactive ? "present-editor-diagram-glyph" : undefined}>
              {((block.content?.nodes as string[]) || ["A", "B", "C"]).map((n) => (
                <span key={n} className="flex-1 truncate rounded border border-slate-300 bg-white px-0.5 text-[8px]">
                  {n}
                </span>
              ))}
            </div>
          ) : kind === "image" ? (
            <ImageGlyph block={block} testId={interactive ? "present-editor-image-glyph" : undefined} />
          ) : editable ? (
            <div
              contentEditable
              suppressContentEditableWarning
              data-testid={interactive ? `present-editor-inline-${kind}` : undefined}
              className="h-full w-full overflow-hidden px-1 text-left text-[11px] text-slate-900 outline-none"
              onBlur={(e) => block.id && onChangeText?.(block.id, (e.currentTarget.textContent || "").slice(0, 800))}
            >
              {kind === "metric" ? `${block.content?.label || ""} ${block.content?.value || ""}` : text || kind}
            </div>
          ) : (
            <span className="block h-full overflow-hidden px-1 py-0.5 text-left text-[10px] leading-tight text-slate-900">
              {text || (kind === "shape" ? "" : kind)}
            </span>
          );
        return (
          <div
            key={block.id || `${kind}-${i}`}
            role={interactive ? "button" : undefined}
            tabIndex={interactive ? 0 : undefined}
            data-testid={interactive ? `present-editor-block-hit-${kind === "text" ? "text" : kind}` : undefined}
            data-block-id={block.id || `${kind}-${i}`}
            data-locked={locked ? "true" : "false"}
            style={{
              ...style,
              backgroundColor: fill || (kind === "shape" ? "#e8eef3" : "transparent"),
              borderRadius: shape === "ellipse" ? "999px" : undefined,
            }}
            className={`absolute overflow-hidden text-left ${
              selected ? "ring-2 ring-teal-700" : locked ? "" : "ring-1 ring-transparent hover:ring-slate-300"
            }`}
            onClick={() => interactive && onSelect?.(block.id || null)}
            onDoubleClick={() => interactive && !locked && onDoubleClick?.(block)}
            onPointerDown={interactive && !locked ? startDrag("move") : undefined}
            onPointerMove={interactive && !locked ? onMove : undefined}
            onPointerUp={() => {
              drag.current = null;
            }}
          >
            {body}
            {interactive && selected && !locked ? (
              <span
                data-testid="present-editor-resize"
                className="absolute bottom-0 right-0 h-2.5 w-2.5 cursor-nwse-resize bg-teal-700"
                onPointerDown={startDrag("resize")}
              />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
