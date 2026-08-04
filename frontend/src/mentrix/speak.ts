/** Mentrix speech — cloned Chatterbox / OpenAI TTS fallback / browser speechSynthesis. */
import { getMyClonedVoice, mentrixSpeakClonedDetailed } from "@/lib/api";
import { chunkSpeakText } from "@/lib/mentrixRealtimeFinalize";

let lastAudio: HTMLAudioElement | null = null;
let awaitGeneration = 0;

export type SpeakResult = { ok: true; engine: string } | { ok: false; error: string };

export function cancelBrowserSpeech() {
  awaitGeneration += 1;
  try {
    window.speechSynthesis?.cancel();
  } catch {
    /* ignore */
  }
  try {
    lastAudio?.pause();
    if (lastAudio) {
      try {
        lastAudio.removeAttribute("src");
        lastAudio.load();
      } catch {
        /* ignore */
      }
    }
    lastAudio = null;
  } catch {
    /* ignore */
  }
}

/** Alias used by Present All Stop — same as cancelBrowserSpeech. */
export function cancelMentrixSpeech() {
  cancelBrowserSpeech();
}

function waitForAudioEnded(audio: HTMLAudioElement, gen: number): Promise<void> {
  return new Promise((resolve, reject) => {
    const done = () => {
      cleanup();
      if (lastAudio === audio) lastAudio = null;
      resolve();
    };
    const fail = () => {
      cleanup();
      if (lastAudio === audio) lastAudio = null;
      reject(new Error("audio playback error"));
    };
    const onCancelCheck = () => {
      if (gen !== awaitGeneration) {
        cleanup();
        if (lastAudio === audio) lastAudio = null;
        resolve(); // cancelled — resolve so callers can exit cleanly
      }
    };
    const cleanup = () => {
      audio.removeEventListener("ended", done);
      audio.removeEventListener("error", fail);
      window.clearInterval(iv);
    };
    audio.addEventListener("ended", done);
    audio.addEventListener("error", fail);
    const iv = window.setInterval(onCancelCheck, 100);
    if (audio.ended) done();
  });
}

function speakBrowserAwait(text: string): Promise<SpeakResult> {
  return new Promise((resolve) => {
    if (typeof window === "undefined" || !window.speechSynthesis) {
      resolve({ ok: false, error: "speechSynthesis unavailable" });
      return;
    }
    const gen = awaitGeneration;
    try {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text.slice(0, 500));
      u.rate = 1.05;
      const iv = window.setInterval(() => {
        if (gen !== awaitGeneration) {
          window.clearInterval(iv);
          try {
            window.speechSynthesis.cancel();
          } catch {
            /* ignore */
          }
          resolve({ ok: false, error: "cancelled" });
        }
      }, 100);
      u.onend = () => {
        window.clearInterval(iv);
        resolve({ ok: true, engine: "browser_speechSynthesis" });
      };
      u.onerror = () => {
        window.clearInterval(iv);
        resolve({ ok: false, error: "browser speech error" });
      };
      window.speechSynthesis.speak(u);
    } catch (e) {
      resolve({ ok: false, error: e instanceof Error ? e.message : "browser speech failed" });
    }
  });
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
    const { url, engine } = await mentrixSpeakClonedDetailed(text);
    if (url && typeof Audio !== "undefined") {
      const audio = new Audio(url);
      lastAudio = audio;
      try {
        await audio.play();
        return { ok: true, engine };
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

/**
 * Like speakMentrix but resolves only after playback finishes (or cancel/error).
 * Used by Present all slides so Right Arrow advances after narration ends.
 */
export async function speakMentrixAwait(text: string, enabled: boolean): Promise<SpeakResult> {
  if (!enabled) return { ok: false, error: "TTS is off — enable Speak replies / Speak status" };
  if (!text.trim()) return { ok: false, error: "Nothing to speak" };
  cancelBrowserSpeech();
  const gen = awaitGeneration;

  let apiError = "";
  try {
    const { url, engine } = await mentrixSpeakClonedDetailed(text);
    if (gen !== awaitGeneration) return { ok: false, error: "cancelled" };
    if (url && typeof Audio !== "undefined") {
      const audio = new Audio(url);
      lastAudio = audio;
      try {
        await audio.play();
        if (gen !== awaitGeneration) {
          cancelBrowserSpeech();
          return { ok: false, error: "cancelled" };
        }
        await waitForAudioEnded(audio, gen);
        if (gen !== awaitGeneration) return { ok: false, error: "cancelled" };
        return { ok: true, engine };
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

  if (gen !== awaitGeneration) return { ok: false, error: "cancelled" };

  try {
    if (typeof window !== "undefined" && window.speechSynthesis) {
      const result = await speakBrowserAwait(text);
      if (apiError && result.ok) {
        return {
          ok: false,
          error: `${apiError} (fell back to browser speech — may be silent in Electron)`,
        };
      }
      return result;
    }
  } catch {
    /* ignore */
  }

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

/**
 * Like speakMentrixAwait, but splits long text into sentence-sized chunks
 * (chunkSpeakText — the same helper the Realtime voice chat path already
 * uses) and prefetches the next chunk's audio while the current one plays.
 * Cuts time-to-first-audio for long text (e.g. a full slide's speaker
 * notes) from "however long the whole paragraph takes to synthesize" down
 * to "however long one sentence takes." Resolves once every chunk has
 * played, or as soon as cancelMentrixSpeech()/a later call bumps the
 * generation counter.
 */
export async function speakMentrixStreamedAwait(text: string, enabled: boolean): Promise<SpeakResult> {
  if (!enabled) return { ok: false, error: "TTS is off — enable Speak replies / Speak status" };
  const chunks = chunkSpeakText(text);
  if (!chunks.length) return { ok: false, error: "Nothing to speak" };
  if (chunks.length === 1) return speakMentrixAwait(chunks[0], enabled);

  cancelBrowserSpeech();
  const gen = awaitGeneration;
  const apiEngines = new Set<string>();
  let usedBrowserFallback = false;

  type ChunkAudio = { url: string; engine: string };
  const fetchChunk = (chunk: string): Promise<ChunkAudio | null> =>
    mentrixSpeakClonedDetailed(chunk).catch(() => null);

  let nextChunk: Promise<ChunkAudio | null> = fetchChunk(chunks[0]);
  for (let i = 0; i < chunks.length; i++) {
    if (gen !== awaitGeneration) return { ok: false, error: "cancelled" };
    const current = await nextChunk;
    const url = current?.url ?? null;
    let prefetched: Promise<ChunkAudio | null> | null = null;
    if (i + 1 < chunks.length) {
      prefetched = fetchChunk(chunks[i + 1]);
      nextChunk = prefetched;
    }
    if (gen !== awaitGeneration) {
      if (url) URL.revokeObjectURL(url);
      // Prefetch for the next chunk already started — don't leak its blob URL.
      prefetched?.then((c) => c?.url && URL.revokeObjectURL(c.url)).catch(() => undefined);
      return { ok: false, error: "cancelled" };
    }

    let played = false;
    if (url && typeof Audio !== "undefined") {
      const audio = new Audio(url);
      lastAudio = audio;
      try {
        await audio.play();
        if (gen !== awaitGeneration) {
          cancelBrowserSpeech();
          URL.revokeObjectURL(url);
          return { ok: false, error: "cancelled" };
        }
        await waitForAudioEnded(audio, gen);
        URL.revokeObjectURL(url);
        if (gen !== awaitGeneration) return { ok: false, error: "cancelled" };
        played = true;
        if (current) apiEngines.add(current.engine);
      } catch (playErr) {
        URL.revokeObjectURL(url);
        const msg = playErr instanceof Error ? playErr.message : String(playErr);
        if (/NotAllowedError|user interaction/i.test(msg)) {
          return {
            ok: false,
            error: "Browser blocked audio — click the page once, then Narrate / Speak again",
          };
        }
      }
    }

    if (!played) {
      // Per-chunk fallback: one bad chunk shouldn't derail the rest of the narration.
      if (typeof window === "undefined" || !window.speechSynthesis) {
        return { ok: false, error: "No audio output for this chunk — check TTS backend/Chatterbox/OpenAI" };
      }
      usedBrowserFallback = true;
      const result = await speakBrowserAwait(chunks[i]);
      if (gen !== awaitGeneration) return { ok: false, error: "cancelled" };
      if (!result.ok) return result;
    }
  }

  const engines = [...apiEngines, ...(usedBrowserFallback ? ["browser_speechSynthesis"] : [])];
  const engine = engines.length === 0
    ? "browser_speechSynthesis"
    : engines.length === 1
      ? engines[0]
      : `mixed(${engines.join("+")})`;
  return { ok: true, engine };
}
