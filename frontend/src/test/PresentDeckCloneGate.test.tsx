import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

vi.mock("@/lib/api", () => ({
  mentrixCompanionIntegrations: vi.fn(async () => ({ presenton: false })),
  mentrixPresentonGenerate: vi.fn(),
  mentrixParsePptx: vi.fn(),
  listMyClonedVoices: vi.fn(async () => [
    {
      voice_id: "v1",
      name: "Me",
      provider: "chatterbox",
      is_default: true,
      has_sample: true,
      engine_ready: false,
    },
  ]),
  mentrixVoiceEngineStatus: vi.fn(),
}));

vi.mock("@/mentrix/speak", () => ({
  cancelMentrixSpeech: vi.fn(),
  speakMentrix: vi.fn(),
  speakMentrixStreamedAwait: vi.fn(),
}));

import { mentrixVoiceEngineStatus } from "@/lib/api";
import PresentDeckPanel from "@/components/PresentDeckPanel";

describe("PresentDeckPanel clone narrate gate", () => {
  beforeEach(() => {
    (mentrixVoiceEngineStatus as ReturnType<typeof vi.fn>).mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("disables narrate when Chatterbox is offline and clone is selected", async () => {
    (mentrixVoiceEngineStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      online: false,
      base_url: "http://localhost:17493",
      default_voice: { voice_id: "v1", name: "Me", has_sample: true },
      hint: "Start local Chatterbox",
    });

    render(<PresentDeckPanel />);

    await waitFor(() => {
      expect(screen.getByTestId("present-deck-engine-status").textContent).toMatch(/offline/i);
    });
    expect(screen.getByTestId("present-deck-narrate")).toBeDisabled();
    expect(screen.getByTestId("present-deck-present-all")).toBeDisabled();
  });

  it("keeps narrate enabled when Chatterbox is online", async () => {
    (mentrixVoiceEngineStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      online: true,
      base_url: "http://localhost:17493",
      default_voice: { voice_id: "v1", name: "Me", has_sample: true },
      hint: "online",
    });

    render(<PresentDeckPanel />);

    await waitFor(() => {
      expect(screen.getByTestId("present-deck-engine-status").textContent).toMatch(/online/i);
    });
    expect(screen.getByTestId("present-deck-narrate")).not.toBeDisabled();
    expect(screen.getByTestId("present-deck-present-all")).not.toBeDisabled();
  });
});
