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

/**
 * Split assistant text into speakable chunks so /voice/speak can start
 * synthesizing the first sentence immediately (lower time-to-first-audio).
 */
export function chunkSpeakText(text: string, maxChars = 220): string[] {
  const cleaned = text.replace(/\s+/g, " ").trim();
  if (!cleaned) return [];
  if (cleaned.length <= maxChars) return [cleaned];

  const sentences = cleaned.match(/[^.!?]+[.!?]+(?:\s+|$)|[^.!?]+$/g) || [cleaned];
  const parts: string[] = [];
  let buf = "";

  const pushHardWrap = (piece: string) => {
    for (let i = 0; i < piece.length; i += maxChars) {
      const slice = piece.slice(i, i + maxChars).trim();
      if (slice) parts.push(slice);
    }
  };

  for (const raw of sentences) {
    const piece = raw.trim();
    if (!piece) continue;
    const next = buf ? `${buf} ${piece}` : piece;
    if (next.length <= maxChars) {
      buf = next;
      continue;
    }
    if (buf) parts.push(buf);
    if (piece.length <= maxChars) {
      buf = piece;
    } else {
      pushHardWrap(piece);
      buf = "";
    }
  }
  if (buf) parts.push(buf);
  return parts;
}
