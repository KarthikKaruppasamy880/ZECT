import { useState, type ReactNode } from "react";
import type { PresentBlock } from "@/lib/api";
import { PRESENT_CHART_TYPES } from "@/lib/presentChartTypes";
import { createEditorBlock } from "@/lib/presentInsertPlacement";

/** @deprecated Use createEditorBlock from presentInsertPlacement */
export function newEditorBlock(
  kind: string,
  slideIndex: number,
  content: Record<string, unknown>,
  existingBlocks: PresentBlock[] = [],
): PresentBlock {
  return createEditorBlock(kind, slideIndex, content, existingBlocks);
}

export type EditorPaletteTab = "ai" | "properties" | "insert" | "blocks" | "texts" | "charts" | "tables" | "images" | "elements" | "layers";

type PresentEditorRailProps = {
  busy: boolean;
  chat: string;
  onChatChange: (value: string) => void;
  onRewrite: () => void;
  onAddChart: (chartType?: string) => void;
  onAddTable: () => void;
  onAddElement: (kind: "quote" | "metric") => void;
  onAddImage: (file: File) => void;
  onAddText?: (role: "title" | "subtitle" | "bullets" | "quote" | "body") => void;
  onAddShape?: (shape: "rect" | "ellipse" | "arrow") => void;
  onAddDiagram?: () => void;
  onAddIcon?: () => void;
  onApplyLayout?: (layout: "title_body" | "split_image" | "two_col") => void;
  slideLabel?: string;
  selectedLabel?: string;
  attachLabels?: string[];
  onAttachFiles?: (files: File[]) => void;
  onQuickPrompt?: (prompt: string) => void;
  sidePanel?: ReactNode;
  studio?: boolean;
  activeTab?: EditorPaletteTab;
  onTabChange?: (tab: EditorPaletteTab) => void;
};

const STUDIO_TABS: Array<{ id: EditorPaletteTab; label: string }> = [
  { id: "ai", label: "AI" },
  { id: "properties", label: "Properties" },
  { id: "insert", label: "Insert" },
];

const REVIEW_TABS: Array<{ id: EditorPaletteTab; label: string }> = [
  { id: "ai", label: "AI" },
  { id: "blocks", label: "Blocks" },
  { id: "texts", label: "Texts" },
  { id: "charts", label: "Charts" },
  { id: "tables", label: "Tables" },
  { id: "images", label: "Images" },
  { id: "elements", label: "Elements" },
  { id: "layers", label: "Layers" },
];

const QUICK_PROMPTS = [
  { id: "rewrite", label: "Rewrite this slide", prompt: "Rewrite speaker notes for an executive audience." },
  { id: "layout", label: "Suggest a layout", prompt: "Apply title + body layout on this slide." },
  { id: "notes", label: "Tighten notes", prompt: "Rewrite speaker notes shorter, keep facts from attached sources only." },
  { id: "diagram", label: "Bullets to diagram", prompt: "Turn these bullets into a diagram." },
  { id: "table", label: "Add comparison table", prompt: "Add a comparison table from this slide." },
  { id: "density", label: "Reduce density", prompt: "Reduce density — keep the first three points." },
];

function InsertPanel({
  busy,
  onAddChart,
  onAddTable,
  onAddElement,
  onAddImage,
  onAddText,
  onAddShape,
  onAddDiagram,
  onAddIcon,
  onApplyLayout,
}: Pick<
  PresentEditorRailProps,
  | "busy"
  | "onAddChart"
  | "onAddTable"
  | "onAddElement"
  | "onAddImage"
  | "onAddText"
  | "onAddShape"
  | "onAddDiagram"
  | "onAddIcon"
  | "onApplyLayout"
>) {
  return (
    <div className="space-y-2">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Insert</p>
      <p className="text-[10px] text-slate-500">Layouts</p>
      {(
        [
          ["title_body", "Title + body"],
          ["split_image", "Split image"],
          ["two_col", "Two column"],
        ] as const
      ).map(([id, label]) => (
        <button
          key={id}
          type="button"
          data-testid={`present-editor-layout-${id}`}
          disabled={busy}
          onClick={() => onApplyLayout?.(id)}
          className="block w-full rounded border border-slate-200 px-2 py-1 text-left text-[11px] text-slate-700 hover:bg-slate-50 disabled:opacity-40"
        >
          {label}
        </button>
      ))}
      <p className="pt-1 text-[10px] text-slate-500">Text</p>
      {(["title", "subtitle", "bullets", "quote", "body"] as const).map((role) => (
        <button
          key={role}
          type="button"
          data-testid={`present-editor-text-${role}`}
          disabled={busy}
          onClick={() => onAddText?.(role)}
          className="block w-full rounded border border-slate-200 px-2 py-1 text-left text-[11px] capitalize text-slate-700 hover:bg-slate-50 disabled:opacity-40"
        >
          {role}
        </button>
      ))}
      <p className="pt-1 text-[10px] text-slate-500">Charts</p>
      {PRESENT_CHART_TYPES.slice(0, 6).map((row) => (
        <button
          key={row.id}
          type="button"
          data-testid={row.id === "column" ? "present-editor-add-chart" : `present-editor-chart-${row.id}`}
          disabled={busy}
          onClick={() => onAddChart(row.id)}
          className="block w-full rounded border border-slate-200 px-2 py-1 text-left text-[11px] text-slate-700 hover:bg-slate-50 disabled:opacity-40"
        >
          {row.label}
        </button>
      ))}
      <button
        type="button"
        data-testid="present-editor-add-table"
        disabled={busy}
        onClick={onAddTable}
        className="block w-full rounded border border-slate-200 px-2 py-1 text-left text-[11px] text-slate-700 hover:bg-slate-50 disabled:opacity-40"
      >
        Table
      </button>
      <button
        type="button"
        data-testid="present-editor-add-quote"
        disabled={busy}
        onClick={() => onAddElement("quote")}
        className="block w-full rounded border border-slate-200 px-2 py-1 text-left text-[11px] text-slate-700 hover:bg-slate-50 disabled:opacity-40"
      >
        Quote
      </button>
      <button
        type="button"
        data-testid="present-editor-add-metric"
        disabled={busy}
        onClick={() => onAddElement("metric")}
        className="block w-full rounded border border-slate-200 px-2 py-1 text-left text-[11px] text-slate-700 hover:bg-slate-50 disabled:opacity-40"
      >
        Metric
      </button>
      <label className="block rounded border border-slate-200 px-2 py-1 text-[11px] text-slate-700 hover:bg-slate-50">
        Image
        <input
          type="file"
          accept="image/png,image/jpeg,image/gif,image/webp"
          data-testid="present-editor-add-image"
          disabled={busy}
          className="mt-1 block w-full text-[10px]"
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = "";
            if (file && !file.name.toLowerCase().endsWith(".svg")) onAddImage(file);
          }}
        />
      </label>
      <button
        type="button"
        data-testid="present-editor-add-diagram"
        disabled={busy}
        onClick={() => onAddDiagram?.()}
        className="block w-full rounded border border-slate-200 px-2 py-1 text-left text-[11px] text-slate-700 hover:bg-slate-50 disabled:opacity-40"
      >
        Diagram
      </button>
      <button
        type="button"
        data-testid="present-editor-add-icon"
        disabled={busy}
        onClick={() => onAddIcon?.()}
        className="block w-full rounded border border-slate-200 px-2 py-1 text-left text-[11px] text-slate-700 hover:bg-slate-50 disabled:opacity-40"
      >
        Icon
      </button>
      {(["rect", "ellipse", "arrow"] as const).map((shape) => (
        <button
          key={shape}
          type="button"
          data-testid={`present-editor-shape-${shape}`}
          disabled={busy}
          onClick={() => onAddShape?.(shape)}
          className="block w-full rounded border border-slate-200 px-2 py-1 text-left text-[11px] capitalize text-slate-700 hover:bg-slate-50 disabled:opacity-40"
        >
          {shape}
        </button>
      ))}
    </div>
  );
}

export default function PresentEditorRail({
  busy,
  chat,
  onChatChange,
  onRewrite,
  onAddChart,
  onAddTable,
  onAddElement,
  onAddImage,
  onAddText,
  onAddShape,
  onAddDiagram,
  onAddIcon,
  onApplyLayout,
  slideLabel,
  selectedLabel,
  attachLabels,
  onAttachFiles,
  onQuickPrompt,
  sidePanel,
  studio = false,
  activeTab: controlledTab,
  onTabChange,
}: PresentEditorRailProps) {
  const [internalTab, setInternalTab] = useState<EditorPaletteTab>("ai");
  const tab = controlledTab ?? internalTab;
  const setTab = (next: EditorPaletteTab) => {
    onTabChange?.(next);
    if (controlledTab === undefined) setInternalTab(next);
  };
  const tabs = studio ? STUDIO_TABS : REVIEW_TABS;
  const propertiesTab = studio ? tab === "properties" : tab === "layers";

  return (
    <aside
      className={`flex shrink-0 flex-col gap-2 overflow-auto border-l border-slate-100 p-2 ${studio ? "w-72" : "w-64"}`}
      data-testid="present-editor-rail"
    >
      <div className="flex flex-wrap gap-1" data-testid="present-editor-palette">
        {tabs.map((item) => (
          <button
            key={item.id}
            type="button"
            data-testid={`present-editor-tab-${item.id === "properties" ? "layers" : item.id}`}
            onClick={() => setTab(item.id)}
            className={`rounded px-2 py-1 text-[11px] font-medium ${
              tab === item.id ? "bg-teal-800 text-white" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>
      {tab === "ai" ? (
        <>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Slide AI</p>
          <p className="text-xs font-medium text-slate-800" data-testid="present-editor-ai-intro">
            What can I do for your deck today?
          </p>
          {slideLabel ? (
            <span
              className="inline-flex w-fit rounded-full bg-teal-50 px-2 py-0.5 text-[10px] text-teal-900"
              data-testid="present-editor-ai-slide-chip"
            >
              {slideLabel}
            </span>
          ) : null}
          {selectedLabel ? (
            <span
              className="inline-flex w-fit rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-700"
              data-testid="present-editor-ai-object-chip"
            >
              Selected: {selectedLabel}
            </span>
          ) : null}
          <textarea
            data-testid="present-editor-chat"
            value={chat}
            onChange={(e) => onChatChange(e.target.value)}
            rows={4}
            placeholder="Rewrite this slide, change the chart to radar, or tighten speaker notes…"
            className="w-full rounded border border-slate-300 px-2 py-1.5 text-xs"
          />
          <label className="text-[10px] text-slate-600">
            Attach source files
            <input
              type="file"
              multiple
              accept=".txt,.md,.csv,.json"
              data-testid="present-editor-ai-attach"
              className="mt-1 block w-full text-[10px]"
              onChange={(e) => {
                const files = Array.from(e.target.files || []);
                e.target.value = "";
                if (files.length) onAttachFiles?.(files);
              }}
            />
          </label>
          {attachLabels?.length ? (
            <p className="text-[10px] text-slate-500" data-testid="present-editor-ai-attach-names">
              {attachLabels.join(" · ")}
            </p>
          ) : (
            <p className="text-[10px] text-slate-400">Facts come from attached docs / ContextPack only — no invented KPIs.</p>
          )}
          <div className="flex flex-wrap gap-1">
            {QUICK_PROMPTS.map((row) => (
              <button
                key={row.id}
                type="button"
                data-testid={`present-editor-ai-quick-${row.id}`}
                disabled={busy}
                onClick={() => onQuickPrompt?.(row.prompt)}
                className="rounded border border-slate-200 px-1.5 py-0.5 text-[10px] text-slate-700 hover:bg-slate-50 disabled:opacity-40"
              >
                {row.label}
              </button>
            ))}
          </div>
          <button
            type="button"
            data-testid="present-editor-chat-apply"
            disabled={busy}
            onClick={onRewrite}
            className="rounded-lg border border-teal-200 bg-teal-50 px-2 py-1.5 text-[11px] text-teal-900 hover:bg-teal-100 disabled:opacity-40"
          >
            Apply to slide
          </button>
        </>
      ) : null}
      {tab === "insert" && studio ? (
        <InsertPanel
          busy={busy}
          onAddChart={onAddChart}
          onAddTable={onAddTable}
          onAddElement={onAddElement}
          onAddImage={onAddImage}
          onAddText={onAddText}
          onAddShape={onAddShape}
          onAddDiagram={onAddDiagram}
          onAddIcon={onAddIcon}
          onApplyLayout={onApplyLayout}
        />
      ) : null}
      {tab === "blocks" && !studio ? (
        <>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Master layouts</p>
          {(
            [
              ["title_body", "Title + body"],
              ["split_image", "Split image"],
              ["two_col", "Two column"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              data-testid={`present-editor-layout-${id}`}
              disabled={busy}
              onClick={() => onApplyLayout?.(id)}
              className="rounded border border-slate-200 px-2 py-1 text-[11px] text-slate-700 hover:bg-slate-50 disabled:opacity-40"
            >
              {label}
            </button>
          ))}
        </>
      ) : null}
      {tab === "texts" && !studio ? (
        <>
          {(["title", "subtitle", "bullets", "quote", "body"] as const).map((role) => (
            <button
              key={role}
              type="button"
              data-testid={`present-editor-text-${role}`}
              disabled={busy}
              onClick={() => onAddText?.(role)}
              className="rounded border border-slate-200 px-2 py-1 text-[11px] capitalize text-slate-700 hover:bg-slate-50 disabled:opacity-40"
            >
              {role}
            </button>
          ))}
        </>
      ) : null}
      {tab === "charts" && !studio ? (
        <>
          {PRESENT_CHART_TYPES.map((row) => (
            <button
              key={row.id}
              type="button"
              data-testid={row.id === "column" ? "present-editor-add-chart" : `present-editor-chart-${row.id}`}
              disabled={busy}
              onClick={() => onAddChart(row.id)}
              className="rounded border border-slate-200 px-2 py-1 text-left text-[11px] text-slate-700 hover:bg-slate-50 disabled:opacity-40"
            >
              {row.label}
            </button>
          ))}
        </>
      ) : null}
      {tab === "tables" && !studio ? (
        <button
          type="button"
          data-testid="present-editor-add-table"
          disabled={busy}
          onClick={onAddTable}
          className="rounded border border-slate-200 px-2 py-1 text-[11px] text-slate-700 hover:bg-slate-50 disabled:opacity-40"
        >
          Table
        </button>
      ) : null}
      {tab === "images" && !studio ? (
        <label className="rounded border border-slate-200 px-2 py-1 text-[11px] text-slate-700 hover:bg-slate-50">
          Image
          <input
            type="file"
            accept="image/png,image/jpeg,image/gif,image/webp"
            data-testid="present-editor-add-image"
            disabled={busy}
            className="mt-1 block w-full text-[10px]"
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (file && !file.name.toLowerCase().endsWith(".svg")) onAddImage(file);
            }}
          />
        </label>
      ) : null}
      {tab === "elements" && !studio ? (
        <>
          <button
            type="button"
            data-testid="present-editor-add-quote"
            disabled={busy}
            onClick={() => onAddElement("quote")}
            className="rounded border border-slate-200 px-2 py-1 text-[11px] text-slate-700 hover:bg-slate-50 disabled:opacity-40"
          >
            Quote
          </button>
          <button
            type="button"
            data-testid="present-editor-add-metric"
            disabled={busy}
            onClick={() => onAddElement("metric")}
            className="rounded border border-slate-200 px-2 py-1 text-[11px] text-slate-700 hover:bg-slate-50 disabled:opacity-40"
          >
            Metric
          </button>
          <button
            type="button"
            data-testid="present-editor-add-diagram"
            disabled={busy}
            onClick={() => onAddDiagram?.()}
            className="rounded border border-slate-200 px-2 py-1 text-[11px] text-slate-700 hover:bg-slate-50 disabled:opacity-40"
          >
            Diagram
          </button>
          {(["rect", "ellipse", "arrow"] as const).map((shape) => (
            <button
              key={shape}
              type="button"
              data-testid={`present-editor-shape-${shape}`}
              disabled={busy}
              onClick={() => onAddShape?.(shape)}
              className="rounded border border-slate-200 px-2 py-1 text-[11px] capitalize text-slate-700 hover:bg-slate-50 disabled:opacity-40"
            >
              {shape}
            </button>
          ))}
        </>
      ) : null}
      {propertiesTab ? sidePanel : null}
    </aside>
  );
}
