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
