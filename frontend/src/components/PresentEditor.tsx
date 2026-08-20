import { useCallback, useEffect, useState } from "react";
import { FileDown, HelpCircle, Save, Sparkles } from "lucide-react";
import SplitPane from "@/components/SplitPane";
import PresentVisualBlocks from "@/components/PresentVisualBlocks";
import PresentEditorRail, { newEditorBlock } from "@/components/PresentEditorRail";
import {
  mentrixAnalyzeDeck,
  mentrixParsePptxFromPath,
  mentrixPresentPptxDownload,
  mentrixPresentQualityGate,
  mentrixPresentSaveNotes,
  mentrixPresentSlidePreview,
  mentrixPresentationAssetUpload,
  type PresentBlock,
  type PresentSlide,
} from "@/lib/api";

type Slide = PresentSlide;
type SlideCache = { sourceFp: string; slides: Slide[] };

type PresentEditorProps = {
  pptxPath: string;
};

const storageKey = (path: string) => `zect_present_editor:${path}`;

const fingerprint = (rows: Slide[]) =>
  rows
    .map((s) => `${s.index}:${s.text || ""}:${s.notes || ""}:${JSON.stringify(s.blocks || [])}`)
    .join("|");

function SlideThumbPreview({ path, index }: { path: string; index: number }) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    let active = true;
    let created = "";
    mentrixPresentSlidePreview(path, index)
      .then((u) => {
        if (!active) {
          URL.revokeObjectURL(u);
          return;
        }
        created = u;
        setUrl(u);
      })
      .catch(() => {
        if (active) setUrl("");
      });
    return () => {
      active = false;
      if (created) URL.revokeObjectURL(created);
    };
  }, [path, index]);
  if (!url) return null;
  return <img src={url} alt="" className="mb-1 h-14 w-full rounded border border-slate-200 object-cover" />;
}

export default function PresentEditor({ pptxPath }: PresentEditorProps) {
  const [slides, setSlides] = useState<Slide[]>([]);
  const [selected, setSelected] = useState(0);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [filename, setFilename] = useState("");
  const [sourceFp, setSourceFp] = useState("");
  const [previewUrl, setPreviewUrl] = useState("");
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [chat, setChat] = useState("");

  const persist = useCallback((path: string, next: Slide[], fp: string) => {
    try {
      const payload: SlideCache = { sourceFp: fp, slides: next };
      localStorage.setItem(storageKey(path), JSON.stringify(payload));
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
      const fp = fingerprint(next);
      try {
        const cached = localStorage.getItem(storageKey(pptxPath));
        if (cached) {
          const saved = JSON.parse(cached) as SlideCache | Slide[];
          if (Array.isArray(saved) && saved.length === next.length) {
            next = saved;
          } else if (
            saved &&
            !Array.isArray(saved) &&
            saved.sourceFp === fp &&
            Array.isArray(saved.slides)
          ) {
            next = saved.slides;
          }
        }
      } catch {
        /* keep parsed */
      }
      setSourceFp(fp);
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

  useEffect(() => {
    let active = true;
    let created = "";
    if (!pptxPath || !current) {
      setPreviewUrl("");
      return;
    }
    mentrixPresentSlidePreview(pptxPath, selected)
      .then((url) => {
        if (!active) {
          URL.revokeObjectURL(url);
          return;
        }
        created = url;
        setPreviewUrl(url);
      })
      .catch(() => {
        if (active) setPreviewUrl("");
      });
    return () => {
      active = false;
      if (created) URL.revokeObjectURL(created);
    };
  }, [pptxPath, selected, current]);

  const patchSlide = (index: number, patch: Partial<Slide>) => {
    setSlides((prev) => {
      const next = prev.map((s) => (s.index === index ? { ...s, ...patch } : s));
      persist(pptxPath, next, sourceFp);
      return next;
    });
  };

  const reindex = (rows: Slide[]) => rows.map((s, i) => ({ ...s, index: i }));

  const addSlide = () => {
    if (busy) return;
    setSlides((prev) => {
      const next = reindex([...prev, { index: prev.length, text: "New slide", notes: "" }]);
      persist(pptxPath, next, sourceFp);
      setSelected(next.length - 1);
      return next;
    });
  };

  const deleteSlide = (index: number) => {
    if (busy) return;
    setSlides((prev) => {
      if (prev.length <= 1) return prev;
      const next = reindex(prev.filter((s) => s.index !== index));
      persist(pptxPath, next, sourceFp);
      setSelected((cur) => Math.min(cur, next.length - 1));
      return next;
    });
  };

  const moveSlide = (index: number, dir: -1 | 1) => {
    if (busy) return;
    setSlides((prev) => {
      const j = index + dir;
      if (j < 0 || j >= prev.length) return prev;
      const copy = [...prev];
      const [row] = copy.splice(index, 1);
      copy.splice(j, 0, row);
      const next = reindex(copy);
      persist(pptxPath, next, sourceFp);
      setSelected(j);
      return next;
    });
  };

  const duplicateSlide = (index: number) => {
    if (busy) return;
    setSlides((prev) => {
      const src = prev[index];
      if (!src) return prev;
      const copy: Slide = {
        ...src,
        blocks: (src.blocks || []).map((b, i) => ({
          ...b,
          id: `${b.id || b.kind}_dup_${i}`,
          slide_index: index + 1,
        })),
      };
      const next = reindex([...prev.slice(0, index + 1), copy, ...prev.slice(index + 1)]);
      persist(pptxPath, next, sourceFp);
      setSelected(index + 1);
      return next;
    });
  };

  const save = useCallback(async () => {
    setBusy(true);
    try {
      const out = await mentrixPresentSaveNotes(pptxPath, slides);
      persist(pptxPath, slides, sourceFp);
      setStatus(
        out.ooxml_roundtrip
          ? "Saved into PPTX (notes and slide text)."
          : "Saved notes sidecar (PPTX round-trip unavailable).",
      );
    } catch (e) {
      persist(pptxPath, slides, sourceFp);
      setStatus(e instanceof Error ? `${e.message} — kept local copy` : "Saved locally");
    } finally {
      setBusy(false);
    }
  }, [pptxPath, slides, sourceFp, persist]);

  const rewrite = async () => {
    if (!current) return;
    setBusy(true);
    try {
      const out = await mentrixAnalyzeDeck({
        slides,
        notes_blob: [chat.trim(), current.notes || current.text || ""].filter(Boolean).join("\n\n"),
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

  const addBlock = (block: PresentBlock) => {
    if (!current) return;
    patchSlide(current.index, { blocks: [...(current.blocks || []), block] });
  };

  const addImageFile = async (file: File) => {
    if (!current) return;
    try {
      const out = await mentrixPresentationAssetUpload(file);
      if (!out.asset_id) {
        setStatus(out.error || "Image rejected");
        return;
      }
      const nextBlock = newEditorBlock("image", current.index, { asset_id: out.asset_id, alt: file.name });
      const without = (current.blocks || []).filter((b) => b.kind !== "image");
      patchSlide(current.index, { blocks: [...without, nextBlock] });
      setStatus("Image attached to this slide.");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Image upload failed");
    }
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      const typing = t?.tagName === "INPUT" || t?.tagName === "TEXTAREA" || Boolean(t?.isContentEditable);
      if (e.key === "?" && !typing && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        setShortcutsOpen(true);
        return;
      }
      if (e.key === "Escape") {
        setShortcutsOpen(false);
        return;
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        void save();
        return;
      }
      if (typing) return;
      if (e.key === "ArrowRight" || e.key === "PageDown") {
        e.preventDefault();
        setSelected((s) => Math.min(s + 1, Math.max(0, slides.length - 1)));
      }
      if (e.key === "ArrowLeft" || e.key === "PageUp") {
        e.preventDefault();
        setSelected((s) => Math.max(s - 1, 0));
      }
      if (e.key.toLowerCase() === "d" && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        duplicateSlide(selected);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [save, slides.length, selected]);

  const exportPptx = async () => {
    setBusy(true);
    try {
      const gate = await mentrixPresentQualityGate(pptxPath);
      if (gate.export_blocked || gate.hard_blocked) {
        setStatus(
          `Export blocked: ${(gate.hard_findings || []).join(", ") || "critical quality"}. Accepting warnings cannot override this.`,
        );
        return;
      }
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
            data-testid="present-editor-shortcuts"
            onClick={() => setShortcutsOpen(true)}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
            title="Keyboard shortcuts"
          >
            <HelpCircle className="h-3.5 w-3.5" /> ?
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
                <SlideThumbPreview path={pptxPath} index={s.index} />
                <div className="font-medium">Slide {s.index + 1}</div>
                <div className="line-clamp-3 text-slate-500">{s.text || s.notes || "(empty)"}</div>
              </button>
              <div className="mb-1 flex gap-1 px-1">
                <button type="button" data-testid={`present-editor-up-${s.index}`} disabled={busy} className="text-[10px] text-slate-500 disabled:opacity-40" onClick={() => moveSlide(i, -1)}>
                  Up
                </button>
                <button type="button" data-testid={`present-editor-down-${s.index}`} disabled={busy} className="text-[10px] text-slate-500 disabled:opacity-40" onClick={() => moveSlide(i, 1)}>
                  Down
                </button>
                <button type="button" data-testid={`present-editor-delete-${s.index}`} disabled={busy} className="text-[10px] text-rose-700 disabled:opacity-40" onClick={() => deleteSlide(s.index)}>
                  Delete
                </button>
                <button type="button" data-testid={`present-editor-duplicate-${s.index}`} disabled={busy} className="text-[10px] text-slate-500 disabled:opacity-40" onClick={() => duplicateSlide(i)}>
                  Duplicate
                </button>
              </div>
            </li>
          ))}
          <li>
            <button
              type="button"
              data-testid="present-editor-add-slide"
              disabled={busy}
              onClick={addSlide}
              className="mb-1 w-full rounded-md border border-dashed border-slate-300 px-2 py-2 text-left text-[11px] text-slate-600 hover:bg-slate-50 disabled:opacity-40"
            >
              Add slide
            </button>
          </li>
        </ul>
        {current ? (
          <div className="flex h-full min-w-0">
          <div className="flex h-full min-w-0 flex-1 flex-col gap-2 overflow-auto p-3">
            <div className="flex aspect-video w-full items-center justify-center overflow-hidden rounded-lg border border-slate-200 bg-slate-100">
            {previewUrl ? (
              <img
                src={previewUrl}
                alt={`Slide ${current.index + 1} canvas`}
                data-testid="present-editor-canvas"
                className="max-h-full max-w-full object-contain"
              />
            ) : (
              <div
                data-testid="present-editor-canvas"
                className="px-3 py-8 text-center text-xs text-slate-500"
              >
                Slide canvas preview unavailable — showing extracted text.
              </div>
            )}
            </div>
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
            <PresentVisualBlocks
              blocks={current.blocks || []}
              busy={busy}
              onChange={(next) => patchSlide(current.index, { blocks: next })}
            />
          </div>
          <PresentEditorRail
            busy={busy}
            chat={chat}
            onChatChange={setChat}
            onRewrite={() => void rewrite()}
            onAddChart={() =>
              addBlock(
                newEditorBlock("chart", current.index, {
                  title: "New chart",
                  categories: ["A", "B"],
                  series: [{ name: "Series", values: [1, 2] }],
                }),
              )
            }
            onAddTable={() =>
              addBlock(
                newEditorBlock("table", current.index, {
                  headers: ["Item", "Value"],
                  rows: [["Row 1", "—"]],
                }),
              )
            }
            onAddElement={(kind) =>
              addBlock(
                kind === "quote"
                  ? newEditorBlock("quote", current.index, { text: "Quote" })
                  : newEditorBlock("metric", current.index, { label: "Metric", value: "—" }),
              )
            }
            onAddImage={(file) => void addImageFile(file)}
          />
          </div>
        ) : (
          <p className="p-4 text-sm text-slate-500">Generate a deck to edit slides.</p>
        )}
      </SplitPane>
      </div>
      {shortcutsOpen ? (
        <div
          className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 p-4"
          data-testid="present-editor-shortcuts-modal"
          onClick={() => setShortcutsOpen(false)}
        >
          <div
            className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-800 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <h4 className="mb-2 font-semibold">Editor shortcuts</h4>
            <ul className="space-y-1 text-xs text-slate-600">
              <li>← / → — previous / next slide</li>
              <li>Ctrl+S — save into PPTX (sidecar fallback)</li>
              <li>D — duplicate current slide</li>
              <li>Delete on a thumb — remove slide</li>
              <li>? — this help</li>
              <li>Present / Narrate live on Rehearse (Electron F5 / Right)</li>
            </ul>
            <button
              type="button"
              className="mt-3 rounded border border-slate-200 px-2 py-1 text-xs"
              onClick={() => setShortcutsOpen(false)}
            >
              Close
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
