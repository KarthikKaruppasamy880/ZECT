import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  mentrixSpeakClonedDetailed: vi.fn(),
  getMyClonedVoice: vi.fn(async () => ({ voice_id: "v1" })),
}));

import { mentrixSpeakClonedDetailed } from "@/lib/api";
import { cancelMentrixSpeech, speakMentrixStreamedAwait } from "./speak";

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

  it("reports mixed when chunks come back from different engines", async () => {
    const s1 = "A".repeat(150) + ".";
    const s2 = "B".repeat(150) + ".";
    const text = `${s1} ${s2}`;
    (mentrixSpeakClonedDetailed as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({ url: "blob:chunk-0", engine: "chatterbox" })
      .mockResolvedValueOnce({ url: "blob:chunk-1", engine: "openai_tts_fallback" });

    const result = await speakMentrixStreamedAwait(text, true);

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
});
