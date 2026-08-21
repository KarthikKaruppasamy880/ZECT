import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("@/lib/api", () => ({
  mentrixAnalyzeDeck: vi.fn(async () => ({ improved_notes: [] })),
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
  mentrixPresentSlidePreview: vi.fn(async () => "blob:preview"),
  mentrixPresentationAssetUpload: vi.fn(),
  mentrixPresentationAssetBlob: vi.fn(),
}));

import PresentEditor from "@/components/PresentEditor";
import { mentrixPresentSaveNotes } from "@/lib/api";

describe("PresentEditor v1", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
});
