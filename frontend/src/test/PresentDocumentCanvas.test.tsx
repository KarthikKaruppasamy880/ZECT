import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import PresentDocumentCanvas from "@/components/PresentDocumentCanvas";
import type { PresentSlide } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  mentrixPresentationAssetBlob: vi.fn(async () => "blob:asset"),
}));

const slideEmu = { cx: 1000, cy: 500 };

function slide(blocks: PresentSlide["blocks"]): PresentSlide {
  return { index: 0, text: "Title", blocks };
}

describe("PresentDocumentCanvas", () => {
  it("renders text, chart, table, diagram, image, and shape from document state", () => {
    render(
      <PresentDocumentCanvas
        slide={slide([
          { id: "t", kind: "text", content: { text: "Hello canvas" }, geometry: { x: 0, y: 0, cx: 200, cy: 50 } },
          {
            id: "c",
            kind: "chart",
            content: { categories: ["A", "B"], series: [{ name: "S", values: [1, 2] }] },
            geometry: { x: 0, y: 60, cx: 200, cy: 80 },
          },
          {
            id: "tb",
            kind: "table",
            content: { headers: ["H1", "H2"], rows: [["a", "b"]] },
            geometry: { x: 220, y: 0, cx: 200, cy: 80 },
          },
          {
            id: "d",
            kind: "diagram",
            content: { nodes: ["N1", "N2"] },
            geometry: { x: 220, y: 90, cx: 200, cy: 40 },
          },
          {
            id: "i",
            kind: "image",
            content: { alt: "Logo", data_url: "data:image/png;base64,aaaa" },
            geometry: { x: 0, y: 160, cx: 80, cy: 80 },
          },
          {
            id: "s",
            kind: "shape",
            content: { shape: "rect", text: "Box", fill: "#abcdef" },
            geometry: { x: 100, y: 160, cx: 80, cy: 80 },
          },
        ])}
        slideEmu={slideEmu}
        testId="present-editor-canvas"
      />,
    );
    expect(screen.getByTestId("present-editor-canvas").getAttribute("data-canvas")).toBe("document");
    expect(screen.getByTestId("present-editor-block-hit-text").textContent).toMatch(/Hello canvas/);
    expect(screen.getByTestId("present-editor-chart-glyph")).toBeTruthy();
    expect(screen.getByTestId("present-editor-table-glyph").textContent).toMatch(/H1/);
    expect(screen.getByTestId("present-editor-diagram-glyph").textContent).toMatch(/N1/);
    expect(screen.getByTestId("present-editor-image-glyph").getAttribute("alt")).toBe("Logo");
    expect(screen.getByTestId("present-editor-block-hit-shape")).toBeTruthy();
  });

  it("does not paint blocks without geometry as giant covering boxes", () => {
    const { container } = render(
      <PresentDocumentCanvas
        slide={slide([{ id: "bad", kind: "shape", content: { text: "no geo" } }])}
        slideEmu={slideEmu}
      />,
    );
    expect(container.querySelector('[data-testid="present-editor-block-hit-shape"]')).toBeNull();
  });

  it("moves editable text blocks on pointer drag when not focused", () => {
    const onGeometry = vi.fn();
    render(
      <PresentDocumentCanvas
        slide={slide([
          { id: "t", kind: "text", content: { text: "Move me" }, geometry: { x: 100, y: 100, cx: 200, cy: 50 } },
        ])}
        slideEmu={slideEmu}
        testId="present-editor-canvas"
        onGeometry={onGeometry}
      />,
    );
    const canvas = screen.getByTestId("present-editor-canvas");
    vi.spyOn(canvas, "getBoundingClientRect").mockReturnValue({
      x: 0,
      y: 0,
      width: 1000,
      height: 500,
      top: 0,
      left: 0,
      bottom: 500,
      right: 1000,
      toJSON: () => ({}),
    });
    const block = screen.getByTestId("present-editor-block-hit-text");
    block.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, clientX: 50, clientY: 50, pointerId: 1, buttons: 1 }));
    block.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, clientX: 120, clientY: 80, pointerId: 1, buttons: 1 }));
    block.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, clientX: 120, clientY: 80, pointerId: 1 }));
    expect(onGeometry).toHaveBeenCalled();
    const last = onGeometry.mock.calls[onGeometry.mock.calls.length - 1];
    expect(last[1].x).toBeGreaterThan(100);
    expect(last[1].y).toBeGreaterThan(100);
  });
});
