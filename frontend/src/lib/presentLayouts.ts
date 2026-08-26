import type { PresentBlock, PresentSlide } from "@/lib/api";
import { WIDESCREEN_CX, WIDESCREEN_CY } from "@/lib/presentGeometry";

export type BlankLayoutId =
  | "blank"
  | "title_slide"
  | "title_content"
  | "section"
  | "two_column"
  | "comparison"
  | "picture_text";

export type EditorLayoutId = "title_body" | "split_image" | "two_col";

export const BLANK_LAYOUT_OPTIONS: Array<{ id: BlankLayoutId; label: string; description: string }> = [
  { id: "title_slide", label: "Title slide", description: "Title and subtitle placeholders" },
  { id: "title_content", label: "Title + content", description: "Title with body area" },
  { id: "blank", label: "Blank", description: "Empty slide with theme accent only" },
  { id: "section", label: "Section", description: "Section divider title" },
  { id: "two_column", label: "Two column", description: "Title with left and right columns" },
  { id: "comparison", label: "Comparison", description: "Side-by-side comparison columns" },
  { id: "picture_text", label: "Picture + text", description: "Title with image and text areas" },
];

const THEME = { text: "#1A1A1A", muted: "#44546A", accent: "#FF7500" };

function accentBar(slideIndex: number): PresentBlock {
  return {
    id: `blk_${slideIndex}_accent`,
    kind: "shape",
    slide_index: slideIndex,
    geometry: { x: 0, y: 0, cx: Math.round(WIDESCREEN_CX * 0.012), cy: WIDESCREEN_CY },
    content: { shape: "rect", fill: THEME.accent, locked: false },
    provenance: { source: "layout", generated: true },
  };
}

function textBlock(
  slideIndex: number,
  id: string,
  role: string,
  text: string,
  geo: { x: number; y: number; cx: number; cy: number },
  fontSize: number,
  color: string,
  bold = false,
): PresentBlock {
  return {
    id: `blk_${slideIndex}_${id}`,
    kind: "text",
    slide_index: slideIndex,
    geometry: geo,
    content: { text, role, font_size_pt: fontSize, color, align: "left", ...(bold ? { bold: true } : {}) },
    provenance: { source: "layout", generated: true },
  };
}

/** Build starter blocks for a blank layout (mirrors backend blank_document.py). */
export function blocksForBlankLayout(slideIndex: number, layout: BlankLayoutId): PresentBlock[] {
  const cx = WIDESCREEN_CX;
  const cy = WIDESCREEN_CY;
  const accent = accentBar(slideIndex);
  if (layout === "blank") return [accent];
  if (layout === "section") {
    return [
      accent,
      textBlock(slideIndex, "section_title", "title", "Section title", {
        x: Math.round(cx * 0.08),
        y: Math.round(cy * 0.38),
        cx: Math.round(cx * 0.84),
        cy: Math.round(cy * 0.18),
      }, 44, THEME.text, true),
    ];
  }
  if (layout === "title_content") {
    return [
      accent,
      textBlock(slideIndex, "title", "title", "Untitled presentation", {
        x: Math.round(cx * 0.08),
        y: Math.round(cy * 0.1),
        cx: Math.round(cx * 0.84),
        cy: Math.round(cy * 0.12),
      }, 36, THEME.text, true),
      textBlock(slideIndex, "body", "body", "", {
        x: Math.round(cx * 0.08),
        y: Math.round(cy * 0.28),
        cx: Math.round(cx * 0.84),
        cy: Math.round(cy * 0.58),
      }, 18, THEME.text),
    ];
  }
  if (layout === "two_column" || layout === "comparison") {
    return [
      accent,
      textBlock(slideIndex, "title", "title", "Untitled presentation", {
        x: Math.round(cx * 0.08),
        y: Math.round(cy * 0.08),
        cx: Math.round(cx * 0.84),
        cy: Math.round(cy * 0.1),
      }, 32, THEME.text, true),
      textBlock(slideIndex, "left", "body", "", {
        x: Math.round(cx * 0.08),
        y: Math.round(cy * 0.24),
        cx: Math.round(cx * 0.4),
        cy: Math.round(cy * 0.62),
      }, 16, THEME.text),
      textBlock(slideIndex, "right", "body", "", {
        x: Math.round(cx * 0.52),
        y: Math.round(cy * 0.24),
        cx: Math.round(cx * 0.4),
        cy: Math.round(cy * 0.62),
      }, 16, THEME.text),
    ];
  }
  if (layout === "picture_text") {
    return [
      accent,
      textBlock(slideIndex, "title", "title", "Untitled presentation", {
        x: Math.round(cx * 0.08),
        y: Math.round(cy * 0.07),
        cx: Math.round(cx * 0.84),
        cy: Math.round(cy * 0.1),
      }, 32, THEME.text, true),
      textBlock(slideIndex, "body", "body", "", {
        x: Math.round(cx * 0.08),
        y: Math.round(cy * 0.22),
        cx: Math.round(cx * 0.44),
        cy: Math.round(cy * 0.68),
      }, 16, THEME.text),
      {
        id: `blk_${slideIndex}_picture`,
        kind: "image",
        slide_index: slideIndex,
        geometry: {
          x: Math.round(cx * 0.56),
          y: Math.round(cy * 0.22),
          cx: Math.round(cx * 0.36),
          cy: Math.round(cy * 0.55),
        },
        content: { alt: "Picture placeholder", fit: "contain", caption: "Insert picture" },
        provenance: { source: "blank", generated: true },
      },
    ];
  }
  return [
    accent,
    textBlock(slideIndex, "title", "title", "Untitled presentation", {
      x: Math.round(cx * 0.08),
      y: Math.round(cy * 0.14),
      cx: Math.round(cx * 0.84),
      cy: Math.round(cy * 0.14),
    }, 40, THEME.text, true),
    textBlock(slideIndex, "subtitle", "subtitle", "", {
      x: Math.round(cx * 0.08),
      y: Math.round(cy * 0.32),
      cx: Math.round(cx * 0.84),
      cy: Math.round(cy * 0.08),
    }, 20, THEME.muted),
  ];
}

const EDITOR_TO_BLANK: Record<EditorLayoutId, BlankLayoutId> = {
  title_body: "title_content",
  split_image: "picture_text",
  two_col: "two_column",
};

/** Apply a master layout to the current slide, preserving non-layout visuals where possible. */
export function applyEditorLayout(slide: PresentSlide, layout: EditorLayoutId): PresentSlide {
  const blankLayout = EDITOR_TO_BLANK[layout];
  const layoutBlocks = blocksForBlankLayout(slide.index, blankLayout);
  const visuals = (slide.blocks || []).filter((b) =>
    ["chart", "table", "image", "diagram", "metric", "quote", "shape", "icon"].includes(String(b.kind)),
  );
  const text = layoutBlocks
    .filter((b) => b.kind === "text")
    .map((b) => String(b.content?.text || "").trim())
    .filter(Boolean)
    .join(" ");
  return {
    ...slide,
    layout_intent: blankLayout,
    text: text || slide.text,
    blocks: [...layoutBlocks, ...visuals],
  };
}
