import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("@/lib/api", () => ({
  mentrixCompanionIntegrations: vi.fn(async () => ({
    present_engine: false,
    present_engine_configured: false,
    present_engine_reachable: false,
  })),
  mentrixPresentGenerate: vi.fn(),
  mentrixPresentGenerationJob: vi.fn(async () => ({ ok: false })),
  mentrixPresentEngineStatus: vi.fn(async () => ({
    configured: false,
    reachable: false,
    base_url: "",
    lifecycle: "PROVIDER_UNAVAILABLE",
  })),
  mentrixPresentationAudiences: vi.fn(async () => ({ audiences: [] })),
  mentrixPresentationTemplates: vi.fn(async () => ({
    ok: true,
    zinnia: [],
    organization: [],
    my_templates: [],
  })),
  mentrixPreparePromptDeck: vi.fn(async (data: { prompt: string }) => ({
    ok: true,
    adapted_prompt: data.prompt,
    claims: [],
    requires_user_approval: false,
    sensitivity: { sensitivity: "PUBLIC" },
  })),
  mentrixAnalyzeDeck: vi.fn(),
  mentrixPresentationNarrateSlides: vi.fn(async (slides: Array<{ notes?: string; text?: string }>) => ({
    ok: true,
    slides: slides.map((s, i) => ({ index: i, script: (s.notes || s.text || `Slide ${i + 1}`).repeat(1), word_count: 12 })),
  })),
  mentrixPresentEngineTemplates: vi.fn(async () => ({
    ok: true,
    source: "builtin",
    templates: [
      { id: "general", name: "General" },
      { id: "modern", name: "Modern" },
      { id: "standard", name: "Standard" },
      { id: "swift", name: "Swift" },
    ],
  })),
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
  mentrixPresentationAssetUpload: vi.fn(async () => ({ ok: true, asset_id: "a1" })),
}));

vi.mock("@/mentrix/speak", () => ({
  cancelMentrixSpeech: vi.fn(),
  speakMentrix: vi.fn(),
  speakMentrixStreamedAwait: vi.fn(),
}));

import {
  mentrixCompanionIntegrations,
  mentrixPresentGenerate,
  mentrixPresentEngineStatus,
  mentrixPresentEngineTemplates,
  mentrixPresentationTemplates,
  mentrixVoiceEngineStatus,
} from "@/lib/api";
import PresentDeckPanel from "@/components/PresentDeckPanel";
import { MemoryRouter } from "react-router-dom";

describe("PresentDeckPanel clone narrate gate", () => {
  beforeEach(() => {
    localStorage.clear();
    (mentrixVoiceEngineStatus as ReturnType<typeof vi.fn>).mockReset();
    (mentrixPresentGenerate as ReturnType<typeof vi.fn>).mockReset();
    (mentrixCompanionIntegrations as ReturnType<typeof vi.fn>).mockResolvedValue({
      present_engine: false,
      present_engine_configured: false,
      present_engine_reachable: false,
    });
    (mentrixPresentEngineStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      configured: false,
      reachable: false,
      base_url: "",
      lifecycle: "PROVIDER_UNAVAILABLE",
    });
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

    render(
      <MemoryRouter>
        <PresentDeckPanel />
      </MemoryRouter>,
    );

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

    render(
      <MemoryRouter>
        <PresentDeckPanel />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("present-deck-engine-status").textContent).toMatch(/online/i);
    });
    expect(screen.getByTestId("present-deck-narrate")).not.toBeDisabled();
    expect(screen.getByTestId("present-deck-present-all")).not.toBeDisabled();
  });

  it("auto-selects a clone over leftover stock Echo", async () => {
    localStorage.setItem("zect_mentrix_present_deck_voice", "stock:echo");
    (mentrixVoiceEngineStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      online: true,
      base_url: "http://127.0.0.1:17493",
      default_voice: { voice_id: "v1", name: "Me", has_sample: true },
      hint: "online",
    });

    render(
      <MemoryRouter>
        <PresentDeckPanel />
      </MemoryRouter>,
    );

    await waitFor(() => {
      const sel = screen.getByTestId("present-deck-voice-select") as HTMLSelectElement;
      expect(sel.value).toBe("clone:v1");
    });
  });

  it("disables Generate deck when presentation engine is not configured", async () => {
    (mentrixVoiceEngineStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      online: true,
      base_url: "http://localhost:17493",
      default_voice: null,
      hint: "online",
    });
    (mentrixCompanionIntegrations as ReturnType<typeof vi.fn>).mockResolvedValue({
      present_engine: false,
      present_engine_configured: false,
      present_engine_reachable: false,
    });

    render(
      <MemoryRouter>
        <PresentDeckPanel mode="create" />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("present-deck-generate")).toBeDisabled();
    });
  });

  it("enables Generate when ZECT native provider is ready (no external Docker)", async () => {
    (mentrixVoiceEngineStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      online: true,
      base_url: "http://127.0.0.1:17493",
      default_voice: null,
      hint: "online",
    });
    (mentrixCompanionIntegrations as ReturnType<typeof vi.fn>).mockResolvedValue({
      present_engine: true,
      present_engine_configured: true,
      present_engine_reachable: true,
    });
    (mentrixPresentEngineStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      configured: true,
      reachable: true,
      base_url: "",
      lifecycle: "READY",
      provider: "zect_native",
    });

    render(
      <MemoryRouter>
        <PresentDeckPanel mode="create" />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("present-deck-generate")).not.toBeDisabled();
    });
  });

  it("shows BLOCKED_EXTERNAL and keeps Zinnia templates when engine is down", async () => {
    (mentrixVoiceEngineStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      online: true,
      base_url: "http://localhost:17493",
      default_voice: null,
      hint: "online",
    });
    (mentrixPresentEngineTemplates as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      reachable: false,
      templates: [],
    });
    (mentrixPresentationTemplates as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      zinnia: [{ id: "zinnia-executive-v1", name: "Zinnia — Executive brief", native_ready: true }],
      organization: [{ id: "org-brand", name: "Org brand", native_ready: true }],
      my_templates: [{ id: "user-my-deck", name: "My deck", native_ready: true }],
    });

    render(
      <MemoryRouter>
        <PresentDeckPanel mode="create" />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("present-lifecycle-state").textContent).toMatch(/BLOCKED_EXTERNAL/);
      const select = screen.getByTestId("present-deck-template") as HTMLSelectElement;
      const labels = [...select.options].map((o) => o.textContent || "");
      expect(labels.some((t) => /Zinnia/i.test(t))).toBe(true);
    });
    expect(screen.getByTestId("present-deck-generate")).toBeDisabled();
    const select = screen.getByTestId("present-deck-template") as HTMLSelectElement;
    const labels = [...select.options].map((o) => o.textContent || "");
    expect(labels.some((t) => /Zinnia/i.test(t))).toBe(true);
    expect(labels.some((t) => /Org brand/i.test(t))).toBe(true);
    expect(labels.some((t) => /My deck/i.test(t))).toBe(true);
    expect(labels.some((t) => /Custom template id/i.test(t))).toBe(false);
  });

  it("passes selected template and n_slides to generate", async () => {
    (mentrixVoiceEngineStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      online: true,
      base_url: "http://localhost:17493",
      default_voice: null,
      hint: "online",
    });
    (mentrixCompanionIntegrations as ReturnType<typeof vi.fn>).mockResolvedValue({
      present_engine: true,
      present_engine_configured: true,
      present_engine_reachable: true,
    });
    (mentrixPresentEngineStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      configured: true,
      reachable: true,
      base_url: "http://127.0.0.1:5000",
      lifecycle: "READY",
    });
    (mentrixPresentGenerate as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      path: "C:\\Users\\me\\Documents\\mentrix-deck.pptx",
    });

    render(
      <MemoryRouter>
        <PresentDeckPanel mode="create" />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("present-deck-generate")).not.toBeDisabled();
    });

    fireEvent.change(screen.getByTestId("present-deck-prompt"), {
      target: { value: "Q2 ZOAS delivery brief" },
    });
    fireEvent.change(screen.getByTestId("present-deck-template"), {
      target: { value: "modern" },
    });
    fireEvent.change(screen.getByTestId("present-deck-n-slides"), {
      target: { value: "8" },
    });
    fireEvent.click(screen.getByTestId("present-deck-generate"));

    await waitFor(() => {
      expect(mentrixPresentGenerate).toHaveBeenCalledWith(
        expect.objectContaining({
          content: "Q2 ZOAS delivery brief",
          template: "modern",
          n_slides: 8,
          language: "English",
          run_id: expect.any(String),
        }),
      );
    });
  });

  it("hides NOT_READY registry templates from generate dropdown", async () => {
    (mentrixVoiceEngineStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      online: true,
      base_url: "http://localhost:17493",
      default_voice: null,
      hint: "online",
    });
    (mentrixCompanionIntegrations as ReturnType<typeof vi.fn>).mockResolvedValue({
      present_engine: true,
      present_engine_configured: true,
      present_engine_reachable: true,
    });
    (mentrixPresentEngineStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      configured: true,
      reachable: true,
      base_url: "http://127.0.0.1:5000",
      lifecycle: "READY",
    });
    (mentrixPresentationTemplates as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      zinnia: [
        { id: "zinnia-executive-v1", name: "Zinnia — Executive brief", native_ready: true },
        { id: "zinnia-delivery-v1", name: "Zinnia — Delivery status", native_ready: false },
      ],
      organization: [],
      my_templates: [],
    });

    render(
      <MemoryRouter>
        <PresentDeckPanel mode="create" />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("present-deck-language")).toBeTruthy();
      expect(screen.getByTestId("present-deck-attach")).toBeTruthy();
    });
    const select = screen.getByTestId("present-deck-template") as HTMLSelectElement;
    const labels = [...select.options].map((o) => o.textContent || "");
    expect(labels.some((t) => /Executive/i.test(t))).toBe(true);
    expect(labels.some((t) => /Delivery/i.test(t))).toBe(false);
  });
});
