import { useState } from "react";
import { GitCompare, Minus, Plus, FileText } from "lucide-react";

/* ---------- Shared types ---------- */

interface DiffLine {
  type: "equal" | "added" | "deleted" | "modified";
  left_line: number | null;
  right_line: number | null;
  left: string;
  right: string;
}

interface DiffStats {
  additions: number;
  deletions: number;
  total_left_lines: number;
  total_right_lines: number;
}

interface GitHubPRFile {
  filename: string;
  status: string;
  additions: number;
  deletions: number;
  changes: number;
  patch: string | null;
}

/* ---------- Props ---------- */

type DiffViewerProps =
  | {
      files: GitHubPRFile[];
      sideBySide?: never;
      unified?: never;
      stats?: never;
      leftLabel?: never;
      rightLabel?: never;
    }
  | {
      files?: never;
      sideBySide: DiffLine[];
      unified: string;
      stats: DiffStats;
      leftLabel?: string;
      rightLabel?: string;
    };

const TYPE_COLORS: Record<string, { bg: string; text: string }> = {
  equal: { bg: "", text: "text-slate-300" },
  added: { bg: "bg-green-900/30", text: "text-green-300" },
  deleted: { bg: "bg-red-900/30", text: "text-red-300" },
  modified: { bg: "bg-yellow-900/20", text: "text-yellow-300" },
};

/* ---------- GitHub PR File Diff ---------- */

function PatchViewer({ files }: { files: GitHubPRFile[] }) {
  const [expandedFile, setExpandedFile] = useState<string | null>(null);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm text-slate-400">
        <GitCompare className="w-4 h-4 text-indigo-400" />
        <span>{files.length} file(s) changed</span>
        <span className="text-green-400">+{files.reduce((s, f) => s + f.additions, 0)}</span>
        <span className="text-red-400">-{files.reduce((s, f) => s + f.deletions, 0)}</span>
      </div>
      {files.map((file) => (
        <div key={file.filename} className="border border-slate-200 rounded-lg overflow-hidden">
          <button
            onClick={() => setExpandedFile(expandedFile === file.filename ? null : file.filename)}
            className="w-full flex items-center justify-between px-4 py-2 bg-slate-50 hover:bg-slate-100 transition-colors"
          >
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-slate-500" />
              <span className="text-sm font-mono text-slate-700">{file.filename}</span>
              <span className={`text-xs px-1.5 py-0.5 rounded ${
                file.status === "added" ? "bg-green-100 text-green-700" :
                file.status === "removed" ? "bg-red-100 text-red-700" :
                "bg-yellow-100 text-yellow-700"
              }`}>
                {file.status}
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="text-green-600">+{file.additions}</span>
              <span className="text-red-600">-{file.deletions}</span>
            </div>
          </button>
          {expandedFile === file.filename && file.patch && (
            <pre className="p-3 text-xs font-mono overflow-x-auto max-h-96 overflow-y-auto bg-slate-900 text-slate-300 whitespace-pre">
              {file.patch}
            </pre>
          )}
        </div>
      ))}
    </div>
  );
}

/* ---------- Side-by-Side Diff ---------- */

function SideBySideViewer({
  sideBySide,
  unified,
  stats,
  leftLabel = "Original",
  rightLabel = "Modified",
}: {
  sideBySide: DiffLine[];
  unified: string;
  stats: DiffStats;
  leftLabel: string;
  rightLabel: string;
}) {
  const [viewMode, setViewMode] = useState<"side" | "unified">("side");

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <GitCompare className="w-5 h-5 text-indigo-400" />
          <div className="flex items-center gap-4 text-sm">
            <span className="flex items-center gap-1 text-green-400">
              <Plus className="w-3 h-3" /> {stats.additions}
            </span>
            <span className="flex items-center gap-1 text-red-400">
              <Minus className="w-3 h-3" /> {stats.deletions}
            </span>
            <span className="text-slate-500">{stats.total_left_lines} → {stats.total_right_lines} lines</span>
          </div>
        </div>
        <div className="flex bg-slate-800 rounded-lg border border-slate-600 p-0.5">
          <button
            onClick={() => setViewMode("side")}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${viewMode === "side" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"}`}
          >
            Side by Side
          </button>
          <button
            onClick={() => setViewMode("unified")}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${viewMode === "unified" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"}`}
          >
            Unified
          </button>
        </div>
      </div>

      {viewMode === "side" ? (
        <div className="border border-slate-700 rounded-lg overflow-hidden">
          <div className="grid grid-cols-2 border-b border-slate-700 bg-slate-800">
            <div className="px-3 py-2 text-xs font-medium text-slate-400 border-r border-slate-700">{leftLabel}</div>
            <div className="px-3 py-2 text-xs font-medium text-slate-400">{rightLabel}</div>
          </div>
          <div className="max-h-[600px] overflow-y-auto font-mono text-xs">
            {sideBySide.map((line, i) => {
              const colors = TYPE_COLORS[line.type] || TYPE_COLORS.equal;
              return (
                <div key={i} className={`grid grid-cols-2 border-b border-slate-800 ${colors.bg}`}>
                  <div className="flex border-r border-slate-700">
                    <span className="w-12 text-right px-2 py-0.5 text-slate-600 bg-slate-900/50 select-none shrink-0">
                      {line.left_line ?? ""}
                    </span>
                    <span className={`px-2 py-0.5 flex-1 ${line.type === "deleted" || line.type === "modified" ? "text-red-300" : colors.text}`}>
                      {line.left}
                    </span>
                  </div>
                  <div className="flex">
                    <span className="w-12 text-right px-2 py-0.5 text-slate-600 bg-slate-900/50 select-none shrink-0">
                      {line.right_line ?? ""}
                    </span>
                    <span className={`px-2 py-0.5 flex-1 ${line.type === "added" || line.type === "modified" ? "text-green-300" : colors.text}`}>
                      {line.right}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="border border-slate-700 rounded-lg overflow-hidden">
          <pre className="p-4 text-xs font-mono text-slate-300 max-h-[600px] overflow-y-auto whitespace-pre-wrap bg-slate-900">
            {unified || "No differences found."}
          </pre>
        </div>
      )}
    </div>
  );
}

/* ---------- Main Component ---------- */

export default function DiffViewer(props: DiffViewerProps) {
  if ("files" in props && props.files) {
    return <PatchViewer files={props.files} />;
  }

  if ("sideBySide" in props && props.sideBySide) {
    return (
      <SideBySideViewer
        sideBySide={props.sideBySide}
        unified={props.unified}
        stats={props.stats}
        leftLabel={props.leftLabel || "Original"}
        rightLabel={props.rightLabel || "Modified"}
      />
    );
  }

  return <div className="text-sm text-slate-500">No diff data provided.</div>;
}
