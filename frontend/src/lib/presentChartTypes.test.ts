import { chartTypeFromPrompt, PRESENT_CHART_TYPES } from "./presentChartTypes";
import { describe, expect, it } from "vitest";

describe("presentChartTypes", () => {
  it("covers Presenton chart labels including radar", () => {
    const ids = PRESENT_CHART_TYPES.map((row) => row.id);
    expect(ids).toContain("radar");
    expect(ids).toContain("stacked_horizontal");
    expect(ids).toContain("scatter");
    expect(chartTypeFromPrompt("make this a radar chart")).toBe("radar");
  });
});
