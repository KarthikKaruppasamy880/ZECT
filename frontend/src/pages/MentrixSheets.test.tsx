import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("@/lib/api", () => ({
  mentrixSheetsGenerate: vi.fn(async () => ({
    ok: true,
    workbook: {
      sheets: [
        {
          name: "Sheet1",
          cells: { A1: { v: "a" }, B1: { v: "b" }, C1: { v: "c" }, A2: { v: "d" }, B2: { v: "e" }, C2: { v: "f" } },
        },
      ],
    },
  })),
  mentrixSheetsImport: vi.fn(),
  mentrixSheetsExport: vi.fn(),
}));

import MentrixSheets from "./MentrixSheets";
import { mentrixSheetsGenerate } from "@/lib/api";

describe("Mentrix Sheets", () => {
  it("fills a mocked 2x3 grid from chat generate", async () => {
    render(<MentrixSheets />);
    fireEvent.change(screen.getByTestId("mentrix-sheets-prompt"), {
      target: { value: "Make a 2x3 status grid" },
    });
    fireEvent.click(screen.getByTestId("mentrix-sheets-generate"));
    await waitFor(() => expect(mentrixSheetsGenerate).toHaveBeenCalled());
    expect(screen.getByTestId("mentrix-sheets-cell-A1")).toHaveValue("a");
    expect(screen.getByTestId("mentrix-sheets-cell-C2")).toHaveValue("f");
  });
});
