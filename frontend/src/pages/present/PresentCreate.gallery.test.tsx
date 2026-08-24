import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

vi.mock("@/components/PresentDeckPanel", () => ({
  default: () => <div data-testid="present-deck-panel" />,
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    mentrixPresentationTemplates: vi.fn(async () => ({
      zinnia: [
        {
          id: "zinnia-executive-v1",
          name: "Zinnia — Executive brief",
          native_ready: true,
          visual: { cover_data_url: "data:image/png;base64,aaa", ready: true, layout_names: ["Title"] },
        },
      ],
      organization: [{ id: "org-upload", name: "Org upload", native_ready: true, visual: { colors: ["#ff7500"] } }],
      my_templates: [],
    })),
    mentrixPresentonStatus: vi.fn(async () => ({
      lifecycle: "READY",
      configured: true,
      reachable: true,
    })),
    mentrixPresentationTemplatePreview: vi.fn(async () => ({ ok: true, name: "Exec", preview: "ok" })),
    mentrixPresentationTemplateUpload: vi.fn(),
    mentrixPresentationTemplateDelete: vi.fn(),
    mentrixPresentationDeleteUnmapped: vi.fn(),
  };
});

import PresentCreate from "./PresentCreate";
import PresentTemplateCardView from "./PresentTemplateCardView";

describe("Present template gallery", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("tabs Built-in Zinnia vs Custom uploads and shows a cover PNG", async () => {
    render(
      <MemoryRouter>
        <PresentCreate />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("zect-present-gallery-tabs")).toBeTruthy();
    });
    expect(screen.getByTestId("zect-present-tab-builtin")).toBeTruthy();
    const cover = screen.getByTestId("zect-present-template-zinnia-executive-v1-thumb");
    expect(cover.tagName).toBe("IMG");
    fireEvent.click(screen.getByTestId("zect-present-tab-custom"));
    expect(screen.getByTestId("zect-present-template-org-upload")).toBeTruthy();
    expect(screen.queryByTestId("zect-present-template-zinnia-executive-v1")).toBeNull();
  });
});

describe("PresentTemplateCardView cover vs swatch", () => {
  it("renders a cover image when cover_data_url is set", () => {
    render(
      <MemoryRouter>
        <PresentTemplateCardView
          tmpl={{
            id: "zinnia-executive-v1",
            name: "Exec",
            visual: { cover_data_url: "data:image/png;base64,xx" },
          }}
          selected={false}
          testId="gallery-cover"
          onSelect={() => undefined}
        />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("gallery-cover-thumb").tagName).toBe("IMG");
  });

  it("falls back to color swatches without a cover", () => {
    render(
      <MemoryRouter>
        <PresentTemplateCardView
          tmpl={{ id: "user-upload", name: "Mine", visual: { colors: ["#0f766e", "#ff7500"] } }}
          selected={false}
          testId="gallery-swatch"
          onSelect={() => undefined}
        />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("gallery-swatch-thumb").tagName).toBe("DIV");
  });
});
