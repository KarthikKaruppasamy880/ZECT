/**
 * Companion Present Deck — open prepared PPTX + Zoom (Electron) and narrate notes (Chatterbox).
 */
import { useEffect, useState } from "react";
import { Presentation, Mic, MonitorPlay } from "lucide-react";
import { speakMentrix } from "@/mentrix/speak";

const STORAGE_KEY = "zect_mentrix_present_deck_path";
const NOTES_KEY = "zect_mentrix_present_deck_notes";

type Props = {
  variant?: "dark" | "light";
};

export default function PresentDeckPanel({ variant = "dark" }: Props) {
  const [path, setPath] = useState("");
  const [notes, setNotes] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const isDesktop = typeof window !== "undefined" && !!window.zectDesktop?.isDesktopApp;
  const dark = variant === "dark";

  useEffect(() => {
    try {
      setPath(localStorage.getItem(STORAGE_KEY) || "");
      setNotes(localStorage.getItem(NOTES_KEY) || "");
    } catch {
      /* ignore */
    }
  }, []);

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
    const res = (await computer(action, args)) as { ok?: boolean; error?: string };
    if (res?.ok === false) {
      setStatus(String(res.error || "desktop_failed"));
      return { ok: false as const, error: String(res.error || "desktop_failed") };
    }
    return { ok: true as const };
  };

  const openPresentation = async () => {
    setBusy(true);
    setStatus("");
    try {
      const target = path.trim();
      if (!target) {
        setStatus("Enter a .pptx path under Desktop, Documents, or Downloads.");
        return;
      }
      const res = await runComputer("open_presentation", { path: target });
      if (res.ok) setStatus("Opened presentation in PowerPoint. Share that window in Zoom.");
    } finally {
      setBusy(false);
    }
  };

  const openZoom = async () => {
    setBusy(true);
    setStatus("");
    try {
      const app =
        typeof navigator !== "undefined" && /Mac/i.test(navigator.platform)
          ? "zoom.us"
          : "Zoom.exe";
      const res = await runComputer("open_app", { app });
      if (res.ok) setStatus("Opened Zoom. Join your meeting and share the PowerPoint window.");
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
      await speakMentrix(text.slice(0, 2000), true);
      setStatus("Narrating talking points with your default Chatterbox voice.");
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Narrate failed");
    } finally {
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
        Share the PowerPoint window in Zoom yourself; Mentrix opens apps and narrates.
      </p>
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
        Talking points
        <textarea
          data-testid="present-deck-notes"
          value={notes}
          onChange={(e) => persistNotes(e.target.value)}
          rows={3}
          placeholder="Key points to narrate with your cloned voice…"
          className={
            dark
              ? "mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100"
              : "mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-xs"
          }
        />
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
        >
          <Mic className="h-3.5 w-3.5" />
          Narrate talking points
        </button>
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
