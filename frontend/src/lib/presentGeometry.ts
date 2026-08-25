/** Shared EMU overlay math for Present thumbs + canvas (E1 / E6). */

export const WIDESCREEN_CX = 9144000;
export const WIDESCREEN_CY = 5143500;

export type EmuBox = { x?: number; y?: number; cx?: number; cy?: number };

export function geometryValid(geo?: EmuBox | null): boolean {
  return Boolean(geo && (geo.cx || 0) > 0 && (geo.cy || 0) > 0);
}

export function geometryPercentStyle(
  geo: EmuBox | undefined,
  slide: { cx: number; cy: number },
): { position: "absolute"; left: string; top: string; width: string; height: string } | undefined {
  if (!geometryValid(geo)) return undefined;
  const cx = slide.cx > 0 ? slide.cx : WIDESCREEN_CX;
  const cy = slide.cy > 0 ? slide.cy : WIDESCREEN_CY;
  return {
    position: "absolute",
    left: `${(100 * (geo?.x || 0)) / cx}%`,
    top: `${(100 * (geo?.y || 0)) / cy}%`,
    width: `${(100 * (geo?.cx || 1)) / cx}%`,
    height: `${(100 * (geo?.cy || 1)) / cy}%`,
  };
}

export const NUDGE_EMU = 50000;

export function composeChildGeometry(parent?: EmuBox | null, child?: EmuBox | null): EmuBox | undefined {
  if (!geometryValid(child)) return undefined;
  if (!geometryValid(parent)) {
    return { x: child?.x || 0, y: child?.y || 0, cx: child?.cx || 0, cy: child?.cy || 0 };
  }
  return {
    x: (parent?.x || 0) + (child?.x || 0),
    y: (parent?.y || 0) + (child?.y || 0),
    cx: child?.cx || 0,
    cy: child?.cy || 0,
  };
}
