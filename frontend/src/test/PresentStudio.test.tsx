import { MemoryRouter, Route, Routes } from "react-router-dom";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PresentStudio from "@/pages/present/PresentStudio";

vi.mock("@/components/PresentEditor", () => ({
  default: ({ pptxPath, variant }: { pptxPath: string; variant?: string }) => (
    <div data-testid="present-editor" data-path={pptxPath} data-variant={variant} />
  ),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    decodeDeckId: (id: string) => (id === "missing" ? "" : "C:\\Users\\me\\Documents\\deck.pptx"),
  };
});

describe("PresentStudio", () => {
  it("renders the dedicated Studio route with the editor", () => {
    render(
      <MemoryRouter initialEntries={["/present/d/abc/edit"]}>
        <Routes>
          <Route path="/present/d/:deckId/edit" element={<PresentStudio />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("present-studio")).toBeTruthy();
    expect(screen.getByTestId("present-editor")).toHaveAttribute("data-variant", "studio");
    expect(screen.getByTestId("present-studio-review-link")).toHaveAttribute("href", "/present/d/abc");
  });
});
