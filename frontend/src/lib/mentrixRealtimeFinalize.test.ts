import { describe, expect, it } from "vitest";
import {
  chunkSpeakText,
  createPerfTracker,
  nextSpeakableSentence,
  shouldAppendAssistantTranscript,
  shouldFinalizeClonedResponse,
} from "./mentrixRealtimeFinalize";

describe("mentrixRealtimeFinalize", () => {
  it("skips transcript.done append when cloned voice is active", () => {
    expect(
      shouldAppendAssistantTranscript({
        clonedVoiceActive: true,
        eventType: "response.output_audio_transcript.done",
      }),
    ).toBe(false);
  });

  it("appends transcript.done when not using cloned voice", () => {
    expect(
      shouldAppendAssistantTranscript({
        clonedVoiceActive: false,
        eventType: "response.audio_transcript.done",
      }),
    ).toBe(true);
  });

  it("finalizes cloned response once per response id", () => {
    const finalizedIds = new Set<string>();
    expect(
      shouldFinalizeClonedResponse({
        clonedVoiceActive: true,
        responseId: "resp_1",
        finalizedIds,
      }),
    ).toBe(true);
    expect(
      shouldFinalizeClonedResponse({
        clonedVoiceActive: true,
        responseId: "resp_1",
        finalizedIds,
      }),
    ).toBe(false);
  });

  it("does not finalize cloned path when clone inactive", () => {
    expect(
      shouldFinalizeClonedResponse({
        clonedVoiceActive: false,
        responseId: "resp_1",
        finalizedIds: new Set(),
      }),
    ).toBe(false);
  });

  it("chunks long replies on sentence boundaries for faster first TTS", () => {
    const text =
      "First sentence is ready. Second sentence follows after. Third wraps up the answer cleanly.";
    const chunks = chunkSpeakText(text, 40);
    expect(chunks.length).toBeGreaterThan(1);
    expect(chunks[0]).toMatch(/First sentence/);
    expect(chunks.join(" ")).toContain("Third wraps");
  });

  it("keeps short replies as a single chunk", () => {
    expect(chunkSpeakText("Short reply.")).toEqual(["Short reply."]);
  });

  it("returns the first complete sentence and how much text it consumed", () => {
    const result = nextSpeakableSentence("First sentence is ready. Second is still streaming");
    expect(result?.sentence).toBe("First sentence is ready.");
    expect(result?.consumedLength).toBe("First sentence is ready. ".length);
  });

  it("returns null while the first sentence has not finished streaming yet", () => {
    expect(nextSpeakableSentence("Still typing the first sentence")).toBeNull();
  });

  it("returns null for empty or whitespace-only input", () => {
    expect(nextSpeakableSentence("")).toBeNull();
    expect(nextSpeakableSentence("   ")).toBeNull();
  });

  it("advancing by consumedLength repeatedly walks through every sentence with nothing skipped or duplicated", () => {
    const full = "First one. Second one! Third one? Trailing partial";
    let spokenUpTo = 0;
    const sentences: string[] = [];
    for (let guard = 0; guard < 10; guard++) {
      const next = nextSpeakableSentence(full.slice(spokenUpTo));
      if (!next) break;
      sentences.push(next.sentence);
      spokenUpTo += next.consumedLength;
    }
    expect(sentences).toEqual(["First one.", "Second one!", "Third one?"]);
    expect(full.slice(spokenUpTo)).toBe("Trailing partial");
  });

  describe("createPerfTracker", () => {
    it("records elapsed time since the last reset for each checkpoint", () => {
      let clock = 1000;
      const tracker = createPerfTracker(() => clock);
      tracker.reset();
      clock = 1295;
      expect(tracker.mark("llm_request_started")).toEqual({ name: "llm_request_started", elapsedMs: 295 });
      clock = 1500;
      expect(tracker.mark("llm_first_token")).toEqual({ name: "llm_first_token", elapsedMs: 500 });
    });

    it("only records the first occurrence of a given checkpoint per cycle", () => {
      let clock = 0;
      const tracker = createPerfTracker(() => clock);
      tracker.reset();
      clock = 100;
      expect(tracker.mark("llm_first_token")).not.toBeNull();
      clock = 900;
      // A second content delta shouldn't re-log or overwrite the first timing.
      expect(tracker.mark("llm_first_token")).toBeNull();
    });

    it("starts a fresh cycle on reset — same checkpoint name marks again", () => {
      let clock = 0;
      const tracker = createPerfTracker(() => clock);
      tracker.reset();
      clock = 50;
      tracker.mark("user_speech_stopped");
      clock = 1000;
      tracker.reset();
      clock = 1080;
      expect(tracker.mark("user_speech_stopped")).toEqual({ name: "user_speech_stopped", elapsedMs: 80 });
    });

    it("reports 0ms before the first reset instead of a huge/garbage elapsed value", () => {
      const tracker = createPerfTracker(() => 5000);
      expect(tracker.mark("user_speech_stopped")).toEqual({ name: "user_speech_stopped", elapsedMs: 0 });
    });
  });
});
