import type { PresentBlock } from "@/lib/api";

type PresentEditorRailProps = {
  busy: boolean;
  chat: string;
  onChatChange: (value: string) => void;
  onRewrite: () => void;
  onAddChart: () => void;
  onAddTable: () => void;
  onAddElement: (kind: "quote" | "metric") => void;
  onAddImage: (file: File) => void;
};

export function newEditorBlock(kind: string, slideIndex: number, content: Record<string, unknown>): PresentBlock {
  return {
    id: `blk_${slideIndex}_${kind}_${Date.now()}`,
    kind,
    slide_index: slideIndex,
    content,
    provenance: { source: "editor", generated: false },
    validation: { ok: true, errors: [] },
  };
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
}: PresentEditorRailProps) {
  return (
    <aside
      className="flex w-52 shrink-0 flex-col gap-2 overflow-auto border-l border-slate-100 p-2"
      data-testid="present-editor-rail"
    >
      <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">New chat</p>
      <textarea
        data-testid="present-editor-chat"
        value={chat}
        onChange={(e) => onChatChange(e.target.value)}
        rows={3}
        placeholder="Ask for an executive rewrite of this slide…"
        className="w-full rounded border border-slate-300 px-2 py-1.5 text-xs"
      />
      <button
        type="button"
        data-testid="present-editor-chat-apply"
        disabled={busy}
        onClick={onRewrite}
        className="rounded-lg border border-teal-200 bg-teal-50 px-2 py-1.5 text-[11px] text-teal-900 hover:bg-teal-100 disabled:opacity-40"
      >
        Apply rewrite
      </button>
      <p className="mt-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Add</p>
      <button
        type="button"
        data-testid="present-editor-add-chart"
        disabled={busy}
        onClick={onAddChart}
        className="rounded border border-slate-200 px-2 py-1 text-[11px] text-slate-700 hover:bg-slate-50 disabled:opacity-40"
      >
        Chart
      </button>
      <button
        type="button"
        data-testid="present-editor-add-table"
        disabled={busy}
        onClick={onAddTable}
        className="rounded border border-slate-200 px-2 py-1 text-[11px] text-slate-700 hover:bg-slate-50 disabled:opacity-40"
      >
        Table
      </button>
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
    </aside>
  );
}
