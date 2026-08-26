import type { PresentBlock } from "@/lib/api";
import { geometryValid } from "@/lib/presentGeometry";
import { boxesOverlap } from "@/lib/presentInsertPlacement";

export type SlideQualityReport = {
  overlapCount: number;
  outOfBounds: number;
  findings: string[];
};

const WIDE_CX = 9144000;
const WIDE_CY = 5143500;

function normGeo(block: PresentBlock) {
  const g = block.geometry;
  if (!geometryValid(g)) return null;
  return { x: g!.x || 0, y: g!.y || 0, cx: g!.cx || 0, cy: g!.cy || 0 };
}

/** Lightweight insert-time overlap check (mirrors QualityCritic geometry pass). */
export function critiqueSlideBlocks(blocks: PresentBlock[]): SlideQualityReport {
  const geos = blocks.map((b) => ({ block: b, geo: normGeo(b) })).filter((r) => r.geo) as Array<{
    block: PresentBlock;
    geo: { x: number; y: number; cx: number; cy: number };
  }>;
  let overlapCount = 0;
  let outOfBounds = 0;
  const findings: string[] = [];
  for (let i = 0; i < geos.length; i++) {
    const a = geos[i].geo;
    if (a.x + a.cx > WIDE_CX + 20000 || a.y + a.cy > WIDE_CY + 20000) {
      outOfBounds += 1;
      findings.push("out_of_bounds");
    }
    for (let j = i + 1; j < geos.length; j++) {
      const b = geos[j].geo;
      if (boxesOverlap(a, b)) {
        overlapCount += 1;
        findings.push("overlap");
      }
    }
  }
  return { overlapCount, outOfBounds, findings: [...new Set(findings)] };
}

export function qualityStatusMessage(report: SlideQualityReport): string | null {
  if (report.overlapCount > 0) {
    return `QualityCritic: ${report.overlapCount} overlap(s) on this slide — adjust layout or use Fix layout in AI.`;
  }
  if (report.outOfBounds > 0) {
    return `QualityCritic: content extends beyond slide bounds.`;
  }
  return null;
}
