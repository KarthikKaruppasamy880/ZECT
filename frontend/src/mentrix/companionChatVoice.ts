/** Companion chat TTS vs Realtime — one audio owner, silent-fallback. */

export const REALTIME_SILENCE_MS = 2500;

export type TtsPlaybackState = "playing" | "silent-fallback" | "muted";

/** Chip next to Speak replies — idle+on is ready, not MUTED. */
export function ttsPlaybackChip(opts: {
  ttsEnabled: boolean;
  ttsPlayback: TtsPlaybackState;
  voiceConnected?: boolean;
}): string {
  if (!opts.ttsEnabled) return "muted";
  if (opts.ttsPlayback === "playing") return "playing";
  if (opts.ttsPlayback === "silent-fallback") return "silent-fallback";
  if (opts.voiceConnected) return "realtime";
  return "ready";
}

export type ChatSpeakPlan =
  | { action: "muted" }
  | { action: "clone" }
  | { action: "realtime_wait"; silenceMs: number };

export function planChatSpeak(opts: {
  ttsEnabled: boolean;
  voiceConnected: boolean;
  hasRealtime: boolean;
}): ChatSpeakPlan {
  if (!opts.ttsEnabled) return { action: "muted" };
  if (opts.voiceConnected && opts.hasRealtime) {
    return { action: "realtime_wait", silenceMs: REALTIME_SILENCE_MS };
  }
  return { action: "clone" };
}

/** True when Realtime never started playback after the assistant text arrived. */
export function shouldSilentFallback(opts: {
  lastRealtimeAudioAt: number;
  startedAt: number;
  now: number;
  silenceMs?: number;
}): boolean {
  const budget = opts.silenceMs ?? REALTIME_SILENCE_MS;
  if (opts.lastRealtimeAudioAt >= opts.startedAt) return false;
  return opts.now - opts.startedAt >= budget;
}
