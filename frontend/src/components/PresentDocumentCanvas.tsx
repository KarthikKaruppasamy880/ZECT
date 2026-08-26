import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import type { PresentBlock, PresentSlide } from "@/lib/api";
import { mentrixPresentationAssetBlob } from "@/lib/api";
import { geometryPercentStyle, geometryValid } from "@/lib/presentGeometry";
import PresentChartPreview from "@/components/PresentChartPreview";
import PresentDiagramPreview from "@/components/PresentDiagramPreview";
import { canvasBlocks, cssGradientFill, isLockedBlock, slideBackgroundFill, slideSize } from "@/lib/presentDocument";

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
    return <div className="h-full w-full bg-slate-100/80" aria-hidden data-testid={testId} />;
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
  const blocks = canvasBlocks(slide, size);
  const bgFill = slideBackgroundFill(slide, blocks, size);
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const drag = useRef<null | {
    id: string;
    startX: number;
    startY: number;
    orig: { x: number; y: number; cx: number; cy: number };
    last?: { x: number; y: number; cx: number; cy: number };
    mode: "move" | "resize";
  }>(null);

  useEffect(() => {
    setEditingId(null);
  }, [slide.index, selectedId]);

  return (
    <div
      ref={canvasRef}
      className={`relative aspect-video w-full ${interactive ? "overflow-hidden" : "overflow-visible"} ${className}`}
      style={{ backgroundColor: bgFill || "#ffffff" }}
      data-testid={testId}
      data-canvas="document"
      data-slide-index={slide.index}
    >
      {blocks.map((block, i) => {
        const geo = block.geometry;
        const hasGeo = geometryValid(geo);
        if (!hasGeo) return null;
        const style = geometryPercentStyle(geo, size);
        const kind = String(block.kind);
        const locked = isLockedBlock(block);
        const selected = Boolean(!locked && block.id && block.id === selectedId);
        const fill = String(block.content?.fill || "");
        const gradient = cssGradientFill(block.content as Record<string, unknown> | undefined);
        const shape = String(block.content?.shape || "rect");
        const text = String(block.content?.text || block.content?.value || "");
        const fontSizePt = Number(block.content?.font_size_pt) || 0;
        const fontSizePx = fontSizePt > 0 ? `${Math.max(8, Math.round(fontSizePt * 1.333))}px` : undefined;
        const textColor = String(block.content?.color || "").trim();
        const textAlign = String(block.content?.align || "left") as "left" | "center" | "right" | "justify";
        const fontWeight = block.content?.bold ? "bold" : undefined;
        const fontStyle = block.content?.italic ? "italic" : undefined;
        const textStyle = {
          fontSize: fontSizePx,
          color: textColor.startsWith("#") ? textColor : undefined,
          textAlign,
          fontWeight,
          fontStyle,
        };
        const textEditable =
          interactive && !locked && (kind === "text" || kind === "quote" || kind === "metric" || kind === "shape");
        const isEditing = Boolean(textEditable && block.id && editingId === block.id);
        const canDrag = interactive && !locked && Boolean(block.id);
        const startDrag = (mode: "move" | "resize") => (e: ReactPointerEvent) => {
          if (!canDrag || !block.id) return;
          if (mode === "move" && isEditing) return;
          e.preventDefault();
          e.stopPropagation();
          try {
            e.currentTarget.setPointerCapture(e.pointerId);
          } catch {
            /* jsdom / legacy browsers */
          }
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
          const rect = canvasRef.current?.getBoundingClientRect();
          if (!rect?.width || !rect.height) return;
          const dx = ((e.clientX - d.startX) / rect.width) * size.cx;
          const dy = ((e.clientY - d.startY) / rect.height) * size.cy;
          const next =
            d.mode === "resize"
              ? { x: d.orig.x, y: d.orig.y, cx: Math.max(1, Math.round(d.orig.cx + dx)), cy: Math.max(1, Math.round(d.orig.cy + dy)) }
              : { x: Math.round(d.orig.x + dx), y: Math.round(d.orig.y + dy), cx: d.orig.cx, cy: d.orig.cy };
          d.last = next;
          onGeometry?.(d.id, next, { skipHistory: true });
        };
        const finishDrag = () => {
          const d = drag.current;
          if (d && d.id === block.id && d.last) {
            onGeometry?.(d.id, d.last);
          }
          drag.current = null;
        };
        const body =
          kind === "chart" ? (
            <PresentChartPreview block={block} testId={interactive ? "present-editor-chart-glyph" : undefined} />
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
            <PresentDiagramPreview block={block} testId={interactive ? "present-editor-diagram-glyph" : undefined} />
          ) : kind === "icon" ? (
            <div
              className="flex h-full items-center justify-center rounded-full text-lg font-bold text-white"
              style={{ backgroundColor: String(block.content?.fill || "#00628B") }}
              data-testid={interactive ? "present-editor-icon-glyph" : undefined}
            >
              {String(block.content?.glyph || "★")}
            </div>
          ) : kind === "image" ? (
            <ImageGlyph block={block} testId={interactive ? "present-editor-image-glyph" : undefined} />
          ) : textEditable ? (
            isEditing ? (
              <div
                contentEditable
                suppressContentEditableWarning
                data-testid={interactive ? `present-editor-inline-${kind}` : undefined}
                className={`h-full w-full overflow-hidden px-1 text-left leading-snug text-slate-900 outline-none ${
                  fontSizePx ? "" : "text-[11px]"
                }`}
                style={{ wordBreak: "break-word", ...textStyle }}
                onBlur={(e) => {
                  if (block.id) onChangeText?.(block.id, (e.currentTarget.textContent || "").slice(0, 800));
                  setEditingId(null);
                }}
              >
                {kind === "metric" ? `${block.content?.label || ""} ${block.content?.value || ""}` : text}
              </div>
            ) : (
              <span
                className={`block h-full cursor-move overflow-hidden px-1 py-0.5 text-left leading-snug text-slate-900 ${
                  fontSizePx ? "" : "text-[11px]"
                }`}
                style={textStyle}
              >
                {kind === "metric" ? `${block.content?.label || ""} ${block.content?.value || ""}` : text}
              </span>
            )
          ) : (
            <span
              className={`block h-full overflow-hidden px-1 py-0.5 text-left leading-tight text-slate-900 ${
                fontSizePx ? "" : "text-[10px]"
              }`}
              style={textStyle}
            >
              {text}
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
              backgroundColor: gradient ? undefined : fill || (kind === "shape" ? "#e8eef3" : "transparent"),
              backgroundImage: gradient,
              borderRadius: shape === "ellipse" ? "999px" : undefined,
            }}
            className={`absolute overflow-hidden text-left ${canDrag ? "cursor-move" : ""} ${
              locked
                ? "pointer-events-none"
                : selected
                  ? "ring-2 ring-teal-700"
                  : "ring-1 ring-transparent hover:ring-slate-300"
            }`}
            onClick={() => {
              if (!interactive || locked) return;
              onSelect?.(block.id || null);
              setEditingId(null);
            }}
            onDoubleClick={() => {
              if (!interactive || locked) return;
              if (textEditable && block.id) {
                setEditingId(block.id);
                onSelect?.(block.id);
                return;
              }
              onDoubleClick?.(block);
            }}
            onPointerDown={canDrag ? startDrag("move") : undefined}
            onPointerMove={canDrag ? onMove : undefined}
            onPointerUp={canDrag ? finishDrag : undefined}
            onPointerCancel={canDrag ? finishDrag : undefined}
          >
            {body}
            {interactive && selected && !locked ? (
              <span
                data-testid="present-editor-resize"
                className="absolute bottom-0 right-0 z-10 h-3 w-3 cursor-nwse-resize bg-teal-700"
                onPointerDown={(e) => {
                  e.stopPropagation();
                  startDrag("resize")(e);
                }}
                onPointerMove={onMove}
                onPointerUp={finishDrag}
              />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
