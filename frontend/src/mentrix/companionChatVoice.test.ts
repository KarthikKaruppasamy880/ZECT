import { describe, expect, it } from "vitest";
import { planChatSpeak, shouldSilentFallback, REALTIME_SILENCE_MS } from "./companionChatVoice";

describe("planChatSpeak", () => {
  it("is muted when Speak replies is off", () => {
    expect(planChatSpeak({ ttsEnabled: false, voiceConnected: true, hasRealtime: true })).toEqual({
      action: "muted",
    });
  });

  it("uses clone TTS when Voice is disconnected", () => {
    expect(planChatSpeak({ ttsEnabled: true, voiceConnected: false, hasRealtime: false })).toEqual({
      action: "clone",
    });
  });

  it("waits on Realtime when Voice is connected", () => {
    expect(planChatSpeak({ ttsEnabled: true, voiceConnected: true, hasRealtime: true })).toEqual({
      action: "realtime_wait",
      silenceMs: REALTIME_SILENCE_MS,
    });
  });
});

describe("shouldSilentFallback", () => {
  it("falls back when no audio arrived in the silence window", () => {
    expect(
      shouldSilentFallback({ lastRealtimeAudioAt: 0, startedAt: 1000, now: 1000 + REALTIME_SILENCE_MS, silenceMs: REALTIME_SILENCE_MS }),
    ).toBe(true);
  });

  it("does not fall back when Realtime started playback after the reply", () => {
    expect(
      shouldSilentFallback({ lastRealtimeAudioAt: 1500, startedAt: 1000, now: 4000, silenceMs: REALTIME_SILENCE_MS }),
    ).toBe(false);
  });
});
