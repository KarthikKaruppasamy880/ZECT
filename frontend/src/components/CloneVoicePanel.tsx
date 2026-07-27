/**
 * Mentrix voice cloning — clone your own voice via local Voicebox; Realtime
 * uses cloned TTS when configured.
 */
import { useCallback, useEffect, useState } from "react";
import { Mic, Trash2, Loader2, CheckCircle2 } from "lucide-react";
import { cloneMyVoice, getMyClonedVoice, resetMyClonedVoice } from "@/lib/api";

type ClonedVoice = { voice_id: string; name: string; provider: string };

export default function CloneVoicePanel() {
  const [voice, setVoice] = useState<ClonedVoice | null>(null);
  const [loading, setLoading] = useState(false);
  const [name, setName] = useState("");
  const [referenceText, setReferenceText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState(false);
  const [voiceboxOk, setVoiceboxOk] = useState<boolean | null>(null);

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

  const handleClone = async () => {
    if (!name.trim() || !referenceText.trim() || !file) return;
    setLoading(true);
    setError("");
    try {
      const v = await cloneMyVoice(name.trim(), referenceText.trim(), file);
      setVoice(v);
      setVoiceboxOk(true);
      setFile(null);
      setName("");
      setReferenceText("");
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

  if (!expanded && !voice) {
    return (
      <button
        data-testid="clone-voice-expand"
        onClick={() => setExpanded(true)}
        className="flex items-center gap-2 text-xs text-slate-500 hover:text-slate-700"
      >
        <Mic className="h-3.5 w-3.5" /> Clone my voice for Mentrix
      </button>
    );
  }

  return (
    <div data-testid="clone-voice-panel" className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Mic className="h-4 w-4 text-teal-600" />
          <h3 className="text-sm font-semibold text-slate-900">Mentrix Voice Cloning</h3>
        </div>
        {voiceboxOk === false && (
          <span data-testid="clone-voice-voicebox-status" className="text-[10px] text-amber-700 bg-amber-50 px-2 py-0.5 rounded">
            Voicebox offline
          </span>
        )}
        {voiceboxOk === true && !voice && (
          <span data-testid="clone-voice-voicebox-status" className="text-[10px] text-teal-700 bg-teal-50 px-2 py-0.5 rounded">
            Voicebox ready
          </span>
        )}
      </div>

      {voice ? (
        <div className="flex items-center justify-between gap-3" data-testid="clone-voice-active">
          <div className="flex items-center gap-2 text-sm text-slate-700">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            Speaking as <strong>{voice.name}</strong>
          </div>
          <button
            data-testid="clone-voice-reset"
            onClick={handleReset}
            disabled={loading}
            className="flex items-center gap-1 text-xs text-red-600 hover:text-red-700 disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
            Reset
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-xs text-slate-500">
            Runs fully on your machine via{" "}
            <a href="https://github.com/jamiepine/voicebox" target="_blank" rel="noreferrer" className="underline">
              Voicebox
            </a>{" "}
            — no API key. Start it locally, then upload a short (10–60s) clean sample plus the exact text you say.
          </p>
          <input
            data-testid="clone-voice-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Voice name (e.g. Karthik)"
            className="w-full p-2 border border-slate-300 rounded-lg text-sm"
          />
          <textarea
            data-testid="clone-voice-transcript"
            value={referenceText}
            onChange={(e) => setReferenceText(e.target.value)}
            placeholder="Exact transcript of what the sample says (needed for accurate cloning)"
            rows={2}
            className="w-full p-2 border border-slate-300 rounded-lg text-sm"
          />
          <input
            data-testid="clone-voice-file"
            type="file"
            accept="audio/wav,audio/mpeg,audio/mp4,audio/ogg,audio/x-wav"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="w-full text-sm"
          />
          <button
            data-testid="clone-voice-submit"
            onClick={handleClone}
            disabled={loading || !name.trim() || !referenceText.trim() || !file}
            className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:bg-slate-300 text-white rounded-lg text-sm font-medium"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mic className="h-4 w-4" />}
            {loading ? "Cloning..." : "Clone My Voice"}
          </button>
        </div>
      )}

      {error && (
        <div data-testid="clone-voice-error" className="text-xs text-red-600">
          {error}
        </div>
      )}
    </div>
  );
}
