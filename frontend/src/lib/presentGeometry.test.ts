import { describe, expect, it } from "vitest";
import { composeChildGeometry, geometryPercentStyle, geometryValid, WIDESCREEN_CX } from "./presentGeometry";

describe("presentGeometry", () => {
  it("rejects missing or zero extents so overlays never cover the slide", () => {
    expect(geometryValid(undefined)).toBe(false);
    expect(geometryValid({ cx: 0, cy: 10 })).toBe(false);
    expect(geometryValid({ x: 0, y: 0, cx: 100, cy: 50 })).toBe(true);
  });

  it("maps EMU boxes to percents of slide size", () => {
    const style = geometryPercentStyle({ x: 914400, y: 0, cx: 914400, cy: 100 }, { cx: WIDESCREEN_CX, cy: 1000 });
    expect(style?.left).toBe("10%");
    expect(style?.width).toBe("10%");
    expect(geometryPercentStyle({ cx: 0, cy: 1 }, { cx: WIDESCREEN_CX, cy: 1000 })).toBeUndefined();
  });

  it("composes group child offsets onto the parent origin", () => {
    const abs = composeChildGeometry({ x: 100, y: 200, cx: 1000, cy: 800 }, { x: 10, y: 20, cx: 50, cy: 60 });
    expect(abs).toEqual({ x: 110, y: 220, cx: 50, cy: 60 });
    expect(composeChildGeometry(null, { cx: 0, cy: 1 })).toBeUndefined();
  });
});
