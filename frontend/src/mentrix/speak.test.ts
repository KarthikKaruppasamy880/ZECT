import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  mentrixSpeakCloned: vi.fn(),
  getMyClonedVoice: vi.fn(async () => ({ voice_id: "v1" })),
}));

import { mentrixSpeakCloned } from "@/lib/api";
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
    (mentrixSpeakCloned as ReturnType<typeof vi.fn>).mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("delegates a single short chunk straight to the non-chunked path", async () => {
    (mentrixSpeakCloned as ReturnType<typeof vi.fn>).mockResolvedValue("blob:chunk-0");

    const result = await speakMentrixStreamedAwait("Short reply.", true);

    expect(result).toEqual({ ok: true, engine: "mentrix_api" });
    expect(mentrixSpeakCloned).toHaveBeenCalledTimes(1);
    expect(mentrixSpeakCloned).toHaveBeenCalledWith("Short reply.");
  });

  it("splits long text into chunks and plays each via mentrix_api in order", async () => {
    const s1 = "A".repeat(150) + ".";
    const s2 = "B".repeat(150) + ".";
    const s3 = "C".repeat(150) + ".";
    const text = `${s1} ${s2} ${s3}`;
    (mentrixSpeakCloned as ReturnType<typeof vi.fn>).mockImplementation(async (chunk: string) => `blob:${chunk.slice(0, 1)}`);

    const result = await speakMentrixStreamedAwait(text, true);

    expect(result).toEqual({ ok: true, engine: "mentrix_api" });
    expect(mentrixSpeakCloned).toHaveBeenCalledTimes(3);
    expect((mentrixSpeakCloned as ReturnType<typeof vi.fn>).mock.calls.map((c) => c[0][0])).toEqual(["A", "B", "C"]);
  });

  it("returns off when disabled without calling the API", async () => {
    const result = await speakMentrixStreamedAwait("Some text.", false);

    expect(result.ok).toBe(false);
    expect(mentrixSpeakCloned).not.toHaveBeenCalled();
  });

  it("stops mid-narration when cancelMentrixSpeech is called before the first chunk resolves", async () => {
    const s1 = "A".repeat(150) + ".";
    const s2 = "B".repeat(150) + ".";
    const gate = deferred<string>();
    (mentrixSpeakCloned as ReturnType<typeof vi.fn>)
      .mockImplementationOnce(() => gate.promise)
      // The pipeline prefetches chunk 2 as soon as chunk 1 resolves, before
      // checking cancellation — real mentrixSpeakCloned always returns a
      // Promise, so give this call a resolved one too.
      .mockResolvedValue("blob:chunk-1");

    const resultPromise = speakMentrixStreamedAwait(`${s1} ${s2}`, true);
    cancelMentrixSpeech();
    gate.resolve("blob:chunk-0");
    const result = await resultPromise;

    expect(result).toEqual({ ok: false, error: "cancelled" });
    expect(mentrixSpeakCloned).toHaveBeenCalledTimes(2);
  });
});
