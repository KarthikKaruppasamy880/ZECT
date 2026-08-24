import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

const { session } = vi.hoisted(() => ({
  session: {
    messages: [{ role: "assistant" as const, text: "I'm Mentrix — your company operator." }],
    setMessages: vi.fn(),
    input: "",
    setInput: vi.fn(),
    avatar: "idle" as const,
    setAvatar: vi.fn(),
    board: [],
    setBoard: vi.fn(),
    log: [{ ts: "1:00", text: "perf: transcript_final at +10ms" }],
    statusLine: "SYSTEMS OPERATIONAL",
    setStatusLine: vi.fn(),
    tts: true,
    setTts: vi.fn(),
    browserTtsEnabled: true,
    ttsPlayback: "playing" as "playing" | "silent-fallback" | "muted",
    voiceConnected: false,
    voiceConnecting: false,
    voiceTelemetry: { mode: "idle" as const, lastMark: "", lastMs: 0, ttsEngine: "" },
    computerMode: false,
    setComputerMode: vi.fn(),
    displayMode: false,
    setDisplayMode: vi.fn(),
    showArtifacts: true,
    setShowArtifacts: vi.fn(),
    pending: [],
    setPending: vi.fn(),
    turnId: "",
    loading: false,
    runsHint: "",
    streamReply: "",
    lastMessage: "",
    setLastMessageKeep: vi.fn(),
    lastProvenance: [],
    lastProgress: null,
    cancelTurn: vi.fn(),
    retryTurn: vi.fn(),
    realtimePreflight: { ready: true, model: "gpt-realtime" },
    micDevices: [],
    micDeviceId: "",
    setMicDeviceId: vi.fn(),
    speakerDevices: [],
    speakerDeviceId: "",
    setSpeakerDeviceId: vi.fn(),
    integrations: { slack: false, jira: false, openai: true, mentrix_local: false },
    dockExpanded: false,
    setDockExpanded: vi.fn(),
    wakeQueued: false,
    skills: [],
    activeSkillId: "",
    setActiveSkillId: vi.fn(),
    chatModel: "gpt-4o-mini",
    setChatModel: vi.fn(),
    pushLog: vi.fn(),
    refreshRealtimePreflight: vi.fn(),
    startVoice: vi.fn(),
    stopVoice: vi.fn(),
    toggleVoice: vi.fn(),
    runTurn: vi.fn(),
    onSend: vi.fn(),
    presentNarrate: vi.fn(),
    onAllow: vi.fn(),
    applyNavPath: vi.fn(),
    chatEndRef: { current: null },
  },
}));

vi.mock("@/mentrix/MentrixSessionContext", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/mentrix/MentrixSessionContext")>();
  return {
    ...actual,
    useMentrixSession: () => session,
  };
});

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    mentrixCompanionPolicy: vi.fn(),
    mentrixCompanionPolicyImport: vi.fn(),
  };
});

vi.mock("@/components/ModelSelector", () => ({
  default: () => <div data-testid="model-selector" />,
}));

vi.mock("@/components/MentrixDesktopPanel", () => ({
  default: () => <div data-testid="desktop-panel" />,
}));

vi.mock("@/components/CompanionScopeStrip", () => ({
  default: () => <div data-testid="companion-scope" />,
}));

import MentrixCompanion from "./MentrixCompanion";

describe("Mentrix Companion chat layout", () => {
  it("shows greeting and replies without opening the events log", () => {
    render(
      <MemoryRouter>
        <MentrixCompanion />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("mentrix-greeting")).toHaveTextContent("Good to see you");
    expect(screen.getByTestId("mentrix-companion-chat")).toHaveTextContent("I'm Mentrix");
    expect(screen.getByTestId("mentrix-avatar").className).toMatch(/h-28/);
    expect(screen.queryByTestId("mentrix-live-log")).toBeNull();
    fireEvent.click(screen.getByTestId("mentrix-companion-more"));
    fireEvent.click(screen.getByTestId("mentrix-events-toggle"));
    expect(screen.getByTestId("mentrix-live-log")).toHaveTextContent("perf:");
  });

  it("keeps greeting and replies when Display is on", () => {
    session.displayMode = true;
    render(
      <MemoryRouter>
        <MentrixCompanion />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("mentrix-greeting")).toBeTruthy();
    expect(screen.getByTestId("mentrix-companion-chat")).toHaveTextContent("I'm Mentrix");
    session.displayMode = false;
  });

  it("shows Speak replies as ready when idle, not MUTED", () => {
    session.tts = true;
    session.ttsPlayback = "muted";
    session.voiceConnected = false;
    render(
      <MemoryRouter>
        <MentrixCompanion />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("mentrix-tts-playback")).toHaveTextContent("ready");
    session.ttsPlayback = "playing";
  });

  it("reaches desktop launcher and artifacts without a desktop breakpoint", () => {
    session.showArtifacts = true;
    render(
      <MemoryRouter>
        <MentrixCompanion />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("mentrix-companion-artifacts")).toBeTruthy();
    expect(screen.getByTestId("mentrix-companion-artifacts").className).not.toMatch(/\bfixed\b/);
    expect(screen.getByTestId("mentrix-mode-voice")).toBeTruthy();
    fireEvent.click(screen.getByTestId("mentrix-mode-voice"));
    expect(screen.getByTestId("mentrix-voice-section")).toBeTruthy();
    fireEvent.click(screen.getByTestId("mentrix-mode-chat"));
    fireEvent.click(screen.getByTestId("mentrix-companion-more"));
    expect(screen.getByTestId("mentrix-companion-more-sheet")).toBeTruthy();
    expect(screen.getByTestId("mentrix-desktop-launcher-sheet")).toBeTruthy();
    expect(screen.getAllByTestId("desktop-panel").length).toBeGreaterThan(0);
  });

  it("hides artifacts until opened and keeps More on desktop", () => {
    session.showArtifacts = false;
    render(
      <MemoryRouter>
        <MentrixCompanion />
      </MemoryRouter>,
    );
    expect(screen.queryByTestId("mentrix-companion-artifacts")).toBeNull();
    expect(screen.getByTestId("mentrix-companion-more").className).not.toMatch(/md:hidden/);
    fireEvent.click(screen.getByTestId("mentrix-companion-more"));
    expect(screen.getByTestId("mentrix-companion-more-sheet").className).not.toMatch(/md:hidden/);
    session.showArtifacts = true;
  });
});
