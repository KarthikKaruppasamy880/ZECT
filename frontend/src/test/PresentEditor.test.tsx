import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("@/lib/api", () => ({
  mentrixAnalyzeDeck: vi.fn(async () => ({ improved_notes: [] })),
  mentrixPresentSlideAi: vi.fn(async () => ({ ok: true, action: "chart_type", chart_type: "radar" })),
  mentrixParsePptxFromPath: vi.fn(async () => ({
    ok: true,
    filename: "deck.pptx",
    slides: [
      { index: 0, text: "One", notes: "n1" },
      { index: 1, text: "Two", notes: "n2" },
    ],
  })),
  mentrixPresentPptxDownload: vi.fn(),
  mentrixPresentQualityGate: vi.fn(),
  mentrixPresentSaveNotes: vi.fn(async () => ({ ok: true, ooxml_roundtrip: true })),
  mentrixPresentSlidePreview: vi.fn(async () => ({ url: "blob:preview", kind: "ooxml" })),
  mentrixPresentationAssetUpload: vi.fn(),
  mentrixPresentationAssetBlob: vi.fn(async () => "blob:asset"),
}));

import PresentEditor from "@/components/PresentEditor";
import { mentrixParsePptxFromPath, mentrixPresentSaveNotes } from "@/lib/api";

const deckPath = "C:\\Users\\me\\Documents\\deck.pptx";

const defaultSlides = [
  { index: 0, text: "One", notes: "n1" },
  { index: 1, text: "Two", notes: "n2" },
];

describe("PresentEditor v1", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.mocked(mentrixParsePptxFromPath).mockResolvedValue({
      ok: true,
      count: 2,
      filename: "deck.pptx",
      slides: defaultSlides,
    });
    if (typeof URL.revokeObjectURL !== "function") {
      URL.revokeObjectURL = () => undefined;
    }
  });

  it("duplicates a slide and reports OOXML save", async () => {
    render(<PresentEditor pptxPath={deckPath} variant="studio" />);
    await waitFor(() => {
      expect(screen.getByTestId("present-editor-thumb-0")).toBeTruthy();
    });
    fireEvent.click(screen.getByTestId("present-editor-duplicate-0"));
    await waitFor(() => {
      expect(screen.getByTestId("present-editor-thumb-2")).toBeTruthy();
    });
    fireEvent.click(screen.getByTestId("present-editor-shortcuts"));
    expect(screen.getByTestId("present-editor-shortcuts-modal")).toBeTruthy();
    fireEvent.click(screen.getByTestId("present-editor-save"));
    await waitFor(() => {
      expect(mentrixPresentSaveNotes).toHaveBeenCalled();
      expect(screen.getByTestId("present-editor-status").textContent).toMatch(/Saved into PPTX/i);
    });
    expect(screen.getByTestId("present-editor-rail")).toBeTruthy();
    expect(screen.getByTestId("present-editor-palette")).toBeTruthy();
    expect(screen.getByTestId("present-editor-tab-ai")).toBeTruthy();
    expect(screen.getByTestId("present-editor-canvas")).toBeTruthy();
    expect(screen.getByTestId("present-editor-ai-intro")).toBeTruthy();
  });

  it("toasts that Save is required after adding a chart", async () => {
    render(<PresentEditor pptxPath={deckPath} variant="studio" />);
    await waitFor(() => {
      expect(screen.getByTestId("present-editor-tab-insert")).toBeTruthy();
    });
    fireEvent.click(screen.getByTestId("present-editor-tab-insert"));
    fireEvent.click(screen.getByTestId("present-editor-add-chart"));
    expect(screen.getByTestId("present-editor-status").textContent).toMatch(/Save to persist/i);
  });

  it("changes selected chart type to radar instead of appending another stub", async () => {
    render(<PresentEditor pptxPath={deckPath} variant="studio" />);
    await waitFor(() => {
      expect(screen.getByTestId("present-editor-tab-insert")).toBeTruthy();
    });
    fireEvent.click(screen.getByTestId("present-editor-tab-insert"));
    fireEvent.click(screen.getByTestId("present-editor-add-chart"));
    await waitFor(() => {
      expect(screen.getByTestId("present-editor-block-hit-chart")).toBeTruthy();
    });
    fireEvent.click(screen.getByTestId("present-editor-block-hit-chart"));
    fireEvent.click(screen.getByTestId("present-editor-tab-layers"));
    fireEvent.change(screen.getByTestId("present-editor-props-chart-type"), { target: { value: "radar" } });
    expect(screen.getAllByTestId("present-editor-block-hit-chart")).toHaveLength(1);
    expect((screen.getByTestId("present-editor-props-chart-type") as HTMLSelectElement).value).toBe("radar");
  });

  it("opens Edit Data Table on double-click and saves into PPTX", async () => {
    render(<PresentEditor pptxPath={deckPath} variant="studio" />);
    await waitFor(() => {
      expect(screen.getByTestId("present-editor-tab-insert")).toBeTruthy();
    });
    fireEvent.click(screen.getByTestId("present-editor-tab-insert"));
    fireEvent.click(screen.getByTestId("present-editor-add-chart"));
    fireEvent.doubleClick(screen.getByTestId("present-editor-block-hit-chart"));
    expect(screen.getByTestId("present-edit-data-table")).toBeTruthy();
    fireEvent.change(screen.getByTestId("present-edit-data-type"), { target: { value: "radar" } });
    fireEvent.click(screen.getByTestId("present-edit-data-save"));
    await waitFor(() => {
      expect(mentrixPresentSaveNotes).toHaveBeenCalled();
    });
  });

  it("exposes every Presenton chart type on the palette", async () => {
    render(<PresentEditor pptxPath={deckPath} />);
    await waitFor(() => {
      expect(screen.getByTestId("present-editor-tab-charts")).toBeTruthy();
    });
    fireEvent.click(screen.getByTestId("present-editor-tab-charts"));
    for (const id of [
      "bar",
      "stacked",
      "stacked_horizontal",
      "line",
      "pie",
      "area",
      "donut",
      "scatter",
      "radar",
      "polar",
      "progress",
      "gauge",
    ]) {
      expect(screen.getByTestId(`present-editor-chart-${id}`)).toBeTruthy();
    }
  });

  it("positions overlay from EMU geometry and keeps data-block-id", async () => {
    vi.mocked(mentrixParsePptxFromPath).mockResolvedValueOnce({
      ok: true,
      count: 1,
      filename: "deck.pptx",
      slides: [
        {
          index: 0,
          text: "One",
          notes: "n1",
          blocks: [
            {
              id: "blk_0_chart_0",
              kind: "chart",
              geometry: { x: 914400, y: 514350, cx: 4000000, cy: 2500000 },
              content: { chart_type: "bar", categories: ["A", "B"], series: [{ name: "S", values: [1, 2] }] },
            },
          ],
        },
      ],
    });
    render(<PresentEditor pptxPath={deckPath} variant="studio" />);
    const hit = await screen.findByTestId("present-editor-block-hit-chart");
    expect(hit.getAttribute("data-block-id")).toBe("blk_0_chart_0");
    expect(hit.style.left).toBe("10%");
    expect(hit.style.position).toBe("absolute");
    expect(screen.getByTestId("present-editor-canvas").getAttribute("data-canvas")).toBe("document");
    expect(screen.getByTestId("present-editor-chart-glyph")).toBeTruthy();
    expect(screen.getByTestId("present-editor-block-overlay").className).not.toMatch(/grid-cols-2/);
  });

  it("scales overlay percents from parsed slide EMU size", async () => {
    vi.mocked(mentrixParsePptxFromPath).mockResolvedValueOnce({
      ok: true,
      count: 1,
      filename: "deck.pptx",
      slide_cx: 10000000,
      slide_cy: 5000000,
      slides: [
        {
          index: 0,
          text: "One",
          notes: "n1",
          blocks: [
            {
              id: "blk_0_chart_0",
              kind: "chart",
              geometry: { x: 1000000, y: 500000, cx: 2000000, cy: 1000000 },
              content: { chart_type: "bar", categories: ["A"], series: [{ name: "S", values: [1] }] },
            },
          ],
        },
      ],
    });
    render(<PresentEditor pptxPath={deckPath} variant="studio" />);
    const hit = await screen.findByTestId("present-editor-block-hit-chart");
    expect(hit.style.left).toBe("10%");
    expect(hit.style.top).toBe("10%");
    expect(hit.style.width).toBe("20%");
    expect(hit.style.height).toBe("20%");
  });

  it("exposes zoom fit and a layers panel", async () => {
    render(<PresentEditor pptxPath={deckPath} variant="studio" />);
    await waitFor(() => {
      expect(screen.getByTestId("present-editor-zoom-in")).toBeTruthy();
    });
    fireEvent.click(screen.getByTestId("present-editor-zoom-in"));
    expect(screen.getByTestId("present-editor-zoom-fit").textContent).toMatch(/110%/);
    fireEvent.click(screen.getByTestId("present-editor-tab-insert"));
    fireEvent.click(screen.getByTestId("present-editor-add-chart"));
    fireEvent.click(screen.getByTestId("present-editor-tab-layers"));
    fireEvent.click(screen.getByTestId("present-editor-advanced-toggle"));
    expect(screen.getByTestId("present-editor-layers")).toBeTruthy();
    expect(screen.getByTestId("present-editor-layer-chart")).toBeTruthy();
    expect(screen.getByTestId("present-editor-props")).toBeTruthy();
  });

  it("uses PNG preview for review and thumbs with template preview banner", async () => {
    render(<PresentEditor pptxPath={deckPath} />);
    await waitFor(() => {
      expect(screen.getByTestId("present-editor-slide-preview")).toBeTruthy();
    });
    expect(screen.getByTestId("present-editor-thumb-img-0")).toBeTruthy();
    expect(screen.queryByTestId("present-editor-canvas")).toBeFalsy();
  });
});
