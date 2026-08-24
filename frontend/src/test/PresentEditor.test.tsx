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
  mentrixPresentationAssetBlob: vi.fn(),
}));

import PresentEditor from "@/components/PresentEditor";
import { mentrixParsePptxFromPath, mentrixPresentSaveNotes } from "@/lib/api";

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
    render(<PresentEditor pptxPath="C:\\Users\\me\\Documents\\deck.pptx" />);
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
    expect(screen.getByTestId("present-editor-tab-blocks")).toBeTruthy();
    expect(screen.getByTestId("present-editor-tab-texts")).toBeTruthy();
    expect(screen.getByTestId("present-editor-tab-charts")).toBeTruthy();
    expect(screen.getByTestId("present-editor-tab-tables")).toBeTruthy();
    expect(screen.getByTestId("present-editor-tab-images")).toBeTruthy();
    expect(screen.getByTestId("present-editor-tab-elements")).toBeTruthy();
    expect(screen.getByTestId("present-editor-canvas")).toBeTruthy();
    expect(screen.getByTestId("present-editor-ai-intro")).toBeTruthy();
  });

  it("toasts that Save is required after adding a chart", async () => {
    render(<PresentEditor pptxPath="C:\\Users\\me\\Documents\\deck.pptx" />);
    await waitFor(() => {
      expect(screen.getByTestId("present-editor-tab-charts")).toBeTruthy();
    });
    fireEvent.click(screen.getByTestId("present-editor-tab-charts"));
    fireEvent.click(screen.getByTestId("present-editor-add-chart"));
    expect(screen.getByTestId("present-editor-status").textContent).toMatch(/Save to persist/i);
  });

  it("changes selected chart type to radar instead of appending another stub", async () => {
    render(<PresentEditor pptxPath="C:\\Users\\me\\Documents\\deck.pptx" />);
    await waitFor(() => {
      expect(screen.getByTestId("present-editor-tab-charts")).toBeTruthy();
    });
    fireEvent.click(screen.getByTestId("present-editor-tab-charts"));
    fireEvent.click(screen.getByTestId("present-editor-add-chart"));
    await waitFor(() => {
      expect(screen.getByTestId("present-editor-block-hit-chart")).toBeTruthy();
    });
    fireEvent.click(screen.getByTestId("present-editor-block-hit-chart"));
    fireEvent.click(screen.getByTestId("present-editor-chart-radar"));
    expect(screen.getByTestId("present-editor-status").textContent).toMatch(/Chart type changed to Radar/i);
    expect(screen.getAllByTestId("present-editor-block-hit-chart")).toHaveLength(1);
  });

  it("opens Edit Data Table on double-click and saves into PPTX", async () => {
    render(<PresentEditor pptxPath="C:\\Users\\me\\Documents\\deck.pptx" />);
    await waitFor(() => {
      expect(screen.getByTestId("present-editor-tab-charts")).toBeTruthy();
    });
    fireEvent.click(screen.getByTestId("present-editor-tab-charts"));
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
    render(<PresentEditor pptxPath="C:\\Users\\me\\Documents\\deck.pptx" variant="studio" />);
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
    render(<PresentEditor pptxPath="C:\\Users\\me\\Documents\\deck.pptx" />);
    const hit = await screen.findByTestId("present-editor-block-hit-chart");
    expect(hit.getAttribute("data-block-id")).toBe("blk_0_chart_0");
    expect(hit.style.left).toBe("10%");
    expect(hit.style.position).toBe("absolute");
    expect(hit.className).toMatch(/bg-transparent/);
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
    render(<PresentEditor pptxPath="C:\\Users\\me\\Documents\\deck.pptx" />);
    const hit = await screen.findByTestId("present-editor-block-hit-chart");
    expect(hit.style.left).toBe("10%");
    expect(hit.style.top).toBe("10%");
    expect(hit.style.width).toBe("20%");
    expect(hit.style.height).toBe("20%");
  });
});
