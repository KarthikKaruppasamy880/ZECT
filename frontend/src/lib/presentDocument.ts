import type { PresentBlock, PresentSlide } from "@/lib/api";
import { WIDESCREEN_CX, WIDESCREEN_CY, geometryValid } from "@/lib/presentGeometry";

export const DOCUMENT_KINDS = new Set([
  "text",
  "body",
  "title",
  "subtitle",
  "bullet",
  "chart",
  "table",
  "image",
  "quote",
  "metric",
  "shape",
  "icon",
  "diagram",
  "group",
]);

export function slideSize(slideEmu?: { cx: number; cy: number }) {
  return {
    cx: slideEmu?.cx && slideEmu.cx > 0 ? slideEmu.cx : WIDESCREEN_CX,
    cy: slideEmu?.cy && slideEmu.cy > 0 ? slideEmu.cy : WIDESCREEN_CY,
  };
}

/** Editable document elements. If parse returned no blocks, seed a title from slide text. */
export function documentBlocks(slide: PresentSlide | undefined, slideEmu?: { cx: number; cy: number }): PresentBlock[] {
  if (!slide) return [];
  const existing = (slide.blocks || []).filter((b) => DOCUMENT_KINDS.has(String(b.kind)));
  if (existing.length) return existing;
  const text = (slide.text || "").trim() || "New slide";
  const size = slideSize(slideEmu);
  return [
    {
      id: `blk_${slide.index}_text_seed`,
      kind: "text",
      slide_index: slide.index,
      content: { text, role: "title" },
      geometry: { x: Math.round(size.cx * 0.05), y: Math.round(size.cy * 0.08), cx: Math.round(size.cx * 0.9), cy: Math.round(size.cy * 0.18) },
    },
  ];
}

/** Persist seeded blocks into slide state so select/drag/save work (blank decks). */
export function materializeSlideBlocks(slides: PresentSlide[], slideEmu?: { cx: number; cy: number }): PresentSlide[] {
  const size = slideSize(slideEmu);
  return slides.map((slide) => {
    const parsed = (slide.blocks || []).filter((b) => DOCUMENT_KINDS.has(String(b.kind)));
    if (parsed.length) return { ...slide, blocks: parsed };
    const seeded = documentBlocks(slide, size);
    return { ...slide, blocks: seeded };
  });
}

export function slideThemeColors(slide: PresentSlide | undefined): string[] {
  const theme = (slide as PresentSlide & { theme?: Record<string, string> })?.theme;
  if (theme && typeof theme === "object") {
    return [...new Set(Object.values(theme).filter((c) => String(c).startsWith("#")))] as string[];
  }
  return ["#FF7500", "#00628B", "#1A1A1A", "#44546A", "#FFFFFF"];
}

export function slideTextFromBlocks(slide: PresentSlide): string {
  const parts = (slide.blocks || [])
    .filter((b) => ["text", "quote", "metric"].includes(String(b.kind)))
    .map((b) => String(b.content?.text || b.content?.value || "").trim())
    .filter(Boolean);
  return parts.join("\n") || slide.text || "";
}

export function blockHasGeometry(block: PresentBlock): boolean {
  return geometryValid(block.geometry);
}

export function isLockedBlock(block: PresentBlock): boolean {
  return Boolean(block.content?.locked);
}

type GradientStop = { pos?: number; color?: string };
type FillGradient = { stops?: GradientStop[]; angle?: number };

/** OOXML linear gradient → CSS backgroundImage (PresentationDocument fill_gradient). */
export function cssGradientFill(content: Record<string, unknown> | undefined): string | undefined {
  const grad = content?.fill_gradient as FillGradient | undefined;
  const stops = (grad?.stops || []).filter((s) => String(s.color || "").startsWith("#"));
  if (!stops.length) return undefined;
  const sorted = [...stops].sort((a, b) => Number(a.pos || 0) - Number(b.pos || 0));
  const cssStops = sorted.map((s) => `${s.color} ${Math.round(Number(s.pos || 0) / 1000)}%`).join(", ");
  const angle = Math.round(Number(grad?.angle || 0) / 60000);
  return `linear-gradient(${angle}deg, ${cssStops})`;
}

/** Locked master/layout graphics render first; editable blocks on top. */
export function canvasBlocks(slide: PresentSlide | undefined, slideEmu?: { cx: number; cy: number }): PresentBlock[] {
  const blocks = documentBlocks(slide, slideEmu);
  const locked = blocks.filter((b) => isLockedBlock(b));
  const editable = blocks.filter((b) => !isLockedBlock(b));
  return [...locked, ...editable];
}

/** Fresh PPTX parse is source of truth for media/theme; cache only overlays editor deltas. */
export function mergeEditorCache(parsed: PresentSlide[], cached: PresentSlide[]): PresentSlide[] {
  return parsed.map((slide, index) => {
    const old = cached[index];
    if (!old) return slide;
    const byId = new Map((old.blocks || []).filter((b) => b.id).map((b) => [String(b.id), b]));
    return {
      ...slide,
      notes: old.notes ?? slide.notes,
      background: slide.background ?? old.background,
      blocks: (slide.blocks || []).map((block) => {
        const extra = block.id ? byId.get(String(block.id)) : undefined;
        if (!extra) return block;
        const parsedContent = block.content || {};
        const cachedContent = extra.content || {};
        return {
          ...block,
          geometry: geometryValid(extra.geometry) ? extra.geometry : block.geometry,
          content: {
            ...parsedContent,
            ...cachedContent,
            asset_id: parsedContent.asset_id || cachedContent.asset_id,
            data_url: parsedContent.data_url || (parsedContent.asset_id ? undefined : cachedContent.data_url),
            media_part: parsedContent.media_part || cachedContent.media_part,
            fill: parsedContent.fill || cachedContent.fill,
            fill_gradient: parsedContent.fill_gradient || cachedContent.fill_gradient,
            locked: parsedContent.locked ?? cachedContent.locked,
            text: cachedContent.text ?? parsedContent.text,
            font_size_pt: parsedContent.font_size_pt ?? cachedContent.font_size_pt,
            color: parsedContent.color ?? cachedContent.color,
            align: parsedContent.align ?? cachedContent.align,
            bold: parsedContent.bold ?? cachedContent.bold,
            italic: parsedContent.italic ?? cachedContent.italic,
          },
        };
      }),
    };
  });
}

/** Slide background from parsed theme/master/layout — not inferred from largest locked shape. */
export function slideBackgroundFill(
  slide: PresentSlide | undefined,
  _blocks: PresentBlock[],
  _slideEmu?: { cx: number; cy: number },
): string | undefined {
  const bg = slide?.background;
  const fill = String(bg?.fill || "").trim();
  if (fill.startsWith("#")) return fill;
  return "#ffffff";
}
