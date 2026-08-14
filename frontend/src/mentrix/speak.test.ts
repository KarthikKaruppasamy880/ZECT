import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  mentrixSpeakClonedDetailed: vi.fn(),
  getMyClonedVoice: vi.fn(async () => ({ voice_id: "v1" })),
}));

import { mentrixSpeakClonedDetailed } from "@/lib/api";
import {
  cancelMentrixSpeech,
  playMentrixPrefetch,
  requireCloneSpeech,
  speakMentrixAwait,
  speakMentrixStreamedAwait,
} from "./speak";

class FakeAudio extends EventTarget {
  ended = false;
  src: string;
  constructor(src?: string) {
    super();
    this.src = src || "";
  }
  play() {
    queueMicrotask(() => {
      this.ended = true;
      this.dispatchEvent(new Event("ended"));
    });
    return Promise.resolve();
  }
  pause() {
    /* no-op */
  }
  removeAttribute() {
    /* no-op */
  }
  load() {
    /* no-op */
  }
}

function deferred<T>() {
  let resolve!: (v: T) => void;
  const promise = new Promise<T>((r) => {
    resolve = r;
  });
  return { promise, resolve };
}

describe("requireCloneSpeech", () => {
  it("defaults to true for clone path", () => {
    expect(requireCloneSpeech(undefined)).toBe(true);
    expect(requireCloneSpeech({ requireClone: true })).toBe(true);
    expect(requireCloneSpeech({ voiceId: "v1" })).toBe(true);
  });

  it("is false for stock voice or explicit opt-out", () => {
    expect(requireCloneSpeech({ stockVoice: "nova" })).toBe(false);
    expect(requireCloneSpeech({ requireClone: false })).toBe(false);
  });
});

describe("speakMentrixStreamedAwait", () => {
  beforeEach(() => {
    vi.stubGlobal("Audio", FakeAudio as unknown as typeof Audio);
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => "blob:fake"),
      revokeObjectURL: vi.fn(),
    });
    (mentrixSpeakClonedDetailed as ReturnType<typeof vi.fn>).mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("delegates a single short chunk straight to the non-chunked path", async () => {
    (mentrixSpeakClonedDetailed as ReturnType<typeof vi.fn>).mockResolvedValue({ url: "blob:chunk-0", engine: "chatterbox" });

    const result = await speakMentrixStreamedAwait("Short reply.", true);

    expect(result).toEqual({ ok: true, engine: "chatterbox" });
    expect(mentrixSpeakClonedDetailed).toHaveBeenCalledTimes(1);
    expect(mentrixSpeakClonedDetailed).toHaveBeenCalledWith("Short reply.", undefined);
  });

  it("threads an explicit voice choice (e.g. a stock voice for presenting) through to every chunk", async () => {
    const s1 = "A".repeat(150) + ".";
    const s2 = "B".repeat(150) + ".";
    (mentrixSpeakClonedDetailed as ReturnType<typeof vi.fn>).mockResolvedValue({ url: "blob:x", engine: "openai_stock:nova" });

    await speakMentrixStreamedAwait(`${s1} ${s2}`, true, { stockVoice: "nova" });

    expect(mentrixSpeakClonedDetailed).toHaveBeenCalledTimes(2);
    for (const call of (mentrixSpeakClonedDetailed as ReturnType<typeof vi.fn>).mock.calls) {
      expect(call[1]).toEqual({ stockVoice: "nova" });
    }
  });

  it("surfaces the real error when an explicitly chosen voice fails, instead of silently falling back to browser speech", async () => {
    const s1 = "A".repeat(150) + ".";
    const s2 = "B".repeat(150) + ".";
    (mentrixSpeakClonedDetailed as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("stock_voice must be one of (...)"),
    );

    const result = await speakMentrixStreamedAwait(`${s1} ${s2}`, true, { stockVoice: "bogus" });

    expect(result).toEqual({ ok: false, error: "Selected voice failed: stock_voice must be one of (...)" });
  });

  it("splits long text into chunks and plays each via the reported engine in order", async () => {
    const s1 = "A".repeat(150) + ".";
    const s2 = "B".repeat(150) + ".";
    const s3 = "C".repeat(150) + ".";
    const text = `${s1} ${s2} ${s3}`;
    (mentrixSpeakClonedDetailed as ReturnType<typeof vi.fn>).mockImplementation(async (chunk: string) => ({
      url: `blob:${chunk.slice(0, 1)}`,
      engine: "chatterbox",
    }));

    const result = await speakMentrixStreamedAwait(text, true);

    expect(result).toEqual({ ok: true, engine: "chatterbox" });
    expect(mentrixSpeakClonedDetailed).toHaveBeenCalledTimes(3);
    expect((mentrixSpeakClonedDetailed as ReturnType<typeof vi.fn>).mock.calls.map((c) => c[0][0])).toEqual(["A", "B", "C"]);
  });

  it("rejects non-chatterbox engines on the default clone path (no silent mixed fallback)", async () => {
    const s1 = "A".repeat(150) + ".";
    const s2 = "B".repeat(150) + ".";
    const text = `${s1} ${s2}`;
    (mentrixSpeakClonedDetailed as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({ url: "blob:chunk-0", engine: "chatterbox" })
      .mockResolvedValueOnce({ url: "blob:chunk-1", engine: "openai_tts_fallback" });

    const result = await speakMentrixStreamedAwait(text, true);

    expect(result).toEqual({
      ok: false,
      error: "Expected your clone (ZECT Voicebox), got openai_tts_fallback — start local ZECT Voicebox",
    });
  });

  it("accepts zect_voicebox engine id as clone success", async () => {
    (mentrixSpeakClonedDetailed as ReturnType<typeof vi.fn>).mockResolvedValue({
      url: "blob:ok",
      engine: "zect_voicebox",
    });
    const result = await speakMentrixAwait("Hello there.", true);
    expect(result).toEqual({ ok: true, engine: "zect_voicebox" });
  });

  it("allows mixed engines when requireClone is false", async () => {
    const s1 = "A".repeat(150) + ".";
    const s2 = "B".repeat(150) + ".";
    const text = `${s1} ${s2}`;
    (mentrixSpeakClonedDetailed as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({ url: "blob:chunk-0", engine: "chatterbox" })
      .mockResolvedValueOnce({ url: "blob:chunk-1", engine: "openai_tts_fallback" });

    const result = await speakMentrixStreamedAwait(text, true, { requireClone: false });

    expect(result).toEqual({ ok: true, engine: "mixed(chatterbox+openai_tts_fallback)" });
  });
  it("returns off when disabled without calling the API", async () => {
    const result = await speakMentrixStreamedAwait("Some text.", false);

    expect(result.ok).toBe(false);
    expect(mentrixSpeakClonedDetailed).not.toHaveBeenCalled();
  });

  it("stops mid-narration when cancelMentrixSpeech is called before the first chunk resolves", async () => {
    const s1 = "A".repeat(150) + ".";
    const s2 = "B".repeat(150) + ".";
    const gate = deferred<{ url: string; engine: string }>();
    (mentrixSpeakClonedDetailed as ReturnType<typeof vi.fn>)
      .mockImplementationOnce(() => gate.promise)
      // The pipeline prefetches chunk 2 as soon as chunk 1 resolves, before
      // checking cancellation — real mentrixSpeakClonedDetailed always
      // returns a Promise, so give this call a resolved one too.
      .mockResolvedValue({ url: "blob:chunk-1", engine: "chatterbox" });

    const resultPromise = speakMentrixStreamedAwait(`${s1} ${s2}`, true);
    cancelMentrixSpeech();
    gate.resolve({ url: "blob:chunk-0", engine: "chatterbox" });
    const result = await resultPromise;

    expect(result).toEqual({ ok: false, error: "cancelled" });
    expect(mentrixSpeakClonedDetailed).toHaveBeenCalledTimes(2);
  });

  it("does not start the next slide's playback until the current audio has ended", async () => {
    const playing: number[] = [];
    const maxConcurrent: number[] = [];
    class GatedAudio extends EventTarget {
      src: string;
      constructor(src?: string) {
        super();
        this.src = src || "";
      }
      play() {
        playing.push(1);
        maxConcurrent.push(playing.length);
        return Promise.resolve();
      }
      pause() {
        /* no-op */
      }
      removeAttribute() {
        /* no-op */
      }
      load() {
        /* no-op */
      }
      endNow() {
        playing.pop();
        this.dispatchEvent(new Event("ended"));
      }
    }
    const instances: GatedAudio[] = [];
    vi.stubGlobal(
      "Audio",
      function Audio(src?: string) {
        const a = new GatedAudio(src);
        instances.push(a);
        return a;
      } as unknown as typeof Audio,
    );

    const run = playMentrixPrefetch(
      [
        { url: "blob:slide-1", engine: "zect_voicebox" },
        { url: "blob:slide-2", engine: "zect_voicebox" },
      ],
      { requireClone: true },
    );
    await Promise.resolve();
    expect(instances.length).toBe(1);
    expect(Math.max(0, ...maxConcurrent)).toBe(1);
    instances[0].endNow();
    await Promise.resolve();
    await Promise.resolve();
    expect(instances.length).toBe(2);
    instances[1].endNow();
    const result = await run;
    expect(result.ok).toBe(true);
    expect(Math.max(...maxConcurrent)).toBe(1);
  });
});
