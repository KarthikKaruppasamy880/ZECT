import { useCallback, useEffect, useMemo, useState } from "react";
import { FileDown, HelpCircle, Redo2, Save, Undo2 } from "lucide-react";
import SplitPane from "@/components/SplitPane";
import PresentVisualBlocks from "@/components/PresentVisualBlocks";
import PresentEditorRail, { newEditorBlock } from "@/components/PresentEditorRail";
import PresentEditDataTable from "@/components/PresentEditDataTable";
import {
  mentrixAnalyzeDeck,
  mentrixParsePptxFromPath,
  mentrixPresentPptxDownload,
  mentrixPresentQualityGate,
  mentrixPresentSaveNotes,
  mentrixPresentSlideAi,
  mentrixPresentSlidePreview,
  mentrixPresentationAssetUpload,
  type PresentBlock,
  type PresentSlide,
} from "@/lib/api";
import { chartTypeFromPrompt, chartTypeLabel } from "@/lib/presentChartTypes";

type Slide = PresentSlide;
type SlideCache = { sourceFp: string; slides: Slide[] };
type SaveState = "saved" | "saving" | "unsaved";

type PresentEditorProps = {
  pptxPath: string;
  variant?: "review" | "studio";
};

const storageKey = (path: string) => `zect_present_editor:${path}`;
const SELECTABLE = new Set(["chart", "table", "image", "quote", "metric", "shape"]);

const fingerprint = (rows: Slide[]) =>
  rows
    .map((s) => `${s.index}:${s.text || ""}:${s.notes || ""}:${JSON.stringify(s.blocks || [])}`)
    .join("|");

function cloneSlides(rows: Slide[]): Slide[] {
  return rows.map((s) => ({ ...s, blocks: (s.blocks || []).map((b) => ({ ...b, content: { ...(b.content || {}) } })) }));
}

function SlideThumbPreview({ path, index, nonce }: { path: string; index: number; nonce: number }) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    let active = true;
    let created = "";
    mentrixPresentSlidePreview(path, index)
      .then((preview) => {
        const u = preview.url;
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
  }, [path, index, nonce]);
  if (!url) return null;
  return <img src={url} alt="" className="mb-1 h-14 w-full rounded border border-slate-200 object-cover" />;
}

export default function PresentEditor({ pptxPath, variant = "review" }: PresentEditorProps) {
  const studio = variant === "studio";
  const [slides, setSlides] = useState<Slide[]>([]);
  const [selected, setSelected] = useState(0);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [filename, setFilename] = useState("");
  const [sourceFp, setSourceFp] = useState("");
  const [savedFp, setSavedFp] = useState("");
  const [previewUrl, setPreviewUrl] = useState("");
  const [previewKind, setPreviewKind] = useState("");
  const [previewNonce, setPreviewNonce] = useState(0);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [notesOpen, setNotesOpen] = useState(!studio);
  const [chat, setChat] = useState("");
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const [dataTableBlock, setDataTableBlock] = useState<PresentBlock | null>(null);
  const [undoStack, setUndoStack] = useState<Slide[][]>([]);
  const [redoStack, setRedoStack] = useState<Slide[][]>([]);
  const [aiAttach, setAiAttach] = useState<string[]>([]);
  const [aiAttachLabels, setAiAttachLabels] = useState<string[]>([]);
  const [saveState, setSaveState] = useState<SaveState>("saved");
  const [slideEmu, setSlideEmu] = useState({ cx: 9144000, cy: 5143500 });

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
      setSavedFp(fingerprint(next));
      setSlides(next);
      setFilename(parsed.filename || "");
      setSlideEmu({
        cx: parsed.slide_cx && parsed.slide_cx > 0 ? parsed.slide_cx : 9144000,
        cy: parsed.slide_cy && parsed.slide_cy > 0 ? parsed.slide_cy : 5143500,
      });
      setSelected(0);
      setSelectedBlockId(null);
      setUndoStack([]);
      setRedoStack([]);
      setSaveState("saved");
      setStatus(`${next.length} slides · ${parsed.filename || "deck"}`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Could not open deck in editor";
      setSlides([]);
      setStatus(`Parse error: ${msg}`);
    } finally {
      setBusy(false);
    }
  }, [pptxPath]);

  useEffect(() => {
    void load();
  }, [load]);

  const current = slides[selected];
  const selectedBlock = (current?.blocks || []).find((b) => b.id && b.id === selectedBlockId) || null;

  useEffect(() => {
    let active = true;
    let created = "";
    if (!pptxPath || !current) {
      setPreviewUrl("");
      return;
    }
    mentrixPresentSlidePreview(pptxPath, selected, { force: previewNonce > 0 })
      .then((preview) => {
        if (!active) {
          URL.revokeObjectURL(preview.url);
          return;
        }
        created = preview.url;
        setPreviewUrl(preview.url);
        setPreviewKind(preview.kind || "");
      })
      .catch(() => {
        if (active) setPreviewUrl("");
      });
    return () => {
      active = false;
      if (created) URL.revokeObjectURL(created);
    };
  }, [pptxPath, selected, current, previewNonce]);

  const commitSlides = useCallback(
    (updater: (prev: Slide[]) => Slide[], opts?: { skipHistory?: boolean }) => {
      setSlides((prev) => {
        const next = updater(prev);
        persist(pptxPath, next, sourceFp);
        return next;
      });
      if (!opts?.skipHistory) {
        setUndoStack((u) => [...u.slice(-29), cloneSlides(slides)]);
        setRedoStack([]);
      }
      setSaveState("unsaved");
    },
    [pptxPath, persist, sourceFp, slides],
  );

  const patchSlide = (index: number, patch: Partial<Slide>) => {
    commitSlides((prev) => prev.map((s) => (s.index === index ? { ...s, ...patch } : s)));
  };

  const reindex = (rows: Slide[]) => rows.map((s, i) => ({ ...s, index: i }));

  const addSlide = () => {
    if (busy) return;
    commitSlides((prev) => {
      const next = reindex([...prev, { index: prev.length, text: "New slide", notes: "" }]);
      setSelected(next.length - 1);
      return next;
    });
  };

  const deleteSlide = (index: number) => {
    if (busy) return;
    commitSlides((prev) => {
      if (prev.length <= 1) return prev;
      const next = reindex(prev.filter((s) => s.index !== index));
      setSelected((cur) => Math.min(cur, next.length - 1));
      return next;
    });
  };

  const moveSlide = (index: number, dir: -1 | 1) => {
    if (busy) return;
    commitSlides((prev) => {
      const j = index + dir;
      if (j < 0 || j >= prev.length) return prev;
      const copy = [...prev];
      const [row] = copy.splice(index, 1);
      copy.splice(j, 0, row);
      const next = reindex(copy);
      setSelected(j);
      return next;
    });
  };

  const duplicateSlide = (index: number) => {
    if (busy) return;
    commitSlides((prev) => {
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
      setSelected(index + 1);
      return next;
    });
  };

  const undo = useCallback(() => {
    setUndoStack((stack) => {
      if (!stack.length) return stack;
      const prev = stack[stack.length - 1];
      setRedoStack((r) => [...r, cloneSlides(slides)]);
      setSlides(prev);
      persist(pptxPath, prev, sourceFp);
      setSaveState("unsaved");
      return stack.slice(0, -1);
    });
  }, [slides, persist, pptxPath, sourceFp]);

  const redo = useCallback(() => {
    setRedoStack((stack) => {
      if (!stack.length) return stack;
      const next = stack[stack.length - 1];
      setUndoStack((u) => [...u, cloneSlides(slides)]);
      setSlides(next);
      persist(pptxPath, next, sourceFp);
      setSaveState("unsaved");
      return stack.slice(0, -1);
    });
  }, [slides, persist, pptxPath, sourceFp]);

  const save = useCallback(async (rows?: Slide[]) => {
    const payload = rows || slides;
    setBusy(true);
    setSaveState("saving");
    try {
      const out = await mentrixPresentSaveNotes(pptxPath, payload);
      persist(pptxPath, payload, sourceFp);
      setSavedFp(fingerprint(payload));
      setPreviewNonce((n) => n + 1);
      setSaveState("saved");
      setStatus(
        out.ooxml_roundtrip
          ? "Saved into PPTX (notes and slide text)."
          : "Saved notes sidecar (PPTX round-trip unavailable).",
      );
    } catch (e) {
      persist(pptxPath, payload, sourceFp);
      setSaveState("unsaved");
      setStatus(e instanceof Error ? `${e.message} — kept local copy` : "Saved locally");
    } finally {
      setBusy(false);
    }
  }, [pptxPath, slides, sourceFp, persist]);

  const applyAi = async (promptOverride?: string) => {
    if (!current) return;
    const prompt = (promptOverride ?? chat).trim();
    if (!prompt) {
      setStatus("Enter a prompt for this slide.");
      return;
    }
    setBusy(true);
    try {
      const heuristicType = chartTypeFromPrompt(prompt);
      if (heuristicType) {
        applyChartType(heuristicType);
        setStatus(`Chart type set to ${chartTypeLabel(heuristicType)}.`);
        return;
      }
      const out = await mentrixPresentSlideAi({
        prompt,
        slide_text: current.text || "",
        notes: current.notes || "",
        selected_kind: selectedBlock?.kind || "",
        selected_chart_type: String(selectedBlock?.content?.chart_type || ""),
        attach_excerpts: aiAttach,
      });
      if (!out.ok) {
        setStatus(out.message || out.error || "Could not apply a typed patch.");
        return;
      }
      if (out.chart_type) {
        applyChartType(out.chart_type);
        setStatus(`Chart type set to ${chartTypeLabel(out.chart_type)}.`);
        return;
      }
      if (out.layout) {
        setStatus(`Layout ${out.layout} — mapped to imported master placeholders`);
        return;
      }
      if (out.notes || out.text) {
        patchSlide(current.index, {
          ...(out.notes ? { notes: out.notes } : {}),
          ...(out.text ? { text: out.text } : {}),
        });
        setStatus("Applied AI patch to this slide.");
        return;
      }
      const fallback = await mentrixAnalyzeDeck({
        slides,
        notes_blob: [prompt, current.notes || current.text || "", ...aiAttach].filter(Boolean).join("\n\n"),
        audience_id: "exec",
      });
      const improved = fallback.improved_notes?.find((n) => n.index === current.index);
      if (improved?.notes) {
        patchSlide(current.index, { notes: improved.notes });
        setStatus("Applied executive rewrite to speaker notes.");
      } else {
        setStatus("Rewrite returned no notes — original kept.");
      }
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "AI patch failed — model may be offline.");
    } finally {
      setBusy(false);
    }
  };

  const applyChartType = (chartType: string) => {
    if (!current) return;
    const blocks = current.blocks || [];
    const target =
      (selectedBlock?.kind === "chart" ? selectedBlock : null) ||
      [...blocks].reverse().find((b) => b.kind === "chart");
    if (target) {
      const nextBlocks = blocks.map((b) =>
        b.id === target.id ? { ...b, content: { ...(b.content || {}), chart_type: chartType } } : b,
      );
      patchSlide(current.index, { blocks: nextBlocks });
      setSelectedBlockId(target.id || null);
      return;
    }
    const block = newEditorBlock("chart", current.index, {
      title: "New chart",
      chart_type: chartType,
      categories: ["A", "B"],
      series: [{ name: "Series", values: [1, 2] }],
    });
    patchSlide(current.index, { blocks: [...blocks, block] });
    setSelectedBlockId(block.id || null);
  };

  const addBlock = (block: PresentBlock, kindLabel: string) => {
    if (!current) {
      setStatus("No slide to edit — Generate on Create with AI, or wait for the deck to parse.");
      return;
    }
    patchSlide(current.index, { blocks: [...(current.blocks || []), block] });
    setSelectedBlockId(block.id || null);
    setStatus(`${kindLabel} added on this slide — click Save to persist into the PPTX.`);
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
      setSelectedBlockId(nextBlock.id || null);
      setStatus("Image attached to this slide — click Save to persist into the PPTX.");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Image upload failed");
    }
  };

  const onChartClick = (chartType?: string) => {
    const kind = chartType || "column";
    if (!current) return;
    const blocks = current.blocks || [];
    const selected = blocks.find((b) => b.id === selectedBlockId && b.kind === "chart");
    const target = selected || [...blocks].reverse().find((b) => b.kind === "chart");
    if (target) {
      patchSlide(current.index, {
        blocks: blocks.map((b) =>
          b.id === target.id ? { ...b, content: { ...(b.content || {}), chart_type: kind } } : b,
        ),
      });
      setSelectedBlockId(target.id || null);
      setStatus(`Chart type changed to ${chartTypeLabel(kind)} — click Save to persist into the PPTX.`);
      return;
    }
    const block = newEditorBlock("chart", current.index, {
      title: "New chart",
      chart_type: kind,
      categories: ["A", "B"],
      series: [{ name: "Series", values: [1, 2] }],
    });
    addBlock(block, "Chart");
  };

  const visualBlocks = useMemo(
    () => (current?.blocks || []).filter((b) => SELECTABLE.has(String(b.kind))),
    [current],
  );

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
        setDataTableBlock(null);
        return;
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        void save();
        return;
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
        e.preventDefault();
        if (e.shiftKey) redo();
        else undo();
        return;
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") {
        e.preventDefault();
        redo();
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
  }, [save, slides.length, selected, undo, redo]);

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

  const dirty = saveState !== "saved" || (slides.length > 0 && fingerprint(slides) !== savedFp);
  const saveLabel = saveState === "saving" ? "Saving" : dirty ? "Unsaved" : "Saved";

  if (!pptxPath) return null;

  return (
    <div
      className={studio ? "flex h-full min-h-0 flex-col rounded-xl border border-slate-200 bg-white" : "rounded-xl border border-slate-200 bg-white"}
      data-testid="present-editor"
      data-variant={variant}
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-3 py-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">{studio ? filename || "Present Studio" : "Deck editor"}</h3>
          {!studio ? (
            <p className="text-[11px] text-slate-500">
              Review slides here; Generate lives on Create with AI; Voicebox narrates Rehearse.
            </p>
          ) : null}
          <p className="text-[11px] text-slate-500" data-testid="present-editor-status">
            {busy ? "Working…" : status || "Select a slide"}
          </p>
          <p className="text-[11px] font-medium text-teal-800" data-testid="present-editor-save-state">
            {saveLabel}
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <button
            type="button"
            data-testid="present-editor-undo"
            disabled={!undoStack.length}
            onClick={undo}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-40"
          >
            <Undo2 className="h-3.5 w-3.5" /> Undo
          </button>
          <button
            type="button"
            data-testid="present-editor-redo"
            disabled={!redoStack.length}
            onClick={redo}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-40"
          >
            <Redo2 className="h-3.5 w-3.5" /> Redo
          </button>
          <button
            type="button"
            data-testid="present-editor-save"
            disabled={busy || !slides.length}
            onClick={() => void save()}
            className="inline-flex items-center gap-1 rounded-lg bg-teal-700 px-2.5 py-1.5 text-xs text-white hover:bg-teal-800 disabled:opacity-40"
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
            data-testid="present-editor-export"
            disabled={busy || !pptxPath}
            onClick={() => void exportPptx()}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-40"
          >
            <FileDown className="h-3.5 w-3.5" /> Export PPTX
          </button>
        </div>
      </div>
      <div className={studio ? "flex min-h-0 flex-1" : "flex min-h-[280px]"}>
      <SplitPane axis="horizontal" storageKey="zect_present_editor_h" initial={18} min={12} max={36} testId="present-editor-split">
        <ul
          className="h-full overflow-auto border-r border-slate-100 p-1"
          data-testid="present-editor-thumbs"
        >
          {slides.map((s, i) => (
            <li key={s.index}>
              <button
                type="button"
                data-testid={`present-editor-thumb-${s.index}`}
                onClick={() => {
                  setSelected(i);
                  setSelectedBlockId(null);
                }}
                className={`mb-1 w-full rounded-md px-2 py-2 text-left text-[11px] ${
                  selected === i ? "bg-teal-50 text-teal-900" : "text-slate-700 hover:bg-slate-50"
                }`}
              >
                <SlideThumbPreview path={pptxPath} index={s.index} nonce={previewNonce} />
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
            <div className="relative flex aspect-video w-full items-center justify-center overflow-hidden rounded-lg border border-slate-200 bg-slate-100">
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
                Preview unavailable
              </div>
            )}
            {previewKind === "ooxml" ? (
              <p
                className="pointer-events-none absolute bottom-1 left-1 right-1 rounded bg-amber-50/90 px-2 py-0.5 text-[10px] text-amber-900"
                data-testid="present-editor-preview-kind"
              >
                Approximate layout — PowerPoint did not rasterize this slide
              </p>
            ) : null}
            {visualBlocks.length ? (
              <div
                className="absolute inset-0"
                data-testid="present-editor-block-overlay"
              >
                {visualBlocks.map((block, i) => {
                  const selectedHit = block.id === selectedBlockId;
                  const geo = block.geometry;
                  const hasGeo = Boolean(geo && (geo.cx || 0) > 0 && (geo.cy || 0) > 0);
                  const raster = previewKind === "com" || previewKind === "libreoffice";
                  const emuCx = slideEmu.cx || 9144000;
                  const emuCy = slideEmu.cy || 5143500;
                  const style = hasGeo
                    ? {
                        position: "absolute" as const,
                        left: `${(100 * (geo?.x || 0)) / emuCx}%`,
                        top: `${(100 * (geo?.y || 0)) / emuCy}%`,
                        width: `${(100 * (geo?.cx || 1)) / emuCx}%`,
                        height: `${(100 * (geo?.cy || 1)) / emuCy}%`,
                      }
                    : undefined;
                  return (
                    <button
                      key={block.id || `${block.kind}-${i}`}
                      type="button"
                      data-testid={`present-editor-block-hit-${block.kind}`}
                      data-block-id={block.id || `${block.kind}-${i}`}
                      style={style}
                      className={`pointer-events-auto text-left text-[10px] text-teal-900 ${
                        hasGeo
                          ? `rounded border-2 bg-transparent ${
                              selectedHit
                                ? "border-teal-600"
                                : raster
                                  ? "border-teal-400/20"
                                  : "border-teal-400/40"
                            }`
                          : `rounded border-2 bg-teal-500/5 ${selectedHit ? "border-teal-600" : "border-teal-400/70"}`
                      }`}
                      onClick={() => setSelectedBlockId(block.id || null)}
                      onDoubleClick={() => {
                        if (block.kind === "chart" || block.kind === "table") setDataTableBlock(block);
                      }}
                    >
                      {hasGeo ? (
                        <span className="sr-only">{block.kind}</span>
                      ) : raster ? (
                        <span className="sr-only">{block.kind}</span>
                      ) : (
                        <span className="block truncate px-1 py-0.5 uppercase">{block.kind}</span>
                      )}
                    </button>
                  );
                })}
              </div>
            ) : null}
            </div>
            {studio ? (
              <button
                type="button"
                data-testid="present-editor-notes-toggle"
                className="self-start text-[11px] text-teal-800"
                onClick={() => setNotesOpen((v) => !v)}
              >
                {notesOpen ? "Hide speaker notes" : "Speaker notes"}
              </button>
            ) : null}
            {(!studio || notesOpen) ? (
              <>
                <label className="text-[11px] font-medium text-slate-600">
                  Slide text
                  <textarea
                    data-testid="present-editor-text"
                    value={current.text || ""}
                    onChange={(e) => patchSlide(current.index, { text: e.target.value })}
                    rows={studio ? 3 : 5}
                    className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm text-slate-900"
                  />
                </label>
                <label className="text-[11px] font-medium text-slate-600">
                  Speaker notes
                  <textarea
                    data-testid="present-editor-notes"
                    value={current.notes || ""}
                    onChange={(e) => patchSlide(current.index, { notes: e.target.value })}
                    rows={studio ? 3 : 4}
                    className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm text-slate-900"
                  />
                </label>
              </>
            ) : null}
            {!studio ? (
              <PresentVisualBlocks
                blocks={current.blocks || []}
                busy={busy}
                onChange={(next) => patchSlide(current.index, { blocks: next })}
              />
            ) : null}
          </div>
          <PresentEditorRail
            busy={busy}
            chat={chat}
            onChatChange={setChat}
            onRewrite={() => void applyAi()}
            slideLabel={`Slide ${current.index + 1}`}
            selectedLabel={
              selectedBlock
                ? `${selectedBlock.kind}${selectedBlock.kind === "chart" ? ` · ${chartTypeLabel(String(selectedBlock.content?.chart_type || "column"))}` : ""}`
                : undefined
            }
            attachLabels={aiAttachLabels}
            onAttachFiles={async (files) => {
              for (const file of files) {
                try {
                  const text = (await file.text()).slice(0, 12_000);
                  setAiAttach((prev) => [...prev, `# ${file.name}\n${text}`]);
                  setAiAttachLabels((prev) => [...prev, file.name]);
                } catch {
                  setStatus(`Could not read ${file.name}`);
                }
              }
            }}
            onQuickPrompt={(prompt) => {
              setChat(prompt);
              void applyAi(prompt);
            }}
            onAddChart={(chartType) => onChartClick(chartType)}
            onAddTable={() =>
              addBlock(
                newEditorBlock("table", current.index, {
                  headers: ["Item", "Value"],
                  rows: [["Row 1", "—"]],
                }),
                "Table",
              )
            }
            onAddElement={(kind) =>
              addBlock(
                kind === "quote"
                  ? newEditorBlock("quote", current.index, { text: "Quote" })
                  : newEditorBlock("metric", current.index, { label: "Metric", value: "—" }),
                kind === "quote" ? "Quote" : "Metric",
              )
            }
            onAddImage={(file) => void addImageFile(file)}
            onAddText={(role) =>
              addBlock(
                newEditorBlock("quote", current.index, {
                  text: role === "title" ? "Title" : role === "subtitle" ? "Subtitle" : role === "bullets" ? "• Point" : "Body",
                }),
                role,
              )
            }
            onAddShape={(shape) =>
              addBlock(
                newEditorBlock("shape", current.index, { shape, text: shape }),
                shape,
              )
            }
            onApplyLayout={(layout) => setStatus(`Layout ${layout} — mapped to imported master placeholders`)}
          />
          </div>
        ) : (
          <p className="p-4 text-sm text-slate-500" data-testid="present-editor-empty">
            {status.startsWith("Parse error")
              ? status
              : "No slides to edit — Generate on Create with AI, or wait for parse. Chart/Table/Image need a saved slide."}
          </p>
        )}
      </SplitPane>
      </div>
      {dataTableBlock ? (
        <PresentEditDataTable
          block={dataTableBlock}
          onClose={() => setDataTableBlock(null)}
          onSave={(content) => {
            if (!current) return;
            const nextBlocks = (current.blocks || []).map((b) =>
              b.id === dataTableBlock.id ? { ...b, content } : b,
            );
            const nextSlides = slides.map((s) =>
              s.index === current.index ? { ...s, blocks: nextBlocks } : s,
            );
            commitSlides(() => nextSlides);
            setDataTableBlock(null);
            void save(nextSlides);
          }}
        />
      ) : null}
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
              <li>Ctrl+Z / Ctrl+Y — undo / redo</li>
              <li>D — duplicate current slide</li>
              <li>Double-click chart or table — Edit Data Table</li>
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
