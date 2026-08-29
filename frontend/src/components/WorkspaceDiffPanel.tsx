import { useEffect, useState } from "react";
import { GitCompare, Loader2, RotateCcw, Check } from "lucide-react";
import DiffViewer from "@/components/DiffViewer";
import { diffCompare } from "@/lib/api";
import { applyHunks, parseUnifiedHunks, revertHunks, type DiffHunk } from "@/lib/diffHunks";

type WorkspaceDiffPanelProps = {
  baseline: string;
  content: string;
  fileLabel?: string;
  onContentChange: (next: string) => void;
  onApplySave: () => void | Promise<void>;
  onRevertFile: () => void | Promise<void>;
  saving?: boolean;
};

/**
 * Phase 3 Stage C — diff + per-hunk apply/revert against the editor buffer.
 * Left = baseline (disk at open / last save), right = current editor content.
 */
export default function WorkspaceDiffPanel({
  baseline,
  content,
  fileLabel,
  onContentChange,
  onApplySave,
  onRevertFile,
  saving = false,
}: WorkspaceDiffPanelProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [diff, setDiff] = useState<{
    unified: string;
    side_by_side: any[];
    stats: any;
  } | null>(null);
  const [hunks, setHunks] = useState<DiffHunk[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      if (baseline === content) {
        setDiff(null);
        setHunks([]);
        setSelected(new Set());
        setError("");
        return;
      }
      setLoading(true);
      setError("");
      try {
        const result = await diffCompare(baseline, content, {
          left_label: "baseline",
          right_label: fileLabel || "editor",
        });
        if (cancelled) return;
        setDiff(result);
        const parsed = parseUnifiedHunks(result.unified || "");
        setHunks(parsed);
        setSelected(new Set(parsed.map((h) => h.id)));
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Diff failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [baseline, content, fileLabel]);

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectedHunks = () => hunks.filter((h) => selected.has(h.id));

  const applySelected = () => {
    const next = applyHunks(baseline, selectedHunks());
    onContentChange(next);
  };

  const revertSelected = () => {
    const next = revertHunks(content, selectedHunks());
    onContentChange(next);
  };

  return (
    <div
      className="flex flex-col h-full min-h-[200px] rounded-lg border border-slate-200 bg-white overflow-hidden"
      data-testid="workspace-diff-panel"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-3 py-1.5">
        <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          <GitCompare className="h-3.5 w-3.5 text-teal-700" />
          Diff / hunks
        </span>
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            disabled={!hunks.length || selected.size === 0}
            onClick={applySelected}
            className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-0.5 text-[11px] text-slate-700 disabled:opacity-40"
            data-testid="workspace-hunk-apply"
            title="Rebuild editor from baseline applying only selected hunks"
          >
            <Check className="h-3 w-3" />
            Apply hunks
          </button>
          <button
            type="button"
            disabled={!hunks.length || selected.size === 0}
            onClick={revertSelected}
            className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-0.5 text-[11px] text-slate-700 disabled:opacity-40"
            data-testid="workspace-hunk-revert"
            title="Remove selected hunks from the current editor buffer"
          >
            <RotateCcw className="h-3 w-3" />
            Revert hunks
          </button>
          <button
            type="button"
            disabled={saving || baseline === content}
            onClick={() => void onApplySave()}
            className="rounded bg-slate-900 px-2 py-0.5 text-[11px] text-white disabled:opacity-40"
            data-testid="workspace-diff-apply-save"
          >
            Apply &amp; Save
          </button>
          <button
            type="button"
            disabled={saving}
            onClick={() => void onRevertFile()}
            className="rounded border border-red-200 px-2 py-0.5 text-[11px] text-red-700 disabled:opacity-40"
            data-testid="workspace-diff-revert-file"
          >
            Revert file
          </button>
        </div>
      </div>

      {error ? (
        <p className="px-3 py-2 text-xs text-red-600" role="alert">
          {error}
        </p>
      ) : null}

      {loading ? (
        <div className="flex-1 flex items-center justify-center text-xs text-slate-500 gap-2">
          <Loader2 className="h-3.5 w-3.5 animate-spin" /> Computing diff…
        </div>
      ) : baseline === content ? (
        <div className="flex-1 flex items-center justify-center text-xs text-slate-500 p-4">
          No local edits vs baseline. Edit the file or open a dirty path to review hunks.
        </div>
      ) : (
        <div className="flex flex-1 min-h-0">
          <ul
            className="w-48 shrink-0 overflow-auto border-r border-slate-100 p-2 space-y-1"
            data-testid="workspace-hunk-list"
          >
            {hunks.length === 0 ? (
              <li className="text-[11px] text-slate-500">No hunks parsed.</li>
            ) : (
              hunks.map((h) => (
                <li key={h.id}>
                  <label className="flex items-start gap-1.5 text-[10px] font-mono text-slate-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selected.has(h.id)}
                      onChange={() => toggle(h.id)}
                      className="mt-0.5"
                      data-testid={`workspace-hunk-${h.id}`}
                    />
                    <span className="truncate" title={h.header}>
                      {h.header}
                    </span>
                  </label>
                </li>
              ))
            )}
          </ul>
          <div className="flex-1 overflow-auto p-2 bg-slate-900">
            {diff ? (
              <DiffViewer
                sideBySide={diff.side_by_side}
                unified={diff.unified}
                stats={diff.stats}
                leftLabel="baseline"
                rightLabel={fileLabel || "editor"}
              />
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
