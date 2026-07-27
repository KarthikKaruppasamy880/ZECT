/**
 * Mentrix Companion voice cloning — record or upload a sample for personal
 * assistant, presentations, reading docs, and agent meetings (local Voicebox).
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { Mic, MicOff, Trash2, Loader2, CheckCircle2, Upload } from "lucide-react";
import { cloneMyVoice, getMyClonedVoice, resetMyClonedVoice } from "@/lib/api";

type ClonedVoice = { voice_id: string; name: string; provider: string };

type Props = {
  /** Open the full form immediately (e.g. Labs → Voice Cloning deep link). */
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
  const [voice, setVoice] = useState<ClonedVoice | null>(null);
  const [loading, setLoading] = useState(false);
  const [name, setName] = useState("");
  const [referenceText, setReferenceText] = useState(SAMPLE_SCRIPT);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [voiceboxOk, setVoiceboxOk] = useState<boolean | null>(null);
  const [recording, setRecording] = useState(false);
  const [recordSecs, setRecordSecs] = useState(0);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<number | null>(null);
  const previewUrlRef = useRef<string | null>(null);

  useEffect(() => {
    if (defaultExpanded) setExpanded(true);
  }, [defaultExpanded]);

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
      const v = await getMyClonedVoice();
      setVoice(v);
      setVoiceboxOk(true);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "";
      if (msg.includes("503") || msg.toLowerCase().includes("voicebox")) {
        setVoiceboxOk(false);
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
    try {
      const v = await cloneMyVoice(name.trim(), referenceText.trim(), file);
      setVoice(v);
      setVoiceboxOk(true);
      setSampleFile(null);
      setName("");
      setReferenceText(SAMPLE_SCRIPT);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to clone voice";
      setError(msg);
      if (msg.toLowerCase().includes("voicebox")) setVoiceboxOk(false);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    setError("");
    try {
      await resetMyClonedVoice();
      setVoice(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to reset voice");
    } finally {
      setLoading(false);
    }
  };

  const fieldClass = dark
    ? "border-slate-700 bg-slate-900 text-slate-100 placeholder:text-slate-500"
    : "border-slate-300 bg-white text-slate-900";

  if (!expanded && !voice) {
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
            Your Mentrix voice
          </h3>
        </div>
        {voiceboxOk === false && (
          <span
            data-testid="clone-voice-voicebox-status"
            className="text-[10px] text-amber-200 bg-amber-900/40 px-2 py-0.5 rounded"
          >
            Voicebox offline
          </span>
        )}
        {voiceboxOk === true && !voice && (
          <span
            data-testid="clone-voice-voicebox-status"
            className={`text-[10px] px-2 py-0.5 rounded ${
              dark ? "text-teal-200 bg-teal-900/40" : "text-teal-700 bg-teal-50"
            }`}
          >
            Voicebox ready
          </span>
        )}
      </div>

      <p className={`text-xs ${dark ? "text-slate-400" : "text-slate-500"}`}>
        Record 10–60 seconds reading the script below (or upload a clean sample). Mentrix then
        speaks as you for personal assistance, presentations, docs, and meetings via{" "}
        <a
          href="https://github.com/jamiepine/voicebox"
          target="_blank"
          rel="noreferrer"
          className="underline"
        >
          Voicebox
        </a>
        .
      </p>

      {voice ? (
        <div className="flex items-center justify-between gap-3" data-testid="clone-voice-active">
          <div
            className={`flex items-center gap-2 text-sm ${dark ? "text-slate-200" : "text-slate-700"}`}
          >
            <CheckCircle2 className="h-4 w-4 text-green-500" />
            Speaking as <strong>{voice.name}</strong>
          </div>
          <button
            data-testid="clone-voice-reset"
            onClick={handleReset}
            disabled={loading}
            className="flex items-center gap-1 text-xs text-red-400 hover:text-red-300 disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
            Reset
          </button>
        </div>
      ) : (
        <div className="space-y-3">
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
            onClick={handleClone}
            disabled={loading || recording || !name.trim() || !referenceText.trim() || !file}
            className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:bg-slate-600 disabled:opacity-50 text-white rounded-lg text-sm font-medium"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mic className="h-4 w-4" />}
            {loading ? "Cloning..." : "Clone My Voice"}
          </button>
        </div>
      )}

      {error && (
        <div data-testid="clone-voice-error" className="text-xs text-red-400">
          {error}
        </div>
      )}
    </div>
  );
}
