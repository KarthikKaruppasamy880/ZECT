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

  /** Prefer word boundaries so TTS does not jump mid-word between chunks. */
  const pushHardWrap = (piece: string) => {
    let rest = piece.trim();
    while (rest.length > maxChars) {
      let cut = rest.lastIndexOf(" ", maxChars);
      if (cut < Math.floor(maxChars * 0.4)) cut = maxChars;
      const slice = rest.slice(0, cut).trim();
      if (slice) parts.push(slice);
      rest = rest.slice(cut).trim();
    }
    if (rest) parts.push(rest);
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

/**
 * First complete sentence at the start of `unspoken` (streaming assistant
 * text not yet dispatched to speech), or null if no sentence boundary has
 * arrived yet. Lets the realtime cloned-voice path start synthesizing each
 * sentence the instant it streams in, instead of the whole reply waiting
 * for the LLM to finish generating before any TTS call fires at all.
 */
/**
 * Named-checkpoint latency tracker for one user turn (user_speech_stopped
 * through playback_finished). reset() marks t0 (called at
 * input_audio_buffer.speech_stopped — the point "response time" is actually
 * measured from). mark() records the FIRST occurrence of a given name since
 * the last reset — later repeats (e.g. llm_first_token semantics only apply
 * once, but a handler may fire per-delta) return null instead of re-logging.
 */
export type PerfMark = { name: string; elapsedMs: number };

export function createPerfTracker(now: () => number = () => performance.now()) {
  let t0 = 0;
  const seen = new Set<string>();
  return {
    reset(): void {
      t0 = now();
      seen.clear();
    },
    mark(name: string): PerfMark | null {
      if (seen.has(name)) return null;
      seen.add(name);
      return { name, elapsedMs: t0 ? Math.round(now() - t0) : 0 };
    },
  };
}

export function nextSpeakableSentence(unspoken: string): { sentence: string; consumedLength: number } | null {
  const match = unspoken.match(/^[\s\S]*?[.!?](?:\s|$)/);
  if (!match) return null;
  const sentence = match[0].trim();
  if (!sentence) return null;
  return { sentence, consumedLength: match[0].length };
}

/**
 * Trailing clone TTS after response.done must use streamed clonedTextAcc, not
 * rejoined response.output text (that string can differ and re-speak the whole reply).
 */
export function clonedRemainderToSpeak(clonedTextAcc: string, clonedSpokenUpTo: number): string {
  if (clonedSpokenUpTo >= clonedTextAcc.length) return "";
  return clonedTextAcc.slice(Math.max(0, clonedSpokenUpTo)).trim();
}
