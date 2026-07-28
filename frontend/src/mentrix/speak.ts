/** Mentrix speech — browser TTS fallback or cloned Voicebox when available. */
import { getMyClonedVoice, mentrixSpeakCloned } from "@/lib/api";

let lastAudio: HTMLAudioElement | null = null;

export function cancelBrowserSpeech() {
  try {
    window.speechSynthesis?.cancel();
  } catch {
    /* ignore */
  }
  try {
    lastAudio?.pause();
    lastAudio = null;
  } catch {
    /* ignore */
  }
}

export function speakBrowser(text: string, enabled: boolean) {
  if (!enabled || typeof window === "undefined" || !window.speechSynthesis) return;
  try {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text.slice(0, 500));
    u.rate = 1.05;
    window.speechSynthesis.speak(u);
  } catch {
    /* ignore */
  }
}

/**
 * Prefer cloned Mentrix voice via /api/mentrix/voice/speak; fall back to speechSynthesis.
 */
export async function speakMentrix(text: string, enabled: boolean): Promise<void> {
  if (!enabled || !text.trim()) return;
  cancelBrowserSpeech();
  try {
    const voice = await getMyClonedVoice();
    if (voice?.voice_id) {
      const url = await mentrixSpeakCloned(text);
      if (url && typeof Audio !== "undefined") {
        const audio = new Audio(url);
        lastAudio = audio;
        await audio.play();
        return;
      }
    }
  } catch {
    /* fall through to browser TTS */
  }
  speakBrowser(text, true);
}
