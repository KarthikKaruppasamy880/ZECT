/** Mentrix speech — cloned Chatterbox / OpenAI TTS fallback / browser speechSynthesis. */
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

export type SpeakResult = { ok: true; engine: string } | { ok: false; error: string };

/**
 * Prefer Mentrix /voice/speak (Chatterbox clone or OpenAI TTS fallback); then speechSynthesis.
 * Throws / returns errors so UI can show why audio is silent.
 */
export async function speakMentrix(text: string, enabled: boolean): Promise<SpeakResult> {
  if (!enabled) return { ok: false, error: "TTS is off — enable Speak replies / Speak status" };
  if (!text.trim()) return { ok: false, error: "Nothing to speak" };
  cancelBrowserSpeech();

  let apiError = "";
  try {
    // Prefer API speak whenever possible (works with OpenAI fallback even without a clone).
    const url = await mentrixSpeakCloned(text);
    if (url && typeof Audio !== "undefined") {
      const audio = new Audio(url);
      lastAudio = audio;
      try {
        await audio.play();
        return { ok: true, engine: "mentrix_api" };
      } catch (playErr) {
        const msg = playErr instanceof Error ? playErr.message : String(playErr);
        if (/NotAllowedError|user interaction/i.test(msg)) {
          return {
            ok: false,
            error: "Browser blocked audio — click the page once, then Narrate / Speak again",
          };
        }
        apiError = msg || "audio.play failed";
      }
    }
  } catch (e) {
    apiError = e instanceof Error ? e.message : "Speak API failed";
  }

  // Browser TTS last resort (often silent in Electron)
  try {
    if (typeof window !== "undefined" && window.speechSynthesis) {
      speakBrowser(text, true);
      // If API failed, still report so operator knows clone/engine path failed
      if (apiError) {
        return {
          ok: false,
          error: `${apiError} (fell back to browser speech — may be silent in Electron)`,
        };
      }
      return { ok: true, engine: "browser_speechSynthesis" };
    }
  } catch {
    /* ignore */
  }

  // Last attempt: if we have a clone listed but speak failed, surface clone hint
  try {
    const voice = await getMyClonedVoice();
    if (!voice?.voice_id && apiError) {
      return {
        ok: false,
        error: `${apiError}. Tip: clone a voice in Companion → Voice, or ensure OPENAI_API_KEY for TTS fallback.`,
      };
    }
  } catch {
    /* ignore */
  }

  return { ok: false, error: apiError || "No audio output — check TTS toggle, backend, and Chatterbox/OpenAI" };
}
