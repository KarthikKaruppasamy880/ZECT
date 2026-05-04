import { useState } from "react";
import { Copy, Check, Maximize2, Minimize2, Download } from "lucide-react";

interface CodeOutputProps {
  code: string;
  language?: string;
  title?: string;
  maxHeight?: string;
}

export default function CodeOutput({
  code,
  language = "text",
  title,
  maxHeight = "400px",
}: CodeOutputProps) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const ext = language === "typescript" || language === "tsx" ? "ts" : language === "python" ? "py" : "txt";
    const blob = new Blob([code], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `generated-code.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-700 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800 border-b border-slate-700">
        <span className="text-sm text-slate-400 font-mono">
          {title || language}
        </span>
        <div className="flex items-center gap-1">
          <button
            onClick={handleCopy}
            className={`p-1.5 rounded text-xs flex items-center gap-1 transition ${
              copied
                ? "text-green-400 bg-green-900/30"
                : "text-slate-400 hover:text-white hover:bg-slate-700"
            }`}
            title="Copy to clipboard"
          >
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            <span className="hidden sm:inline">{copied ? "Copied" : "Copy"}</span>
          </button>
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-1.5 rounded text-slate-400 hover:text-white hover:bg-slate-700 transition"
            title={expanded ? "Collapse" : "Expand"}
          >
            {expanded ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
          </button>
          <button
            onClick={handleDownload}
            className="p-1.5 rounded text-slate-400 hover:text-white hover:bg-slate-700 transition"
            title="Download"
          >
            <Download className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Code content */}
      <pre
        className="p-4 overflow-auto text-sm text-slate-200 font-mono whitespace-pre-wrap"
        style={{ maxHeight: expanded ? "none" : maxHeight }}
      >
        <code>{code}</code>
      </pre>
    </div>
  );
}
