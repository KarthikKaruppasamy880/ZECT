import { describe, expect, it } from "vitest";
import {
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
});
