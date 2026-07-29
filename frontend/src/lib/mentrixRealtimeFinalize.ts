/**
 * Pure helpers for Realtime assistant finalize (unit-tested).
 * Prevents double bubble / double speak on long cloned-voice replies.
 */

export function shouldAppendAssistantTranscript(opts: {
  clonedVoiceActive: boolean;
  eventType: string;
}): boolean {
  if (opts.clonedVoiceActive) return false;
  return (
    opts.eventType === "response.output_audio_transcript.done" ||
    opts.eventType === "response.audio_transcript.done"
  );
}

export function shouldFinalizeClonedResponse(opts: {
  clonedVoiceActive: boolean;
  responseId: string;
  finalizedIds: Set<string>;
}): boolean {
  if (!opts.clonedVoiceActive) return false;
  if (!opts.responseId) return true;
  if (opts.finalizedIds.has(opts.responseId)) return false;
  opts.finalizedIds.add(opts.responseId);
  return true;
}
