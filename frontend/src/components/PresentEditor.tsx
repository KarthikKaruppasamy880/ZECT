import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, ChevronUp, Copy, FileDown, HelpCircle, Redo2, Save, Trash2, Undo2, ZoomIn, ZoomOut } from "lucide-react";
import SplitPane from "@/components/SplitPane";
import PresentVisualBlocks from "@/components/PresentVisualBlocks";
import PresentEditorRail, { type EditorPaletteTab } from "@/components/PresentEditorRail";
import PresentEditDataTable from "@/components/PresentEditDataTable";
import PresentInsertTableDialog from "@/components/PresentInsertTableDialog";
import PresentInsertDiagramDialog from "@/components/PresentInsertDiagramDialog";
import PresentInsertIconDialog from "@/components/PresentInsertIconDialog";
import { defaultChartContent, defaultDiagramContent, defaultIconContent, defaultTableContent, defaultTextContent } from "@/lib/presentInsertDefaults";
import { createEditorBlock } from "@/lib/presentInsertPlacement";
import { applyEditorLayout, type EditorLayoutId } from "@/lib/presentLayouts";
import { critiqueSlideBlocks, qualityStatusMessage } from "@/lib/presentEditorQuality";
import PresentDocumentCanvas from "@/components/PresentDocumentCanvas";
import PresentEditorSidePanel from "@/components/PresentEditorSidePanel";
import { geometryValid, NUDGE_EMU } from "@/lib/presentGeometry";
import { documentBlocks, materializeSlideBlocks, mergeEditorCache, slideTextFromBlocks, slideThemeColors } from "@/lib/presentDocument";
import { blockLayerLabel } from "@/lib/presentEditorLabels";
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

export type PresentEditorVariant = "review" | "edit" | "studio";

type PresentEditorProps = {
  pptxPath: string;
  variant?: PresentEditorVariant;
};

const storageKey = (path: string) => `zect_present_editor:${path}`;

const fingerprint = (rows: Slide[]) =>
  rows
    .map((s) => `${s.index}:${s.text || ""}:${s.notes || ""}:${JSON.stringify(s.blocks || [])}`)
    .join("|");

function cloneSlides(rows: Slide[]): Slide[] {
  return rows.map((s) => ({ ...s, blocks: (s.blocks || []).map((b) => ({ ...b, content: { ...(b.content || {}) } })) }));
}

function SlideThumbPreview({
  pptxPath,
  slideIndex,
  refreshKey,
}: {
  pptxPath: string;
  slideIndex: number;
  refreshKey: string;
}) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    let objectUrl: string | null = null;
    void mentrixPresentSlidePreview(pptxPath, slideIndex)
      .then(({ url: nextUrl }) => {
        if (!alive) {
          URL.revokeObjectURL(nextUrl);
          return;
        }
        objectUrl = nextUrl;
        setUrl(nextUrl);
      })
      .catch(() => {
        if (alive) setUrl(null);
      });
    return () => {
      alive = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [pptxPath, slideIndex, refreshKey]);

  return (
    <div className="relative mb-1 aspect-video w-full overflow-hidden rounded border border-slate-100 bg-white">
      {url ? (
        <img src={url} alt="" className="h-full w-full object-contain" data-testid={`present-editor-thumb-img-${slideIndex}`} />
      ) : (
        <div className="flex h-full items-center justify-center text-[9px] text-slate-400">…</div>
      )}
    </div>
  );
}

const previewKindLabel = (kind: string) => {
  if (kind === "com") return "PowerPoint preview";
  if (kind === "libreoffice") return "LibreOffice preview";
  return "Template preview";
};

export default function PresentEditor({ pptxPath, variant = "review" }: PresentEditorProps) {
  const studio = variant === "studio";
  const visualEdit = variant === "edit" || variant === "studio";
  const reviewPreview = variant === "review";
  const [slides, setSlides] = useState<Slide[]>([]);
  const [selected, setSelected] = useState(0);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [filename, setFilename] = useState("");
  const [sourceFp, setSourceFp] = useState("");
  const [savedFp, setSavedFp] = useState("");
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [propsAdvanced, setPropsAdvanced] = useState(false);
  const showImplementationFields = variant === "studio" && propsAdvanced;
  const [railTab, setRailTab] = useState<EditorPaletteTab>("ai");
  const [chat, setChat] = useState("");
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const [dataTableBlock, setDataTableBlock] = useState<PresentBlock | null>(null);
  const [tableInsertOpen, setTableInsertOpen] = useState(false);
  const [diagramInsertOpen, setDiagramInsertOpen] = useState(false);
  const [iconInsertOpen, setIconInsertOpen] = useState(false);
  const [undoStack, setUndoStack] = useState<Slide[][]>([]);
  const [redoStack, setRedoStack] = useState<Slide[][]>([]);
  const [aiAttach, setAiAttach] = useState<string[]>([]);
  const [aiAttachLabels, setAiAttachLabels] = useState<string[]>([]);
  const [saveState, setSaveState] = useState<SaveState>("saved");
  const [slideEmu, setSlideEmu] = useState({ cx: 9144000, cy: 5143500 });
  const [zoom, setZoom] = useState(100);
  const canvasFrameRef = useRef<HTMLDivElement | null>(null);
  const [slidePreviewUrl, setSlidePreviewUrl] = useState<string | null>(null);
  const [slidePreviewKind, setSlidePreviewKind] = useState("");
  const [slidePreviewError, setSlidePreviewError] = useState(false);

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
            next = mergeEditorCache(next, saved);
          } else if (
            saved &&
            !Array.isArray(saved) &&
            Array.isArray(saved.slides) &&
            saved.slides.length === next.length
          ) {
            next = mergeEditorCache(next, saved.slides);
          }
        }
      } catch {
        /* keep parsed */
      }
      next = materializeSlideBlocks(next, {
        cx: parsed.slide_cx && parsed.slide_cx > 0 ? parsed.slide_cx : 9144000,
        cy: parsed.slide_cy && parsed.slide_cy > 0 ? parsed.slide_cy : 5143500,
      });
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

  useEffect(() => {
    if (studio && selectedBlockId) setRailTab("properties");
  }, [selectedBlockId, studio]);

  useEffect(() => {
    if (!pptxPath || !slides.length) {
      setSlidePreviewUrl(null);
      setSlidePreviewKind("");
      setSlidePreviewError(false);
      return;
    }
    let alive = true;
    let objectUrl: string | null = null;
    setSlidePreviewError(false);
    void mentrixPresentSlidePreview(pptxPath, selected)
      .then(({ url, kind }) => {
        if (!alive) {
          URL.revokeObjectURL(url);
          return;
        }
        objectUrl = url;
        setSlidePreviewUrl(url);
        setSlidePreviewKind(kind);
      })
      .catch(() => {
        if (alive) {
          setSlidePreviewUrl(null);
          setSlidePreviewKind("");
          setSlidePreviewError(true);
        }
      });
    return () => {
      alive = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [pptxPath, selected, slides.length, savedFp]);

  const current = slides[selected];
  const selectedBlock =
    (current?.blocks || []).find((b) => b.id && b.id === selectedBlockId) ||
    documentBlocks(current, slideEmu).find((b) => b.id && b.id === selectedBlockId) ||
    null;

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
        blocks: documentBlocks(current, slideEmu),
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
        const next = applyEditorLayout(current, out.layout as EditorLayoutId);
        patchSlide(current.index, { blocks: next.blocks, layout_intent: next.layout_intent, text: next.text });
        setStatus(`Layout applied: ${out.layout}`);
        return;
      }
      if (Array.isArray(out.blocks) && out.blocks.length) {
        const placed = out.blocks.map((b, i) => {
          const prior = out.blocks!.slice(0, i);
          if (b.geometry?.cx && b.geometry?.cy) return b;
          return createEditorBlock(String(b.kind || "text"), current.index, (b.content || {}) as Record<string, unknown>, prior);
        });
        patchSlide(current.index, {
          blocks: placed,
          ...(out.text ? { text: out.text } : {}),
          ...(out.notes ? { notes: out.notes } : {}),
        });
        const qc = critiqueSlideBlocks(placed);
        const warn = qualityStatusMessage(qc);
        setStatus(warn || `Applied ${out.action || "document"} patch to this slide.`);
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
    const block = createEditorBlock("chart", current.index, defaultChartContent(chartType), blocks);
    patchSlide(current.index, { blocks: [...blocks, block] });
    setSelectedBlockId(block.id || null);
    setDataTableBlock(block);
  };

  const addBlock = (block: PresentBlock, kindLabel: string) => {
    if (!current) {
      setStatus("No slide to edit — Generate on Create with AI, or wait for the deck to parse.");
      return;
    }
    const nextBlocks = [...(current.blocks || []), block];
    patchSlide(current.index, { blocks: nextBlocks });
    setSelectedBlockId(block.id || null);
    const qc = critiqueSlideBlocks(nextBlocks);
    const warn = qualityStatusMessage(qc);
    setStatus(warn || `${kindLabel} added on this slide — click Save to persist into the PPTX.`);
  };

  const addImageFile = async (file: File) => {
    if (!current) return;
    try {
      const out = await mentrixPresentationAssetUpload(file);
      if (!out.asset_id) {
        setStatus(out.error || "Image rejected");
        return;
      }
      const blocks = current.blocks || [];
      const nextBlock = createEditorBlock(
        "image",
        current.index,
        { asset_id: out.asset_id, alt: file.name },
        blocks.filter((b) => b.kind !== "image"),
      );
      const without = blocks.filter((b) => b.kind !== "image");
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
    const block = createEditorBlock("chart", current.index, defaultChartContent(kind), blocks);
    addBlock(block, "Chart");
    setDataTableBlock(block);
    setRailTab("properties");
  };

  const visualBlocks = useMemo(() => documentBlocks(current, slideEmu), [current, slideEmu]);

  const patchSelectedGeometry = useCallback(
    (next: { x: number; y: number; cx: number; cy: number }, opts?: { skipHistory?: boolean }) => {
      if (!current || !selectedBlockId) return;
      commitSlides(
        (prev) =>
          prev.map((s) =>
            s.index === current.index
              ? {
                  ...s,
                  blocks: (s.blocks || []).map((b) =>
                    b.id === selectedBlockId ? { ...b, geometry: next } : b,
                  ),
                }
              : s,
          ),
        opts,
      );
    },
    [commitSlides, current, selectedBlockId],
  );

  const patchSelectedContent = useCallback(
    (patch: Record<string, unknown>) => {
      if (!current || !selectedBlockId) return;
      commitSlides((prev) =>
        prev.map((s) =>
          s.index === current.index
            ? {
                ...s,
                blocks: (s.blocks || []).map((b) =>
                  b.id === selectedBlockId ? { ...b, content: { ...(b.content || {}), ...patch } } : b,
                ),
              }
            : s,
        ),
      );
    },
    [commitSlides, current, selectedBlockId],
  );

  const deleteSelectedBlock = useCallback(() => {
    if (!current || !selectedBlockId) return;
    commitSlides((prev) =>
      prev.map((s) =>
        s.index === current.index
          ? { ...s, blocks: (s.blocks || []).filter((b) => b.id !== selectedBlockId) }
          : s,
      ),
    );
    setSelectedBlockId(null);
    setStatus("Removed selected object.");
  }, [commitSlides, current, selectedBlockId]);

  const duplicateSelectedBlock = useCallback(() => {
    if (!current || !selectedBlockId) return;
    const src = (current.blocks || []).find((b) => b.id === selectedBlockId);
    if (!src) return;
    const geo = src.geometry || { x: 0, y: 0, cx: 1, cy: 1 };
    const copy: PresentBlock = {
      ...src,
      id: `${src.id || src.kind}_dup_${Date.now()}`,
      geometry: geometryValid(geo)
        ? { ...geo, x: (geo.x || 0) + NUDGE_EMU, y: (geo.y || 0) + NUDGE_EMU }
        : geo,
    };
    commitSlides((prev) =>
      prev.map((s) => (s.index === current.index ? { ...s, blocks: [...(s.blocks || []), copy] } : s)),
    );
    setSelectedBlockId(copy.id || null);
  }, [commitSlides, current, selectedBlockId]);

  const reorderBlock = useCallback(
    (id: string, dir: -1 | 1) => {
      if (!current) return;
      commitSlides((prev) =>
        prev.map((s) => {
          if (s.index !== current.index) return s;
          const blocks = [...(s.blocks || [])];
          const i = blocks.findIndex((b) => b.id === id);
          const j = i + dir;
          if (i < 0 || j < 0 || j >= blocks.length) return s;
          const [row] = blocks.splice(i, 1);
          blocks.splice(j, 0, row);
          return { ...s, blocks };
        }),
      );
    },
    [commitSlides, current],
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
        setSelectedBlockId(null);
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
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "d") {
        e.preventDefault();
        if (selectedBlockId) duplicateSelectedBlock();
        else duplicateSlide(selected);
        return;
      }
      if (typing) return;
      if ((e.key === "Delete" || e.key === "Backspace") && selectedBlockId) {
        e.preventDefault();
        deleteSelectedBlock();
        return;
      }
      const geo = selectedBlock?.geometry;
      if (selectedBlockId && geometryValid(geo)) {
        const dx = e.key === "ArrowLeft" ? -NUDGE_EMU : e.key === "ArrowRight" ? NUDGE_EMU : 0;
        const dy = e.key === "ArrowUp" ? -NUDGE_EMU : e.key === "ArrowDown" ? NUDGE_EMU : 0;
        if (dx || dy) {
          e.preventDefault();
          patchSelectedGeometry({
            x: (geo?.x || 0) + dx,
            y: (geo?.y || 0) + dy,
            cx: geo?.cx || 1,
            cy: geo?.cy || 1,
          });
          return;
        }
      }
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
  }, [
    save,
    slides.length,
    selected,
    undo,
    redo,
    selectedBlockId,
    selectedBlock,
    deleteSelectedBlock,
    duplicateSelectedBlock,
    patchSelectedGeometry,
  ]);

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
      setStatus(`Exported ${name || filename || "zect-deck.pptx"} (${blob.size.toLocaleString()} bytes)`);
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
      className={visualEdit ? "flex h-full min-h-0 flex-col rounded-xl border border-slate-200 bg-white" : "rounded-xl border border-slate-200 bg-white"}
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
            data-testid="present-editor-zoom-out"
            onClick={() => setZoom((z) => Math.max(50, z - 10))}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
          >
            <ZoomOut className="h-3.5 w-3.5" /> Zoom out
          </button>
          <button
            type="button"
            data-testid="present-editor-zoom-fit"
            onClick={() => setZoom(100)}
            className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
          >
            {zoom}%
          </button>
          <button
            type="button"
            data-testid="present-editor-zoom-in"
            onClick={() => setZoom((z) => Math.min(200, z + 10))}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
          >
            <ZoomIn className="h-3.5 w-3.5" /> Zoom in
          </button>
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
          {!reviewPreview ? (
          <button
            type="button"
            data-testid="present-editor-export"
            disabled={busy || !pptxPath}
            onClick={() => void exportPptx()}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-40"
          >
            <FileDown className="h-3.5 w-3.5" /> Export PPTX
          </button>
          ) : (
            <span className="text-[10px] text-slate-500" data-testid="present-editor-export-hint">
              Export on Export tab
            </span>
          )}
        </div>
      </div>
      <div className={visualEdit ? "flex min-h-0 flex-1" : "flex min-h-[280px]"}>
      <SplitPane axis="horizontal" storageKey="zect_present_editor_h" initial={14} min={10} max={28} testId="present-editor-split">
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
                <SlideThumbPreview pptxPath={pptxPath} slideIndex={s.index} refreshKey={savedFp} />
                <div className="font-medium">Slide {s.index + 1}</div>
                {!studio ? (
                  <div className="line-clamp-2 text-slate-500">{s.text || s.notes || "(empty)"}</div>
                ) : null}
              </button>
              <div className="mb-1 flex items-center justify-center gap-0.5 px-1">
                <button
                  type="button"
                  title="Move up"
                  aria-label="Move slide up"
                  data-testid={`present-editor-up-${s.index}`}
                  disabled={busy || i === 0}
                  className="rounded p-0.5 text-slate-500 hover:bg-slate-100 disabled:opacity-30"
                  onClick={() => moveSlide(i, -1)}
                >
                  <ChevronUp className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  title="Move down"
                  aria-label="Move slide down"
                  data-testid={`present-editor-down-${s.index}`}
                  disabled={busy || i >= slides.length - 1}
                  className="rounded p-0.5 text-slate-500 hover:bg-slate-100 disabled:opacity-30"
                  onClick={() => moveSlide(i, 1)}
                >
                  <ChevronDown className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  title="Duplicate slide"
                  aria-label="Duplicate slide"
                  data-testid={`present-editor-duplicate-${s.index}`}
                  disabled={busy}
                  className="rounded p-0.5 text-slate-500 hover:bg-slate-100 disabled:opacity-30"
                  onClick={() => duplicateSlide(i)}
                >
                  <Copy className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  title="Delete slide"
                  aria-label="Delete slide"
                  data-testid={`present-editor-delete-${s.index}`}
                  disabled={busy || slides.length <= 1}
                  className="rounded p-0.5 text-rose-700 hover:bg-rose-50 disabled:opacity-30"
                  onClick={() => deleteSlide(s.index)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
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
          <div className="flex h-full min-w-0 flex-1 flex-col overflow-hidden p-3">
            <div
              ref={canvasFrameRef}
              className="relative flex min-h-0 flex-1 items-center justify-center overflow-hidden rounded-lg border border-slate-200 bg-slate-50"
              data-testid="present-editor-canvas-frame"
            >
              <div
                className="relative aspect-video max-h-full w-full max-w-full"
                style={{ width: studio ? `${zoom}%` : `${zoom}%`, maxWidth: "100%" }}
              >
              <div className="absolute inset-0" data-testid="present-editor-block-overlay">
                {slidePreviewUrl ? (
                  <img
                    src={slidePreviewUrl}
                    alt={`Slide ${selected + 1} preview`}
                    className="absolute inset-0 h-full w-full object-contain bg-white"
                    data-testid="present-editor-slide-preview"
                    data-preview-kind={slidePreviewKind || "ooxml"}
                  />
                ) : null}
                {reviewPreview && slidePreviewError ? (
                  <PresentDocumentCanvas
                    slide={current}
                    slideEmu={slideEmu}
                    selectedId={selectedBlockId}
                    testId="present-editor-canvas"
                    className="h-full w-full"
                    onSelect={(id) => {
                      setSelectedBlockId(id);
                      if (studio && id) setRailTab("properties");
                    }}
                    onChangeText={(id, text) => {
                      const nextBlocks = documentBlocks(current, slideEmu).map((b) =>
                        b.id === id ? { ...b, content: { ...(b.content || {}), text } } : b,
                      );
                      patchSlide(current.index, { blocks: nextBlocks, text: slideTextFromBlocks({ ...current, blocks: nextBlocks }) });
                    }}
                    onDoubleClick={(block) => {
                      if (block.kind === "chart" || block.kind === "table") setDataTableBlock(block);
                    }}
                    onGeometry={(id, geo, opts) => {
                      commitSlides(
                        (prev) =>
                          prev.map((s) =>
                            s.index === current.index
                              ? {
                                  ...s,
                                  blocks: documentBlocks(s, slideEmu).map((b) => (b.id === id ? { ...b, geometry: geo } : b)),
                                }
                              : s,
                          ),
                        opts,
                      );
                    }}
                  />
                ) : visualEdit ? (
                  <PresentDocumentCanvas
                    slide={current}
                    slideEmu={slideEmu}
                    selectedId={selectedBlockId}
                    overlayMode={Boolean(slidePreviewUrl)}
                    testId="present-editor-canvas"
                    className="absolute inset-0 h-full w-full"
                    onSelect={(id) => {
                      setSelectedBlockId(id);
                      if (studio && id) setRailTab("properties");
                    }}
                    onChangeText={(id, text) => {
                      const nextBlocks = documentBlocks(current, slideEmu).map((b) =>
                        b.id === id ? { ...b, content: { ...(b.content || {}), text } } : b,
                      );
                      patchSlide(current.index, { blocks: nextBlocks, text: slideTextFromBlocks({ ...current, blocks: nextBlocks }) });
                    }}
                    onDoubleClick={(block) => {
                      if (block.kind === "chart" || block.kind === "table") setDataTableBlock(block);
                    }}
                    onGeometry={(id, geo, opts) => {
                      commitSlides(
                        (prev) =>
                          prev.map((s) =>
                            s.index === current.index
                              ? {
                                  ...s,
                                  blocks: documentBlocks(s, slideEmu).map((b) => (b.id === id ? { ...b, geometry: geo } : b)),
                                }
                              : s,
                          ),
                        opts,
                      );
                    }}
                  />
                ) : slidePreviewUrl ? null : (
                  <PresentDocumentCanvas
                    slide={current}
                    slideEmu={slideEmu}
                    selectedId={selectedBlockId}
                    testId="present-editor-canvas"
                    className="h-full w-full"
                  />
                )}
                {slidePreviewKind ? (
                  <p
                    className="absolute right-2 top-2 rounded bg-slate-900/75 px-2 py-0.5 text-[10px] text-white"
                    data-testid="present-editor-preview-kind"
                  >
                    {previewKindLabel(slidePreviewKind)}
                  </p>
                ) : null}
                {reviewPreview && slidePreviewError ? (
                  <p className="absolute bottom-2 left-2 rounded bg-amber-50 px-2 py-1 text-[10px] text-amber-900" data-testid="present-editor-preview-fallback">
                    PowerPoint preview unavailable — showing document canvas fallback
                  </p>
                ) : null}
              </div>
              </div>
            </div>
            {showImplementationFields ? (
              <>
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
              </>
            ) : null}
          </div>
          <PresentEditorRail
            studio={studio}
            activeTab={railTab}
            onTabChange={setRailTab}
            busy={busy}
            chat={chat}
            onChatChange={setChat}
            onRewrite={() => void applyAi()}
            slideLabel={`Slide ${current.index + 1}`}
            selectedLabel={selectedBlock ? blockLayerLabel(selectedBlock) : undefined}
            sidePanel={
              visualEdit ? (
                <PresentEditorSidePanel
                  visualBlocks={visualBlocks}
                  selectedBlock={selectedBlock || null}
                  selectedBlockId={selectedBlockId}
                  showAdvanced={propsAdvanced}
                  onToggleAdvanced={() => setPropsAdvanced((v) => !v)}
                  onSelectBlock={setSelectedBlockId}
                  onReorderBlock={reorderBlock}
                  onPatchContent={patchSelectedContent}
                  onPatchGeometry={patchSelectedGeometry}
                  themeColors={slideThemeColors(current)}
                  slideBackground={String(current.background?.fill || "#FFFFFF")}
                  onSlideBackground={(fill) =>
                    patchSlide(current.index, { background: { ...(current.background || {}), fill } })
                  }
                  speakerNotes={current.notes || ""}
                  onSpeakerNotesChange={(value) => patchSlide(current.index, { notes: value })}
                />
              ) : undefined
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
            onAddTable={() => setTableInsertOpen(true)}
            onAddElement={(kind) => {
              const blocks = current?.blocks || [];
              addBlock(
                createEditorBlock(
                  kind,
                  current!.index,
                  kind === "quote" ? { text: "Quote" } : { label: "Metric", value: "0" },
                  blocks,
                ),
                kind === "quote" ? "Quote" : "Metric",
              );
            }}
            onAddImage={(file) => void addImageFile(file)}
            onAddText={(role) => {
              const blocks = current?.blocks || [];
              addBlock(createEditorBlock("text", current!.index, defaultTextContent(role), blocks), role);
            }}
            onAddShape={(shape) => {
              const blocks = current?.blocks || [];
              addBlock(createEditorBlock("shape", current!.index, { shape, text: shape }, blocks), shape);
            }}
            onAddDiagram={() => setDiagramInsertOpen(true)}
            onAddIcon={() => setIconInsertOpen(true)}
            onApplyLayout={(layout) => {
              if (!current) return;
              const next = applyEditorLayout(current, layout);
              patchSlide(current.index, { blocks: next.blocks, layout_intent: next.layout_intent, text: next.text });
              setStatus(`Layout applied: ${layout}`);
            }}
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
      {diagramInsertOpen ? (
        <PresentInsertDiagramDialog
          onClose={() => setDiagramInsertOpen(false)}
          onConfirm={(diagramType, nodes) => {
            if (!current) return;
            const blocks = current.blocks || [];
            const block = createEditorBlock("diagram", current.index, defaultDiagramContent(diagramType, nodes), blocks);
            addBlock(block, "Diagram");
            setDiagramInsertOpen(false);
            setSelectedBlockId(block.id || null);
            setRailTab("properties");
          }}
        />
      ) : null}
      {iconInsertOpen ? (
        <PresentInsertIconDialog
          onClose={() => setIconInsertOpen(false)}
          onConfirm={(iconId) => {
            if (!current) return;
            const blocks = current.blocks || [];
            const block = createEditorBlock("icon", current.index, defaultIconContent(iconId), blocks);
            addBlock(block, "Icon");
            setIconInsertOpen(false);
            setSelectedBlockId(block.id || null);
            setRailTab("properties");
          }}
        />
      ) : null}
      {tableInsertOpen ? (
        <PresentInsertTableDialog
          onClose={() => setTableInsertOpen(false)}
          onConfirm={(rows, cols) => {
            if (!current) return;
            const blocks = current.blocks || [];
            const block = createEditorBlock("table", current.index, defaultTableContent(rows, cols), blocks);
            addBlock(block, "Table");
            setTableInsertOpen(false);
            setDataTableBlock(block);
            setRailTab("properties");
          }}
        />
      ) : null}
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
              <li>← / → — previous / next slide (nudge selected object)</li>
              <li>Ctrl+S — save into PPTX (sidecar fallback)</li>
              <li>Ctrl+Z / Ctrl+Y — undo / redo</li>
              <li>D — duplicate current slide · Ctrl+D — duplicate object</li>
              <li>Delete — remove selected object</li>
              <li>Esc — clear selection</li>
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
