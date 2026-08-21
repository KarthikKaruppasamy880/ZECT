import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import MentrixConfirmModal from "./MentrixConfirmModal";

describe("MentrixConfirmModal", () => {
  beforeEach(() => {
    vi.stubGlobal("speechSynthesis", {
      cancel: vi.fn(),
      speak: vi.fn(),
    });
  });

  it("does not speak when speakPrompt is false (single TTS owner)", () => {
    render(
      <MentrixConfirmModal
        open
        items={[{ tool: "desktop_list_dir", reason: "List Desktop" }]}
        speakPrompt={false}
        onAllow={vi.fn()}
        onDeny={vi.fn()}
      />,
    );
    expect(screen.getByTestId("mentrix-confirm-modal")).toBeInTheDocument();
    expect(window.speechSynthesis.speak).not.toHaveBeenCalled();
  });
});
