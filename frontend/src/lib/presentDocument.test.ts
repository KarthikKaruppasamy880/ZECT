import { describe, expect, it } from "vitest";
import { documentBlocks, slideTextFromBlocks } from "@/lib/presentDocument";

describe("presentDocument", () => {
  it("seeds a title block when parse returned no document kinds", () => {
    const blocks = documentBlocks({ index: 0, text: "Hello title", notes: "" }, { cx: 9144000, cy: 5143500 });
    expect(blocks).toHaveLength(1);
    expect(blocks[0].kind).toBe("text");
    expect(blocks[0].content?.text).toBe("Hello title");
    expect(blocks[0].geometry?.cx).toBeGreaterThan(0);
  });

  it("keeps parsed text/chart/table/image blocks instead of a screenshot placeholder", () => {
    const blocks = documentBlocks(
      {
        index: 0,
        text: "ignored",
        blocks: [
          { kind: "text", id: "t", content: { text: "Body" }, geometry: { x: 1, y: 1, cx: 10, cy: 10 } },
          { kind: "chart", id: "c", content: { categories: ["A", "B"], series: [{ values: [1, 2] }] }, geometry: { x: 1, y: 1, cx: 10, cy: 10 } },
        ],
      },
      { cx: 100, cy: 100 },
    );
    expect(blocks.map((b) => b.kind)).toEqual(["text", "chart"]);
  });

  it("joins text blocks for slide text save", () => {
    expect(
      slideTextFromBlocks({
        index: 0,
        text: "fallback",
        blocks: [{ kind: "text", content: { text: "One" } }, { kind: "quote", content: { text: "Two" } }],
      }),
    ).toBe("One\nTwo");
  });
});
