/**
 * Companion Present Deck — Presenton generate + open PPTX/Zoom (Electron) + narrate (Chatterbox).
 * Electron-only Present all slides: parse notes → F5 → speak await → Right Arrow.
 */
import { useEffect, useRef, useState } from "react";
import { Presentation, Mic, MonitorPlay, Sparkles, Square } from "lucide-react";
import { mentrixCompanionIntegrations, mentrixPresentonGenerate, listMyClonedVoices, type ClonedVoiceInfo } from "@/lib/api";
import { cancelMentrixSpeech, speakMentrix, speakMentrixStreamedAwait, type SpeakVoiceOptions } from "@/mentrix/speak";

const STORAGE_KEY = "zect_mentrix_present_deck_path";
const NOTES_KEY = "zect_mentrix_present_deck_notes";
const PROMPT_KEY = "zect_mentrix_present_deck_prompt";
const JOIN_KEY = "zect_mentrix_zoom_join_url";
const VOICE_CHOICE_KEY = "zect_mentrix_present_deck_voice";

// OpenAI's real TTS voice names — offered as an explicit alternative to your
// clone, e.g. when you want a stock male/female voice for a given presentation.
const STOCK_VOICES: { id: string; label: string }[] = [
  { id: "alloy", label: "OpenAI — Alloy (neutral)" },
  { id: "echo", label: "OpenAI — Echo (male)" },
  { id: "fable", label: "OpenAI — Fable (male, British)" },
  { id: "onyx", label: "OpenAI — Onyx (male, deep)" },
  { id: "nova", label: "OpenAI — Nova (female)" },
  { id: "shimmer", label: "OpenAI — Shimmer (female)" },
];

type Props = {
  variant?: "dark" | "light";
};

type SlideParsed = { index: number; notes?: string; text?: string };

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

function friendlyDesktopError(code: string): string {
  const c = String(code || "");
  if (c === "unsupported_presentation_type") {
    return "Need a .pptx/.ppt/.pdf path — strip quotes when pasting from Explorer.";
  }
  if (c === "pptx_required_for_present_all") {
    return "Present all slides requires a .pptx file.";
  }
  if (c === "path_outside_allowlist") {
    return "Path must be under Desktop, Documents, or Downloads (OneDrive OK).";
  }
  if (c === "not_found") return "File not found at that path.";
  if (c === "zoom_not_found") {
    return "Zoom.exe not found — set ZOOM_DESKTOP_PATH or a Zoom join URL.";
  }
  if (c === "invalid_zoom_join_url") return "Join URL must be https://*.zoom.us/…";
  if (c === "computer_mode_off") return "Turn on Computer Mode in Electron first.";
  return c;
}

export default function PresentDeckPanel({ variant = "dark" }: Props) {
  const [path, setPath] = useState("");
  const [notes, setNotes] = useState("");
  const [prompt, setPrompt] = useState("");
  const [joinUrl, setJoinUrl] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [presenting, setPresenting] = useState(false);
  const [presentonReady, setPresentonReady] = useState(false);
  const [myVoices, setMyVoices] = useState<ClonedVoiceInfo[]>([]);
  const [voiceChoice, setVoiceChoice] = useState("");
  const abortRef = useRef(false);
  const isDesktop = typeof window !== "undefined" && !!window.zectDesktop?.isDesktopApp;
  const dark = variant === "dark";

  useEffect(() => {
    try {
      setPath(localStorage.getItem(STORAGE_KEY) || "");
      setNotes(localStorage.getItem(NOTES_KEY) || "");
      setPrompt(localStorage.getItem(PROMPT_KEY) || "");
      setJoinUrl(localStorage.getItem(JOIN_KEY) || "");
      setVoiceChoice(localStorage.getItem(VOICE_CHOICE_KEY) || "");
    } catch {
      /* ignore */
    }
    mentrixCompanionIntegrations()
      .then((s) => {
        setPresentonReady(!!s.presenton);
        if (!localStorage.getItem(JOIN_KEY) && s.zoom_join_url_configured) {
          /* env-backed join is opened server-side via Electron env; UI field optional */
        }
      })
      .catch(() => setPresentonReady(false));
    listMyClonedVoices()
      .then((v) => setMyVoices(Array.isArray(v) ? v : []))
      .catch(() => setMyVoices([]));
  }, []);

  const persistVoiceChoice = (value: string) => {
    setVoiceChoice(value);
    try {
      localStorage.setItem(VOICE_CHOICE_KEY, value);
    } catch {
      /* ignore */
    }
  };

  /** Turns the dropdown value into what speak.ts/the /speak endpoint expects.
   * Empty string = your default cloned voice, unchanged from before this existed. */
  const voiceOptsFromChoice = (choice: string): SpeakVoiceOptions | undefined => {
    if (!choice) return undefined;
    if (choice.startsWith("clone:")) return { voiceId: choice.slice("clone:".length) };
    if (choice.startsWith("stock:")) return { stockVoice: choice.slice("stock:".length) };
    return undefined;
  };

  const persistPath = (value: string) => {
    setPath(value);
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch {
      /* ignore */
    }
  };

  const persistNotes = (value: string) => {
    setNotes(value);
    try {
      localStorage.setItem(NOTES_KEY, value);
    } catch {
      /* ignore */
    }
  };

  const persistPrompt = (value: string) => {
    setPrompt(value);
    try {
      localStorage.setItem(PROMPT_KEY, value);
    } catch {
      /* ignore */
    }
  };

  const persistJoin = (value: string) => {
    setJoinUrl(value);
    try {
      localStorage.setItem(JOIN_KEY, value);
    } catch {
      /* ignore */
    }
  };

  const ensureComputerMode = async () => {
    const mentrix = window.zectDesktop?.mentrix;
    if (!mentrix?.setComputerMode) return false;
    await mentrix.setComputerMode(true);
    return true;
  };

  const runComputer = async (action: string, args: Record<string, unknown>) => {
    if (!isDesktop) {
      setStatus("Electron desktop app required to open PowerPoint / Zoom.");
      return { ok: false as const, error: "not_desktop_app" };
    }
    await ensureComputerMode();
    const computer = window.zectDesktop?.mentrix?.computer;
    if (!computer) {
      setStatus("Electron desktop app required to open PowerPoint / Zoom.");
      return { ok: false as const, error: "not_desktop_app" };
    }
    const res = (await computer(action, args)) as {
      ok?: boolean;
      error?: string;
      hint?: string;
      note?: string;
      slides?: SlideParsed[];
      count?: number;
    };
    if (res?.ok === false) {
      const msg = friendlyDesktopError(String(res.error || "desktop_failed"));
      setStatus(res.hint ? `${msg} (${res.hint})` : msg);
      return { ok: false as const, error: String(res.error || "desktop_failed") };
    }
    return {
      ok: true as const,
      note: res.note,
      slides: res.slides,
      count: res.count,
    };
  };

  const generateDeck = async () => {
    setBusy(true);
    setStatus("");
    try {
      const content = prompt.trim();
      if (!content) {
        setStatus("Enter a deck prompt (topic + key points) for Presenton.");
        return;
      }
      const out = await mentrixPresentonGenerate({
        content,
        n_slides: 6,
        template: "general",
        filename: "mentrix-deck.pptx",
      });
      if (out?.path) {
        persistPath(out.path);
        setStatus(`Deck saved to ${out.path}. Open presentation, then join Zoom and share.`);
      } else {
        setStatus("Presenton returned no path — check PRESENTON_BASE_URL.");
      }
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Generate deck failed");
    } finally {
      setBusy(false);
    }
  };

  const openPresentation = async () => {
    setBusy(true);
    setStatus("");
    try {
      const target = path.trim().replace(/^["']+|["']+$/g, "");
      if (!target) {
        setStatus("Enter a .pptx path under Desktop, Documents, or Downloads (OneDrive OK).");
        return;
      }
      persistPath(target);
      const res = await runComputer("open_presentation", { path: target });
      if (res.ok) {
        setStatus("Opened presentation in PowerPoint. Join your meeting, share PowerPoint, then Narrate.");
      }
    } finally {
      setBusy(false);
    }
  };

  const openZoom = async () => {
    setBusy(true);
    setStatus("");
    try {
      const url = joinUrl.trim();
      const res = await runComputer("open_zoom", url ? { join_url: url } : {});
      if (res.ok) {
        setStatus(
          res.note ||
            "Opened Zoom. Join your meeting, share PowerPoint, then Narrate. (Mentrix does not auto-share.)",
        );
      }
    } finally {
      setBusy(false);
    }
  };

  const narrateNotes = async () => {
    setBusy(true);
    setStatus("");
    try {
      const text =
        notes.trim() ||
        "Mentrix Present Deck. Paste talking points, then Narrate again with your default Chatterbox voice.";
      const result = await speakMentrix(text.slice(0, 2000), true, voiceOptsFromChoice(voiceChoice));
      if (result.ok) {
        setStatus(
          result.engine === "browser_speechSynthesis"
            ? "Narrating via browser speech (Chatterbox/OpenAI unavailable)."
            : "Narrating talking points (Mentrix TTS).",
        );
      } else {
        setStatus(result.error);
      }
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Narrate failed");
    } finally {
      setBusy(false);
    }
  };

  const stopPresentAll = () => {
    abortRef.current = true;
    cancelMentrixSpeech();
    setStatus("Stopped presenting.");
    setPresenting(false);
    setBusy(false);
  };

  const presentAllSlides = async () => {
    if (!isDesktop) {
      setStatus("Present all slides requires the Electron desktop app (Computer Mode).");
      return;
    }
    const target = path.trim().replace(/^["']+|["']+$/g, "");
    if (!target) {
      setStatus("Enter a .pptx path under Desktop, Documents, or Downloads (OneDrive OK).");
      return;
    }
    if (!/\.pptx$/i.test(target)) {
      setStatus("Present all slides requires a .pptx file.");
      return;
    }

    abortRef.current = false;
    setPresenting(true);
    setBusy(true);
    setStatus("");
    persistPath(target);

    try {
      const parsed = await runComputer("parse_presentation_slides", { path: target });
      if (!parsed.ok) return;
      const slides = parsed.slides || [];
      if (!slides.length) {
        setStatus("No slides found in that .pptx.");
        return;
      }

      const opened = await runComputer("open_presentation", { path: target });
      if (!opened.ok || abortRef.current) return;

      setStatus(`Starting slideshow (F5)… ${slides.length} slides`);
      await sleep(2000);
      if (abortRef.current) return;

      const f5 = await runComputer("powerpoint_key", { key: "f5" });
      if (!f5.ok || abortRef.current) return;
      await sleep(400);

      for (let i = 0; i < slides.length; i++) {
        if (abortRef.current) {
          setStatus("Stopped presenting.");
          return;
        }
        const slide = slides[i];
        const n = slides.length;
        const script = (slide.notes || slide.text || "").trim() || `Slide ${i + 1} of ${n}.`;
        setStatus(`Slide ${i + 1} / ${n}`);
        const spoken = await speakMentrixStreamedAwait(script.slice(0, 2000), true, voiceOptsFromChoice(voiceChoice));
        if (abortRef.current) {
          setStatus("Stopped presenting.");
          return;
        }
        if (!spoken.ok && spoken.error !== "cancelled") {
          setStatus(`Slide ${i + 1}: ${spoken.error}`);
          return;
        }
        if (i < slides.length - 1) {
          const right = await runComputer("powerpoint_key", { key: "right" });
          if (!right.ok || abortRef.current) {
            if (abortRef.current) setStatus("Stopped presenting.");
            return;
          }
          await sleep(400);
        }
      }
      setStatus(`Finished presenting ${slides.length} slides.`);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Present all failed");
    } finally {
      setPresenting(false);
      setBusy(false);
    }
  };

  return (
    <div
      data-testid="present-deck-panel"
      className={
        dark
          ? "rounded-xl border border-teal-800/50 bg-slate-950/70 p-3 space-y-2"
          : "rounded-xl border border-slate-200 bg-white p-3 space-y-2"
      }
    >
      <div className="flex items-center gap-2">
        <Presentation className={`h-4 w-4 ${dark ? "text-teal-400" : "text-teal-700"}`} />
        <p
          className={`text-[10px] uppercase tracking-[0.2em] ${
            dark ? "text-teal-400" : "text-teal-700"
          }`}
        >
          Present Deck — PPTX + Zoom
        </p>
      </div>
      <p className={`text-[11px] ${dark ? "text-slate-400" : "text-slate-600"}`}>
        Generate with Presenton (optional), open PowerPoint + Zoom in Electron. You join the meeting
        and share the PowerPoint window — Mentrix narrates with your clone. Desktop: Present all
        slides uses speaker notes (or slide text), F5, then Right after each narration ends.
      </p>
      <label className={`block text-xs ${dark ? "text-slate-300" : "text-slate-700"}`}>
        Generate deck prompt (Presenton)
        <textarea
          data-testid="present-deck-prompt"
          value={prompt}
          onChange={(e) => persistPrompt(e.target.value)}
          rows={2}
          placeholder="Q2 ZOAS delivery brief: status, risks, next actions…"
          className={
            dark
              ? "mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100"
              : "mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-xs"
          }
        />
      </label>
      <button
        type="button"
        data-testid="present-deck-generate"
        disabled={busy}
        onClick={() => void generateDeck()}
        className="inline-flex items-center gap-1.5 rounded-lg border border-violet-700 px-2.5 py-1.5 text-xs text-violet-200 hover:bg-violet-950 disabled:opacity-40"
        title={
          presentonReady
            ? "Calls PRESENTON_BASE_URL generate API"
            : "Set PRESENTON_BASE_URL and run Presenton Docker"
        }
      >
        <Sparkles className="h-3.5 w-3.5" />
        Generate deck
      </button>
      <label className={`block text-xs ${dark ? "text-slate-300" : "text-slate-700"}`}>
        Presentation path (.pptx)
        <input
          data-testid="present-deck-path"
          value={path}
          onChange={(e) => persistPath(e.target.value)}
          placeholder="C:\\Users\\you\\Documents\\deck.pptx"
          className={
            dark
              ? "mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100"
              : "mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-xs"
          }
        />
      </label>
      <label className={`block text-xs ${dark ? "text-slate-300" : "text-slate-700"}`}>
        Zoom join URL (optional)
        <input
          data-testid="present-deck-zoom-join"
          value={joinUrl}
          onChange={(e) => persistJoin(e.target.value)}
          placeholder="https://zoom.us/j/…"
          className={
            dark
              ? "mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100"
              : "mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-xs"
          }
        />
      </label>
      <label className={`block text-xs ${dark ? "text-slate-300" : "text-slate-700"}`}>
        Manual script (separate from your .pptx — typed here, not read from the file)
        <textarea
          data-testid="present-deck-notes"
          value={notes}
          onChange={(e) => persistNotes(e.target.value)}
          rows={3}
          placeholder="Key points to narrate with your cloned voice — this text is NOT pulled from the PPTX above…"
          className={
            dark
              ? "mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100"
              : "mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-xs"
          }
        />
      </label>
      <label className={`block text-xs ${dark ? "text-slate-300" : "text-slate-700"}`}>
        Narration voice
        <select
          data-testid="present-deck-voice-select"
          value={voiceChoice}
          onChange={(e) => persistVoiceChoice(e.target.value)}
          className={
            dark
              ? "mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100"
              : "mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-xs"
          }
        >
          <option value="">My default cloned voice</option>
          {myVoices
            .filter((v) => !v.is_default)
            .map((v) => (
              <option key={v.voice_id} value={`clone:${v.voice_id}`}>
                My voice — {v.name}
              </option>
            ))}
          {STOCK_VOICES.map((v) => (
            <option key={v.id} value={`stock:${v.id}`}>
              {v.label}
            </option>
          ))}
        </select>
      </label>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          data-testid="present-deck-open-pptx"
          disabled={busy}
          onClick={() => void openPresentation()}
          className="inline-flex items-center gap-1.5 rounded-lg border border-teal-700 px-2.5 py-1.5 text-xs text-teal-200 hover:bg-teal-950 disabled:opacity-40"
        >
          <MonitorPlay className="h-3.5 w-3.5" />
          Open presentation
        </button>
        <button
          type="button"
          data-testid="present-deck-open-zoom"
          disabled={busy}
          onClick={() => void openZoom()}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 px-2.5 py-1.5 text-xs text-slate-200 hover:bg-slate-800 disabled:opacity-40"
        >
          Open Zoom
        </button>
        <button
          type="button"
          data-testid="present-deck-narrate"
          disabled={busy}
          onClick={() => void narrateNotes()}
          className="inline-flex items-center gap-1.5 rounded-lg bg-teal-700 px-2.5 py-1.5 text-xs text-white hover:bg-teal-600 disabled:opacity-40"
          title="Speaks the Manual script text above — does not read your .pptx file"
        >
          <Mic className="h-3.5 w-3.5" />
          Narrate manual script (not the PPTX)
        </button>
        <button
          type="button"
          data-testid="present-deck-present-all"
          disabled={busy || !isDesktop}
          onClick={() => void presentAllSlides()}
          className="inline-flex items-center gap-1.5 rounded-lg border border-amber-700 px-2.5 py-1.5 text-xs text-amber-100 hover:bg-amber-950 disabled:opacity-40"
          title={
            isDesktop
              ? "Reads real slide text + speaker notes from your .pptx, opens PowerPoint, F5 slideshow, narrates each slide, advances with Right Arrow"
              : "Electron desktop only"
          }
        >
          <Presentation className="h-3.5 w-3.5" />
          Present &amp; narrate my PPTX (all slides)
        </button>
        {presenting && (
          <button
            type="button"
            data-testid="present-deck-stop"
            onClick={stopPresentAll}
            className="inline-flex items-center gap-1.5 rounded-lg border border-red-700 px-2.5 py-1.5 text-xs text-red-200 hover:bg-red-950"
          >
            <Square className="h-3.5 w-3.5" />
            Stop presenting
          </button>
        )}
      </div>
      {status && (
        <p
          data-testid="present-deck-status"
          className={`text-[11px] ${dark ? "text-amber-300/90" : "text-amber-800"}`}
        >
          {status}
        </p>
      )}
    </div>
  );
}
