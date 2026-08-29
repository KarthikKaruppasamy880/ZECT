import type { PresentBlock } from "@/lib/api";
import { WIDESCREEN_CX, WIDESCREEN_CY, type EmuBox } from "@/lib/presentGeometry";

const MARGIN_X = Math.round(WIDESCREEN_CX * 0.08);
const MARGIN_Y = Math.round(WIDESCREEN_CY * 0.1);
const GAP = Math.round(WIDESCREEN_CX * 0.02);
const PAD = 8000;

export type PlacedGeometry = { x: number; y: number; cx: number; cy: number };

const VISUAL_KINDS = new Set(["chart", "table", "image", "diagram", "metric", "quote", "shape", "icon"]);

function normGeo(geo?: EmuBox | null): PlacedGeometry | null {
  if (!geo || (geo.cx || 0) <= 0 || (geo.cy || 0) <= 0) return null;
  return {
    x: Math.round(geo.x || 0),
    y: Math.round(geo.y || 0),
    cx: Math.round(geo.cx || 0),
    cy: Math.round(geo.cy || 0),
  };
}

export function boxesOverlap(a: PlacedGeometry, b: PlacedGeometry, pad = PAD): boolean {
  return !(
    a.x + a.cx + pad <= b.x ||
    b.x + b.cx + pad <= a.x ||
    a.y + a.cy + pad <= b.y ||
    b.y + b.cy + pad <= a.y
  );
}

function contentRegion(): PlacedGeometry {
  return {
    x: MARGIN_X,
    y: Math.round(WIDESCREEN_CY * 0.46),
    cx: WIDESCREEN_CX - 2 * MARGIN_X,
    cy: Math.round(WIDESCREEN_CY * 0.46),
  };
}

function splitHorizontal(box: PlacedGeometry, leftRatio = 0.5): [PlacedGeometry, PlacedGeometry] {
  const leftW = Math.floor(box.cx * leftRatio) - Math.floor(GAP / 2);
  const rightW = box.cx - leftW - GAP;
  return [
    { x: box.x, y: box.y, cx: leftW, cy: box.cy },
    { x: box.x + leftW + GAP, y: box.y, cx: rightW, cy: box.cy },
  ];
}

function splitVertical(box: PlacedGeometry, topRatio = 0.55): [PlacedGeometry, PlacedGeometry] {
  const topH = Math.floor(box.cy * topRatio) - Math.floor(GAP / 2);
  const bottomH = box.cy - topH - GAP;
  return [
    { x: box.x, y: box.y, cx: box.cx, cy: topH },
    { x: box.x, y: box.y + topH + GAP, cx: box.cx, cy: bottomH },
  ];
}

function occupied(blocks: PresentBlock[]): PlacedGeometry[] {
  return blocks
    .filter((b) => !Boolean((b.content as Record<string, unknown> | undefined)?.locked))
    .map((b) => normGeo(b.geometry))
    .filter((g): g is PlacedGeometry => g !== null);
}

function fits(slot: PlacedGeometry, taken: PlacedGeometry[]): boolean {
  return taken.every((t) => !boxesOverlap(slot, t));
}

function defaultSize(kind: string): PlacedGeometry {
  const region = contentRegion();
  if (kind === "chart") {
    const [left] = splitHorizontal(region, 0.52);
    return left;
  }
  if (kind === "table") {
    const [, right] = splitHorizontal(region, 0.52);
    return right;
  }
  if (kind === "image") {
    const [, right] = splitHorizontal(region, 0.48);
    return right;
  }
  if (kind === "text") {
    return {
      x: MARGIN_X,
      y: Math.round(WIDESCREEN_CY * 0.44),
      cx: WIDESCREEN_CX - 2 * MARGIN_X,
      cy: Math.round(WIDESCREEN_CY * 0.12),
    };
  }
  if (kind === "icon") {
    return {
      x: Math.round(WIDESCREEN_CX * 0.42),
      y: Math.round(WIDESCREEN_CY * 0.35),
      cx: Math.round(WIDESCREEN_CX * 0.12),
      cy: Math.round(WIDESCREEN_CY * 0.18),
    };
  }
  if (kind === "shape") {
    return {
      x: Math.round(WIDESCREEN_CX * 0.35),
      y: Math.round(WIDESCREEN_CY * 0.35),
      cx: Math.round(WIDESCREEN_CX * 0.3),
      cy: Math.round(WIDESCREEN_CY * 0.22),
    };
  }
  return {
    x: region.x,
    y: region.y,
    cx: Math.min(region.cx, Math.round(WIDESCREEN_CX * 0.42)),
    cy: Math.min(region.cy, Math.round(WIDESCREEN_CY * 0.38)),
  };
}

function candidateSlots(kind: string, blocks: PresentBlock[]): PlacedGeometry[] {
  const region = contentRegion();
  const [left, right] = splitHorizontal(region, 0.5);
  const [top, bottom] = splitVertical(region, 0.55);
  const hasChart = blocks.some((b) => b.kind === "chart");
  const hasTable = blocks.some((b) => b.kind === "table");

  if (kind === "chart") {
    if (hasTable) return [left, top, region];
    return [left, top, region];
  }
  if (kind === "table") {
    if (hasChart) return [right, bottom, region];
    return [right, bottom, region];
  }
  if (kind === "image") {
    if (hasChart || hasTable) return [right, bottom, region];
    return [right, region, left];
  }
  return [defaultSize(kind), region, left, right, top, bottom];
}

function stackBelow(taken: PlacedGeometry[]): PlacedGeometry {
  const region = contentRegion();
  if (!taken.length) return defaultSize("chart");
  const lowest = taken.reduce((a, b) => (a.y + a.cy > b.y + b.cy ? a : b));
  const y = Math.min(lowest.y + lowest.cy + GAP, WIDESCREEN_CY - MARGIN_Y - Math.round(WIDESCREEN_CY * 0.2));
  return {
    x: region.x,
    y,
    cx: Math.round(region.cx * 0.48),
    cy: Math.round(WIDESCREEN_CY * 0.22),
  };
}

/** Pick non-overlapping geometry for a new insert on the active slide. */
export function placeInsertGeometry(kind: string, existingBlocks: PresentBlock[]): PlacedGeometry {
  const visual = existingBlocks.filter((b) => VISUAL_KINDS.has(String(b.kind || "")));
  const taken = occupied(existingBlocks);
  const slots = candidateSlots(kind, visual);
  for (const slot of slots) {
    if (fits(slot, taken)) return slot;
  }
  const stacked = stackBelow(taken);
  if (fits(stacked, taken)) return stacked;
  return {
    ...stacked,
    x: stacked.x + taken.length * GAP,
    y: stacked.y + taken.length * GAP,
  };
}

export function createEditorBlock(
  kind: string,
  slideIndex: number,
  content: Record<string, unknown>,
  existingBlocks: PresentBlock[] = [],
): PresentBlock {
  return {
    id: `blk_${slideIndex}_${kind}_${Date.now()}`,
    kind,
    slide_index: slideIndex,
    content,
    geometry: placeInsertGeometry(kind, existingBlocks),
    provenance: { source: "editor", generated: false },
    validation: { ok: true, errors: [] },
  };
}
