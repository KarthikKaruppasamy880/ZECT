import { useState } from "react";
import { ChevronDown, ChevronRight, Plus, Minus, FileText } from "lucide-react";
import type { GitHubPRFile } from "@/types";

function statusColor(status: string) {
  switch (status) {
    case "added":
      return "text-green-600 bg-green-50";
    case "removed":
      return "text-red-600 bg-red-50";
    case "modified":
      return "text-yellow-600 bg-yellow-50";
    case "renamed":
      return "text-blue-600 bg-blue-50";
    default:
      return "text-slate-600 bg-slate-50";
  }
}

function parsePatch(patch: string) {
  const lines: { type: "add" | "del" | "ctx" | "hdr"; content: string; oldNum?: number; newNum?: number }[] = [];
  let oldLine = 0;
  let newLine = 0;
  for (const raw of patch.split("\n")) {
    if (raw.startsWith("@@")) {
      const m = raw.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
      if (m) {
        oldLine = parseInt(m[1], 10);
        newLine = parseInt(m[2], 10);
      }
      lines.push({ type: "hdr", content: raw });
    } else if (raw.startsWith("+")) {
      lines.push({ type: "add", content: raw.slice(1), newNum: newLine });
      newLine++;
    } else if (raw.startsWith("-")) {
      lines.push({ type: "del", content: raw.slice(1), oldNum: oldLine });
      oldLine++;
    } else {
      lines.push({ type: "ctx", content: raw.startsWith(" ") ? raw.slice(1) : raw, oldNum: oldLine, newNum: newLine });
      oldLine++;
      newLine++;
    }
  }
  return lines;
}

interface FileCardProps {
  file: GitHubPRFile;
}

function FileCard({ file }: FileCardProps) {
  const [open, setOpen] = useState(true);
  const patchLines = file.patch ? parsePatch(file.patch) : [];

  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden bg-white mb-3">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-4 py-2.5 bg-slate-50 hover:bg-slate-100 transition-colors text-left"
      >
        {open ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
        <FileText className="h-4 w-4 text-slate-400" />
        <span className="font-mono text-sm text-slate-800 flex-1 truncate">{file.filename}</span>
        <span className={`text-xs font-medium px-2 py-0.5 rounded ${statusColor(file.status)}`}>
          {file.status}
        </span>
        <span className="text-xs text-green-600 font-mono">+{file.additions}</span>
        <span className="text-xs text-red-600 font-mono">-{file.deletions}</span>
      </button>

      {open && patchLines.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono">
            <tbody>
              {patchLines.map((line, i) => {
                if (line.type === "hdr") {
                  return (
                    <tr key={i} className="bg-blue-50">
                      <td colSpan={3} className="px-3 py-1 text-blue-700">
                        {line.content}
                      </td>
                    </tr>
                  );
                }
                const bg =
                  line.type === "add"
                    ? "bg-green-50"
                    : line.type === "del"
                    ? "bg-red-50"
                    : "";
                const textColor =
                  line.type === "add"
                    ? "text-green-800"
                    : line.type === "del"
                    ? "text-red-800"
                    : "text-slate-700";
                return (
                  <tr key={i} className={bg}>
                    <td className="w-10 text-right pr-2 pl-3 py-0 text-slate-400 select-none border-r border-slate-200">
                      {line.oldNum ?? ""}
                    </td>
                    <td className="w-10 text-right pr-2 pl-1 py-0 text-slate-400 select-none border-r border-slate-200">
                      {line.newNum ?? ""}
                    </td>
                    <td className={`px-3 py-0 whitespace-pre ${textColor}`}>
                      {line.type === "add" && <Plus className="inline h-3 w-3 mr-1" />}
                      {line.type === "del" && <Minus className="inline h-3 w-3 mr-1" />}
                      {line.content}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {open && !file.patch && (
        <p className="px-4 py-3 text-sm text-slate-500 italic">Binary file or no diff available</p>
      )}
    </div>
  );
}

interface DiffViewerProps {
  files: GitHubPRFile[];
}

export default function DiffViewer({ files }: DiffViewerProps) {
  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <h3 className="text-sm font-semibold text-slate-700">
          {files.length} file{files.length !== 1 ? "s" : ""} changed
        </h3>
        <span className="text-xs text-green-600 font-mono">
          +{files.reduce((a, f) => a + f.additions, 0)}
        </span>
        <span className="text-xs text-red-600 font-mono">
          -{files.reduce((a, f) => a + f.deletions, 0)}
        </span>
      </div>
      {files.map((file) => (
        <FileCard key={file.filename} file={file} />
      ))}
    </div>
  );
}
