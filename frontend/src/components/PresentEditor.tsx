import { useCallback, useEffect, useState } from "react";
import { FileDown, Save, Sparkles } from "lucide-react";
import SplitPane from "@/components/SplitPane";
import {
  mentrixAnalyzeDeck,
  mentrixParsePptxFromPath,
  mentrixPresentPptxDownload,
  mentrixPresentSaveNotes,
} from "@/lib/api";

type Slide = { index: number; notes?: string; text?: string };

type PresentEditorProps = {
  pptxPath: string;
};

const storageKey = (path: string) => `zect_present_editor:${path}`;

export default function PresentEditor({ pptxPath }: PresentEditorProps) {
  const [slides, setSlides] = useState<Slide[]>([]);
  const [selected, setSelected] = useState(0);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [filename, setFilename] = useState("");

  const persist = useCallback((path: string, next: Slide[]) => {
    try {
      localStorage.setItem(storageKey(path), JSON.stringify(next));
    } catch {
      /* ignore */
    }
  }, []);

  const load = useCallback(async () => {
    if (!pptxPath) return;
    setBusy(true);
    setStatus("");
    try {
      const parsed = await mentrixParsePptxFromPath(pptxPath);
      let next = parsed.slides || [];
      try {
        const cached = localStorage.getItem(storageKey(pptxPath));
        if (cached) {
          const saved = JSON.parse(cached) as Slide[];
          if (Array.isArray(saved) && saved.length === next.length) next = saved;
        }
      } catch {
        /* keep parsed */
      }
      setSlides(next);
      setFilename(parsed.filename || "");
      setSelected(0);
      setStatus(`${next.length} slides · ${parsed.filename || "deck"}`);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Could not open deck in editor");
    } finally {
      setBusy(false);
    }
  }, [pptxPath]);

  useEffect(() => {
    void load();
  }, [load]);

  const current = slides[selected];

  const patchSlide = (index: number, patch: Partial<Slide>) => {
    setSlides((prev) => {
      const next = prev.map((s) => (s.index === index ? { ...s, ...patch } : s));
      persist(pptxPath, next);
      return next;
    });
  };

  const reindex = (rows: Slide[]) => rows.map((s, i) => ({ ...s, index: i }));

  const addSlide = () => {
    setSlides((prev) => {
      const next = reindex([...prev, { index: prev.length, text: "New slide", notes: "" }]);
      persist(pptxPath, next);
      setSelected(next.length - 1);
      return next;
    });
  };

  const deleteSlide = (index: number) => {
    setSlides((prev) => {
      if (prev.length <= 1) return prev;
      const next = reindex(prev.filter((s) => s.index !== index));
      persist(pptxPath, next);
      setSelected((cur) => Math.min(cur, next.length - 1));
      return next;
    });
  };

  const moveSlide = (index: number, dir: -1 | 1) => {
    setSlides((prev) => {
      const j = index + dir;
      if (j < 0 || j >= prev.length) return prev;
      const copy = [...prev];
      const [row] = copy.splice(index, 1);
      copy.splice(j, 0, row);
      const next = reindex(copy);
      persist(pptxPath, next);
      setSelected(j);
      return next;
    });
  };

  const save = async () => {
    setBusy(true);
    try {
      await mentrixPresentSaveNotes(pptxPath, slides);
      persist(pptxPath, slides);
      setStatus("Saved notes for this deck (leave/return restores them).");
    } catch (e) {
      persist(pptxPath, slides);
      setStatus(e instanceof Error ? `${e.message} — kept local copy` : "Saved locally");
    } finally {
      setBusy(false);
    }
  };

  const rewrite = async () => {
    if (!current) return;
    setBusy(true);
    try {
      const out = await mentrixAnalyzeDeck({
        slides,
        notes_blob: current.notes || current.text || "",
        audience_id: "exec",
      });
      const improved = out.improved_notes?.find((n) => n.index === current.index);
      if (improved?.notes) {
        patchSlide(current.index, { notes: improved.notes });
        setStatus("Applied executive rewrite to speaker notes.");
      } else {
        setStatus("Rewrite returned no notes — original kept.");
      }
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Rewrite failed");
    } finally {
      setBusy(false);
    }
  };

  const exportPptx = async () => {
    setBusy(true);
    try {
      const { blob, filename: name } = await mentrixPresentPptxDownload(pptxPath);
      if (blob.size < 100) throw new Error("Export produced an empty file");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = name || filename || "zect-deck.pptx";
      a.click();
      URL.revokeObjectURL(url);
      setStatus(`Exported ${blob.size} bytes`);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Export failed");
    } finally {
      setBusy(false);
    }
  };

  if (!pptxPath) return null;

  return (
    <div className="rounded-xl border border-slate-200 bg-white" data-testid="present-editor">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-3 py-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Deck editor</h3>
          <p className="text-[11px] text-slate-500" data-testid="present-editor-status">
            {busy ? "Working…" : status || "Select a slide"}
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <button
            type="button"
            data-testid="present-editor-save"
            disabled={busy || !slides.length}
            onClick={() => void save()}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-40"
          >
            <Save className="h-3.5 w-3.5" /> Save
          </button>
          <button
            type="button"
            data-testid="present-editor-rewrite"
            disabled={busy || !current}
            onClick={() => void rewrite()}
            className="inline-flex items-center gap-1 rounded-lg border border-teal-200 bg-teal-50 px-2.5 py-1.5 text-xs text-teal-900 hover:bg-teal-100 disabled:opacity-40"
          >
            <Sparkles className="h-3.5 w-3.5" /> Executive rewrite
          </button>
          <button
            type="button"
            data-testid="present-editor-export"
            disabled={busy || !pptxPath}
            onClick={() => void exportPptx()}
            className="inline-flex items-center gap-1 rounded-lg bg-teal-700 px-2.5 py-1.5 text-xs text-white hover:bg-teal-800 disabled:opacity-40"
          >
            <FileDown className="h-3.5 w-3.5" /> Export PPTX
          </button>
        </div>
      </div>
      <div className="flex min-h-[280px]">
      <SplitPane axis="horizontal" storageKey="zect_present_editor_h" initial={22} min={14} max={40} testId="present-editor-split">
        <ul
          className="h-full overflow-auto border-r border-slate-100 p-1"
          data-testid="present-editor-thumbs"
        >
          {slides.map((s, i) => (
            <li key={s.index}>
              <button
                type="button"
                data-testid={`present-editor-thumb-${s.index}`}
                onClick={() => setSelected(i)}
                className={`mb-1 w-full rounded-md px-2 py-2 text-left text-[11px] ${
                  selected === i ? "bg-teal-50 text-teal-900" : "text-slate-700 hover:bg-slate-50"
                }`}
              >
                <div className="font-medium">Slide {s.index + 1}</div>
                <div className="line-clamp-3 text-slate-500">{s.text || s.notes || "(empty)"}</div>
              </button>
              <div className="mb-1 flex gap-1 px-1">
                <button type="button" data-testid={`present-editor-up-${s.index}`} className="text-[10px] text-slate-500" onClick={() => moveSlide(i, -1)}>
                  Up
                </button>
                <button type="button" data-testid={`present-editor-down-${s.index}`} className="text-[10px] text-slate-500" onClick={() => moveSlide(i, 1)}>
                  Down
                </button>
                <button type="button" data-testid={`present-editor-delete-${s.index}`} className="text-[10px] text-rose-700" onClick={() => deleteSlide(s.index)}>
                  Delete
                </button>
              </div>
            </li>
          ))}
          <li>
            <button
              type="button"
              data-testid="present-editor-add-slide"
              onClick={addSlide}
              className="mb-1 w-full rounded-md border border-dashed border-slate-300 px-2 py-2 text-left text-[11px] text-slate-600 hover:bg-slate-50"
            >
              Add slide
            </button>
          </li>
        </ul>
        {current ? (
          <div className="flex h-full min-w-0 flex-col gap-2 overflow-auto p-3">
            <label className="text-[11px] font-medium text-slate-600">
              Slide text
              <textarea
                data-testid="present-editor-text"
                value={current.text || ""}
                onChange={(e) => patchSlide(current.index, { text: e.target.value })}
                rows={5}
                className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm text-slate-900"
              />
            </label>
            <label className="text-[11px] font-medium text-slate-600">
              Speaker notes
              <textarea
                data-testid="present-editor-notes"
                value={current.notes || ""}
                onChange={(e) => patchSlide(current.index, { notes: e.target.value })}
                rows={4}
                className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm text-slate-900"
              />
            </label>
            <p className="text-[10px] text-slate-400">
              Charts, images, tables, and layout blocks stay in the generated PPTX (not edited here).
            </p>
          </div>
        ) : (
          <p className="p-4 text-sm text-slate-500">Generate a deck to edit slides.</p>
        )}
      </SplitPane>
      </div>
    </div>
  );
}
