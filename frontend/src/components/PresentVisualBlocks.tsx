import { useEffect, useState } from "react";
import type { PresentBlock } from "@/lib/api";
import { mentrixPresentationAssetBlob, mentrixPresentationAssetUpload } from "@/lib/api";

type PresentVisualBlocksProps = {
  blocks: PresentBlock[];
  busy: boolean;
  onChange: (next: PresentBlock[]) => void;
};

function contentRecord(block: PresentBlock): Record<string, unknown> {
  return block.content && typeof block.content === "object" ? { ...block.content } : {};
}

export default function PresentVisualBlocks({ blocks, busy, onChange }: PresentVisualBlocksProps) {
  const visuals = blocks.filter((b) => ["image", "chart", "table", "metric", "quote", "diagram"].includes(b.kind));
  if (!visuals.length) {
    return (
      <p className="text-[10px] text-slate-400" data-testid="present-editor-visuals-empty">
        No image, chart, or table blocks on this slide yet. Upload an image or generate a native deck with visual
        content.
      </p>
    );
  }
  return (
    <div className="space-y-3" data-testid="present-editor-visuals">
      {visuals.map((block, i) => (
        <VisualCard
          key={block.id || `${block.kind}-${i}`}
          block={block}
          busy={busy}
          onPatch={(patch) => {
            onChange(blocks.map((b) => (b.id === block.id ? { ...b, ...patch } : b)));
          }}
          onDelete={() => onChange(blocks.filter((b) => b.id !== block.id))}
        />
      ))}
    </div>
  );
}

type CardProps = {
  block: PresentBlock;
  busy: boolean;
  onPatch: (patch: Partial<PresentBlock>) => void;
  onDelete: () => void;
};

function VisualCard({ block, busy, onPatch, onDelete }: CardProps) {
  const content = contentRecord(block);
  const provenance = block.provenance?.source || "generated";
  return (
    <div className="rounded-md border border-slate-200 p-2" data-testid={`present-editor-block-${block.kind}`}>
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="text-[11px] font-semibold uppercase text-slate-600">
          {block.kind} · {provenance}
        </span>
        <button
          type="button"
          data-testid={`present-editor-${block.kind}-delete`}
          disabled={busy}
          onClick={onDelete}
          className="text-[10px] text-rose-700 disabled:opacity-40"
        >
          Delete
        </button>
      </div>
      {block.kind === "image" ? <ImageFields block={block} busy={busy} onPatch={onPatch} /> : null}
      {block.kind === "chart" ? (
        <div className="space-y-1">
          <label className="block text-[11px] text-slate-600">
            Chart title
            <input
              data-testid="present-editor-chart-title"
              disabled={busy}
              value={String(content.title || "")}
              onChange={(e) => onPatch({ content: { ...content, title: e.target.value } })}
              className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
            />
          </label>
          <label className="block text-[11px] text-slate-600">
            Categories (comma)
            <input
              data-testid="present-editor-chart-categories"
              disabled={busy}
              value={(Array.isArray(content.categories) ? content.categories : []).map(String).join(", ")}
              onChange={(e) =>
                onPatch({
                  content: {
                    ...content,
                    categories: e.target.value.split(",").map((c) => c.trim()).filter(Boolean),
                  },
                })
              }
              className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
            />
          </label>
        </div>
      ) : null}
      {block.kind === "table" ? (
        <label className="block text-[11px] text-slate-600">
          Table (TSV)
          <textarea
            data-testid="present-editor-table-data"
            disabled={busy}
            rows={4}
            value={tableTsv(content)}
            onChange={(e) => onPatch({ content: tsvToTable(content, e.target.value) })}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1 font-mono text-xs"
          />
        </label>
      ) : null}
      {block.kind === "metric" ? (
        <p className="text-sm text-slate-800" data-testid="present-editor-metric">
          {String(content.label || "Metric")}: {String(content.value || "—")}
        </p>
      ) : null}
      {block.kind === "quote" ? (
        <p className="text-sm italic text-slate-800" data-testid="present-editor-quote">
          {String(content.text || "")}
        </p>
      ) : null}
    </div>
  );
}

function ImageFields({
  block,
  busy,
  onPatch,
}: {
  block: PresentBlock;
  busy: boolean;
  onPatch: (patch: Partial<PresentBlock>) => void;
}) {
  const content = contentRecord(block);
  const assetId = String(content.asset_id || "");
  const [src, setSrc] = useState("");
  useEffect(() => {
    let url = "";
    if (!assetId) return;
    void mentrixPresentationAssetBlob(assetId)
      .then((next) => {
        url = next;
        setSrc(next);
      })
      .catch(() => setSrc(""));
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [assetId]);
  return (
    <div className="space-y-1">
      {src ? (
        <img src={src} alt={String(content.alt || "Slide image")} className="max-h-36 rounded border" data-testid="present-editor-image-preview" />
      ) : (
        <p className="text-[11px] text-slate-500">{assetId ? `asset ${assetId.slice(0, 12)}…` : "No image asset"}</p>
      )}
      <input
        type="file"
        accept="image/png,image/jpeg,image/gif,image/webp"
        data-testid="present-editor-image-upload"
        disabled={busy}
        onChange={async (e) => {
          const file = e.target.files?.[0];
          e.target.value = "";
          if (!file) return;
          if (file.name.toLowerCase().endsWith(".svg")) return;
          const out = await mentrixPresentationAssetUpload(file);
          if (out.asset_id) {
            onPatch({
              content: { ...content, asset_id: out.asset_id },
              provenance: { source: "upload", generated: false },
              validation: { ok: true, errors: [] },
            });
          }
        }}
      />
    </div>
  );
}

function tableTsv(content: Record<string, unknown>): string {
  const headers = Array.isArray(content.headers) ? content.headers.map(String) : [];
  const rows = Array.isArray(content.rows) ? content.rows : [];
  const lines = [headers.join("\t")];
  for (const row of rows) {
    if (Array.isArray(row)) lines.push(row.map(String).join("\t"));
  }
  return lines.join("\n");
}

function tsvToTable(content: Record<string, unknown>, raw: string): Record<string, unknown> {
  const lines = raw.split(/\r?\n/).filter((ln) => ln.trim());
  if (!lines.length) return { ...content, headers: [], rows: [] };
  const headers = lines[0].split("\t").map((c) => c.slice(0, 80));
  const rows = lines.slice(1, 13).map((ln) => ln.split("\t").map((c) => c.slice(0, 120)));
  return { ...content, headers, rows };
}
