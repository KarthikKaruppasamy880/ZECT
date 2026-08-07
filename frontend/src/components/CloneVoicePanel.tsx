/**
 * Mentrix Companion Chatterbox voice — record/upload a sample stored in ZECT.
 * Default voice is used for Present, narrate, and Connect Voice sessions.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { Mic, MicOff, Trash2, Loader2, CheckCircle2, Upload, Star } from "lucide-react";
import {
  cloneMyVoice,
  deleteClonedVoice,
  listMyClonedVoices,
  mentrixVoiceEngineStatus,
  setDefaultClonedVoice,
  type ClonedVoiceInfo,
  type VoiceEngineStatus,
} from "@/lib/api";
import { speakMentrix } from "@/mentrix/speak";

type Props = {
  /** Open the full form immediately (e.g. Companion Voice tab deep link). */
  defaultExpanded?: boolean;
  /** Companion HUD uses dark surfaces. */
  variant?: "light" | "dark";
};

const SAMPLE_SCRIPT =
  "Hello, this is my Mentrix voice. I use it for personal assistance, reading documents, presentations, and meetings.";

function pickRecorderMime(): string {
  if (typeof MediaRecorder === "undefined") return "";
  for (const mime of ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"]) {
    if (MediaRecorder.isTypeSupported(mime)) return mime;
  }
  return "";
}

export default function CloneVoicePanel({
  defaultExpanded = false,
  variant = "light",
}: Props) {
  const dark = variant === "dark";
  const [voices, setVoices] = useState<ClonedVoiceInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [name, setName] = useState("");
  const [referenceText, setReferenceText] = useState(SAMPLE_SCRIPT);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [recording, setRecording] = useState(false);
  const [recordSecs, setRecordSecs] = useState(0);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [readyNote, setReadyNote] = useState("");
  const [engineStatus, setEngineStatus] = useState<VoiceEngineStatus | null>(null);
  const [desktopCb, setDesktopCb] = useState<{
    bundled?: boolean;
    online?: boolean;
    running?: boolean;
    hint?: string;
    binaryPath?: string;
  } | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<number | null>(null);
  const previewUrlRef = useRef<string | null>(null);

  const defaultVoice = voices.find((v) => v.is_default) || voices[0] || null;

  useEffect(() => {
    if (defaultExpanded) setExpanded(true);
  }, [defaultExpanded]);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      mentrixVoiceEngineStatus()
        .then((s) => {
          if (!cancelled) setEngineStatus(s);
        })
        .catch(() => {
          if (!cancelled) {
            setEngineStatus({
              online: false,
              base_url: "http://127.0.0.1:17493",
              default_voice: null,
              hint: "Could not reach ZECT API for engine status.",
            });
          }
        });
      const desktop = (
        window as unknown as {
          zectDesktop?: {
            mentrix?: { chatterboxStatus?: () => Promise<Record<string, unknown>> };
          };
        }
      ).zectDesktop?.mentrix;
      if (desktop?.chatterboxStatus) {
        desktop
          .chatterboxStatus()
          .then((s) => {
            if (!cancelled) {
              setDesktopCb({
                bundled: Boolean(s.bundled),
                online: Boolean(s.online),
                running: Boolean(s.running),
                hint: typeof s.hint === "string" ? s.hint : undefined,
                binaryPath: typeof s.binaryPath === "string" ? s.binaryPath : undefined,
              });
            }
          })
          .catch(() => {});
      }
    };
    load();
    const t = window.setInterval(load, 8000);
    return () => {
      cancelled = true;
      window.clearInterval(t);
    };
  }, []);

  useEffect(() => {
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    };
  }, []);

  const setSampleFile = useCallback((next: File | null) => {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = null;
    }
    setFile(next);
    if (next) {
      const url = URL.createObjectURL(next);
      previewUrlRef.current = url;
      setPreviewUrl(url);
    } else {
      setPreviewUrl(null);
    }
  }, []);

  const refresh = useCallback(async () => {
    try {
      const list = await listMyClonedVoices();
      setVoices(Array.isArray(list) ? list : []);
    } catch {
      try {
        const { getMyClonedVoice } = await import("@/lib/api");
        const v = await getMyClonedVoice();
        setVoices(v ? [{ ...v, is_default: true }] : []);
      } catch {
        /* ignore */
      }
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const stopRecording = useCallback(() => {
    const rec = mediaRecorderRef.current;
    if (rec && rec.state !== "inactive") {
      rec.stop();
    }
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setRecording(false);
  }, []);

  const startRecording = useCallback(async () => {
    setError("");
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("This browser cannot record audio — upload a WAV/MP3 file instead.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mime = pickRecorderMime();
      const recorder = mime
        ? new MediaRecorder(stream, { mimeType: mime })
        : new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (ev) => {
        if (ev.data.size > 0) chunksRef.current.push(ev.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        const blobType = recorder.mimeType || mime || "audio/webm";
        const blob = new Blob(chunksRef.current, { type: blobType });
        const ext = blobType.includes("mp4") ? "m4a" : blobType.includes("ogg") ? "ogg" : "webm";
        const recorded = new File([blob], `mentrix-voice-sample.${ext}`, { type: blobType });
        setSampleFile(recorded);
        mediaRecorderRef.current = null;
      };
      mediaRecorderRef.current = recorder;
      recorder.start(250);
      setRecording(true);
      setRecordSecs(0);
      timerRef.current = window.setInterval(() => {
        setRecordSecs((s) => {
          if (s >= 59) {
            stopRecording();
            return 60;
          }
          return s + 1;
        });
      }, 1000);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Microphone permission denied — allow mic access or upload a file.",
      );
    }
  }, [setSampleFile, stopRecording]);

  const handleClone = async () => {
    if (!name.trim() || !referenceText.trim() || !file) return;
    setLoading(true);
    setError("");
    setReadyNote("");
    try {
      await cloneMyVoice(name.trim(), referenceText.trim(), file);
      await refresh();
      setSampleFile(null);
      setName("");
      setReferenceText(SAMPLE_SCRIPT);
      setReadyNote("Voice saved in your account. Use Present, narrate, or Test speak to verify audio.");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to clone voice";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (voiceId: string) => {
    setLoading(true);
    setError("");
    try {
      await deleteClonedVoice(voiceId);
      await refresh();
      setReadyNote("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete voice");
    } finally {
      setLoading(false);
    }
  };

  const handleSetDefault = async (voiceId: string) => {
    setLoading(true);
    setError("");
    try {
      await setDefaultClonedVoice(voiceId);
      await refresh();
      setReadyNote("Default voice updated for Present & sessions.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to set default");
    } finally {
      setLoading(false);
    }
  };

  const handleTestSpeak = async () => {
    setLoading(true);
    setError("");
    setReadyNote("");
    try {
      if (engineStatus && !engineStatus.online) {
        setError(
          `Chatterbox offline at ${engineStatus.base_url} — start the local engine to Test speak with your clone (sample in ZECT ≠ engine online).`,
        );
        return;
      }
      const result = await speakMentrix(
        "Mentrix voice check. If you hear this, TTS output is working.",
        true,
        { requireClone: true },
      );
      if (result.ok) {
        if (result.engine !== "chatterbox") {
          setError(`Expected clone TTS (chatterbox), got ${result.engine}`);
        } else {
          setReadyNote(`Voice check OK via ${result.engine}.`);
        }
      } else {
        setError(result.error);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Test speak failed");
    } finally {
      setLoading(false);
    }
  };

  const fieldClass = dark
    ? "border-slate-700 bg-slate-900 text-slate-100 placeholder:text-slate-500"
    : "border-slate-300 bg-white text-slate-900";

  if (!expanded && !defaultVoice) {
    return (
      <button
        data-testid="clone-voice-expand"
        onClick={() => setExpanded(true)}
        className={`flex items-center gap-2 text-xs ${
          dark ? "text-slate-400 hover:text-teal-300" : "text-slate-500 hover:text-slate-700"
        }`}
      >
        <Mic className="h-3.5 w-3.5" /> Clone my voice for Mentrix
      </button>
    );
  }

  return (
    <div
      data-testid="clone-voice-panel"
      className={`rounded-xl border p-4 space-y-3 ${
        dark ? "border-slate-700 bg-slate-950/80" : "border-slate-200 bg-white"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Mic className={`h-4 w-4 ${dark ? "text-teal-400" : "text-teal-600"}`} />
          <h3 className={`text-sm font-semibold ${dark ? "text-teal-100" : "text-slate-900"}`}>
            Mentrix Chatterbox voice
          </h3>
        </div>
        {defaultVoice && (
          <span
            data-testid="clone-voice-chatterbox-status"
            className={`text-[10px] px-2 py-0.5 rounded ${
              defaultVoice.sample_missing
                ? dark
                  ? "text-red-200 bg-red-900/40"
                  : "text-red-700 bg-red-50"
                : dark
                  ? "text-teal-200 bg-teal-900/40"
                  : "text-teal-700 bg-teal-50"
            }`}
          >
            {defaultVoice.sample_missing
              ? "Sample missing — re-clone"
              : defaultVoice.engine_ready
                ? "Default ready (engine)"
                : defaultVoice.has_sample
                  ? "Default saved (sample OK)"
                  : "Default ready"}
          </span>
        )}
      </div>

      <p className={`text-xs ${dark ? "text-slate-400" : "text-slate-500"}`}>
        Record 10–60 seconds reading the script (or upload a clean sample). ZECT stores the clone
        in your account — use it for Present, narrate, and Connect Voice sessions. Delete anytime.
        A saved sample is not the same as Chatterbox online — start the local engine to hear your voice.
      </p>

      <p
        data-testid="clone-voice-engine-status"
        className={`text-[11px] rounded border px-2 py-1 ${
          engineStatus?.online
            ? dark
              ? "border-emerald-800 text-emerald-200 bg-emerald-950/40"
              : "border-emerald-200 text-emerald-800 bg-emerald-50"
            : dark
              ? "border-amber-800 text-amber-200 bg-amber-950/40"
              : "border-amber-200 text-amber-900 bg-amber-50"
        }`}
        title={engineStatus?.hint || undefined}
      >
        {!engineStatus
          ? "Checking Chatterbox engine…"
          : engineStatus.online
            ? `Chatterbox online (${engineStatus.base_url})`
            : `Chatterbox offline (${engineStatus.base_url}) — start local engine to Test speak / Present`}
      </p>
      {desktopCb?.bundled ? (
        <p className={`text-[10px] ${dark ? "text-teal-300/80" : "text-teal-700"}`} data-testid="clone-voice-bundled">
          Bundled Chatterbox sidecar detected
          {desktopCb.binaryPath ? ` (${desktopCb.binaryPath.split(/[/\\]/).pop()})` : ""}
        </p>
      ) : null}
      {typeof window !== "undefined" &&
        (window as unknown as { zectDesktop?: { mentrix?: { chatterboxStart?: () => Promise<unknown> } } })
          .zectDesktop?.mentrix?.chatterboxStart && (
        <div className="flex flex-wrap gap-2 items-center">
          <button
            type="button"
            data-testid="clone-voice-chatterbox-start"
            className={`text-[11px] px-2 py-1 rounded border ${
              dark ? "border-slate-600 text-slate-200" : "border-slate-300 text-slate-700"
            }`}
            onClick={async () => {
              setError("");
              setStatus("Starting ZECT Voicebox / Chatterbox…");
              try {
                const raw = await (
                  window as unknown as {
                    zectDesktop: {
                      mentrix: {
                        chatterboxStart: () => Promise<{
                          ok?: boolean;
                          error?: string;
                          already?: boolean;
                          zectVoicebox?: boolean;
                        }>;
                      };
                    };
                  }
                ).zectDesktop.mentrix.chatterboxStart();
                if (raw && raw.ok === false) {
                  setError(
                    raw.error ||
                      "Start failed — no binary and ZECT Voicebox could not launch. See docs/ZECT_VOICEBOX.md",
                  );
                  setStatus("");
                  return;
                }
                if (raw?.already) {
                  setStatus("Engine process already running — checking health…");
                } else if (raw?.zectVoicebox) {
                  setStatus("Started ZECT Voicebox — waiting for /profiles…");
                } else {
                  setStatus("Engine start requested — waiting for /profiles…");
                }
                let online = false;
                for (let i = 0; i < 10; i++) {
                  await new Promise((r) => setTimeout(r, 800));
                  const st = await mentrixVoiceEngineStatus();
                  setEngineStatus(st);
                  if (st.online) {
                    online = true;
                    break;
                  }
                }
                if (online) {
                  setStatus("Chatterbox online — Test speak unlocked.");
                  setError("");
                } else {
                  setError(
                    "Engine started but Mentrix still sees offline. Confirm CHATTERBOX_BASE_URL=http://127.0.0.1:17493 and restart the ZECT API.",
                  );
                  setStatus("");
                }
              } catch (e) {
                setError(e instanceof Error ? e.message : "Start Chatterbox failed");
                setStatus("");
              }
            }}
          >
            {desktopCb?.bundled ? "Start bundled Chatterbox" : "Start local Chatterbox (Electron)"}
          </button>
          <button
            type="button"
            data-testid="clone-voice-chatterbox-stop"
            className={`text-[11px] px-2 py-1 rounded border ${
              dark ? "border-slate-600 text-slate-200" : "border-slate-300 text-slate-700"
            }`}
            onClick={async () => {
              setError("");
              try {
                await (
                  window as unknown as {
                    zectDesktop: { mentrix: { chatterboxStop: () => Promise<unknown> } };
                  }
                ).zectDesktop.mentrix.chatterboxStop();
                const st = await mentrixVoiceEngineStatus();
                setEngineStatus(st);
                setStatus(st.online ? "Stop requested (engine still answering)." : "Engine stopped.");
              } catch (e) {
                setError(e instanceof Error ? e.message : "Stop failed");
              }
            }}
          >
            Stop engine
          </button>
        </div>
      )}

      {voices.length > 0 && (
        <ul className="space-y-2" data-testid="clone-voice-list">
          {voices.map((v) => (
            <li
              key={v.voice_id}
              className={`flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm ${
                dark ? "border-slate-700 text-slate-200" : "border-slate-200 text-slate-700"
              }`}
              data-testid="clone-voice-active"
            >
              <div className="flex items-center gap-2 min-w-0">
                {v.is_default ? (
                  <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                ) : (
                  <Mic className="h-4 w-4 text-slate-500 shrink-0" />
                )}
                <span className="truncate">
                  <strong>{v.name}</strong>
                  {v.is_default ? " · Present/sessions default" : ""}
                </span>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {!v.is_default && (
                  <button
                    type="button"
                    data-testid="clone-voice-set-default"
                    onClick={() => void handleSetDefault(v.voice_id)}
                    disabled={loading}
                    className="flex items-center gap-1 text-xs text-teal-400 hover:text-teal-300 disabled:opacity-50"
                    title="Use for Present and sessions"
                  >
                    <Star className="h-3.5 w-3.5" /> Use
                  </button>
                )}
                <button
                  type="button"
                  data-testid="clone-voice-reset"
                  onClick={() => void handleDelete(v.voice_id)}
                  disabled={loading}
                  className="flex items-center gap-1 text-xs text-red-400 hover:text-red-300 disabled:opacity-50"
                >
                  {loading ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Trash2 className="h-3.5 w-3.5" />
                  )}
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          data-testid="clone-voice-test-speak"
          disabled={loading || (engineStatus !== null && !engineStatus.online)}
          onClick={() => void handleTestSpeak()}
          className={`rounded-lg border px-2.5 py-1.5 text-xs disabled:opacity-40 ${
            dark
              ? "border-teal-700 text-teal-200 hover:bg-teal-950"
              : "border-teal-300 text-teal-800 hover:bg-teal-50"
          }`}
          title={
            engineStatus && !engineStatus.online
              ? "Start local Chatterbox to Test speak with your clone"
              : "Speak a short line with your default clone"
          }
        >
          Test speak
        </button>
        {readyNote && (
          <p data-testid="clone-voice-ready" className="text-xs text-emerald-400">
            {readyNote}
          </p>
        )}
      </div>

      <div className="space-y-3">
        <p className={`text-[11px] font-semibold uppercase tracking-wide ${dark ? "text-teal-400" : "text-teal-700"}`}>
          {voices.length ? "Add another voice" : "Clone a voice"}
        </p>
        <input
          data-testid="clone-voice-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Voice name (e.g. Karthik)"
          className={`w-full p-2 rounded-lg text-sm border ${fieldClass}`}
        />
        <div>
          <label className={`mb-1 block text-[11px] font-medium ${dark ? "text-slate-400" : "text-slate-600"}`}>
            Read this aloud while recording (edit if you say something else)
          </label>
          <textarea
            data-testid="clone-voice-transcript"
            value={referenceText}
            onChange={(e) => setReferenceText(e.target.value)}
            rows={3}
            className={`w-full p-2 rounded-lg text-sm border ${fieldClass}`}
          />
        </div>

        <div
          className={`rounded-lg border p-3 space-y-2 ${
            dark ? "border-teal-900/60 bg-slate-900/80" : "border-teal-100 bg-teal-50/40"
          }`}
        >
          <p className={`text-[11px] font-semibold uppercase tracking-wide ${dark ? "text-teal-400" : "text-teal-700"}`}>
            Record sample
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {!recording ? (
              <button
                type="button"
                data-testid="clone-voice-record"
                onClick={() => void startRecording()}
                className="inline-flex items-center gap-2 rounded-lg bg-rose-600 hover:bg-rose-500 px-3 py-2 text-sm font-medium text-white"
              >
                <Mic className="h-4 w-4" />
                Start recording
              </button>
            ) : (
              <button
                type="button"
                data-testid="clone-voice-stop"
                onClick={stopRecording}
                className="inline-flex items-center gap-2 rounded-lg bg-slate-700 hover:bg-slate-600 px-3 py-2 text-sm font-medium text-white"
              >
                <MicOff className="h-4 w-4" />
                Stop ({recordSecs}s)
              </button>
            )}
            {recording && (
              <span data-testid="clone-voice-recording" className="text-xs text-rose-400 animate-pulse">
                ● Recording — speak clearly for 10–60s
              </span>
            )}
          </div>
          {file && !recording && (
            <div className="space-y-1" data-testid="clone-voice-sample-ready">
              <p className={`text-xs ${dark ? "text-emerald-400" : "text-emerald-700"}`}>
                Sample ready: {file.name} ({Math.max(1, Math.round(file.size / 1024))} KB)
              </p>
              {previewUrl && (
                <audio data-testid="clone-voice-preview" controls src={previewUrl} className="w-full h-8" />
              )}
              <button
                type="button"
                className="text-xs text-slate-400 hover:text-slate-200 underline"
                onClick={() => setSampleFile(null)}
              >
                Clear sample
              </button>
            </div>
          )}
          <label
            className={`inline-flex items-center gap-2 text-xs cursor-pointer ${
              dark ? "text-slate-400 hover:text-teal-300" : "text-slate-600 hover:text-teal-700"
            }`}
          >
            <Upload className="h-3.5 w-3.5" />
            Or upload WAV / MP3 / WebM
            <input
              data-testid="clone-voice-file"
              type="file"
              accept="audio/wav,audio/mpeg,audio/mp4,audio/ogg,audio/webm,audio/x-wav"
              className="hidden"
              onChange={(e) => setSampleFile(e.target.files?.[0] || null)}
            />
          </label>
        </div>

        <button
          data-testid="clone-voice-submit"
          onClick={() => void handleClone()}
          disabled={loading || recording || !name.trim() || !referenceText.trim() || !file}
          className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:bg-slate-600 disabled:opacity-50 text-white rounded-lg text-sm font-medium"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mic className="h-4 w-4" />}
          {loading ? "Saving..." : "Save voice to ZECT"}
        </button>
      </div>

      {error && (
        <div data-testid="clone-voice-error" className="text-xs text-red-400">
          {error}
        </div>
      )}
    </div>
  );
}
