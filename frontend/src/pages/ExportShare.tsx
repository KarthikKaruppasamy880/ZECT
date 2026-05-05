import { useState, useEffect } from "react";
import { Download, FileText, Copy, Check } from "lucide-react";

interface ExportJob {
  id: number;
  export_type: string;
  content_type: string;
  title: string;
  status: string;
  file_size_bytes: number;
  created_at: string;
  completed_at: string | null;
}

const API = import.meta.env.VITE_API_URL ?? "";

export default function ExportShare() {
  const [jobs, setJobs] = useState<ExportJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [customContent, setCustomContent] = useState("");
  const [title, setTitle] = useState("");
  const [exportResult, setExportResult] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/export`);
      if (res.ok) setJobs(await res.json());
    } catch { /* API not available */ }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchJobs(); }, []);

  const createExport = async () => {
    if (!customContent.trim()) return;
    try {
      const res = await fetch(`${API}/api/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content_type: "custom",
          export_type: "markdown",
          title: title || "Custom Export",
          custom_content: customContent,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setExportResult(data.content);
        fetchJobs();
      }
    } catch { /* error */ }
  };

  const copyToClipboard = () => {
    if (exportResult) {
      navigator.clipboard.writeText(exportResult);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const downloadMarkdown = () => {
    if (!exportResult) return;
    const blob = new Blob([exportResult], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title || "export"}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Download className="h-6 w-6 text-green-400" />
          Export / Share
        </h1>
        <p className="text-sm text-slate-400 mt-1">Export plans, reviews, and code as Markdown or PDF</p>
      </div>

      {/* Create Export */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 space-y-4">
        <h3 className="text-white font-semibold">Create Export</h3>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Export title"
          className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg px-3 py-2 text-sm"
        />
        <textarea
          value={customContent}
          onChange={(e) => setCustomContent(e.target.value)}
          placeholder="Paste content to export as Markdown..."
          rows={8}
          className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg px-3 py-2 text-sm font-mono"
        />
        <button onClick={createExport} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500 text-sm font-medium">
          Export as Markdown
        </button>
      </div>

      {/* Export Result */}
      {exportResult && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-white font-semibold">Export Result</h3>
            <div className="flex gap-2">
              <button onClick={copyToClipboard} className="flex items-center gap-1 px-3 py-1.5 bg-slate-700 text-slate-300 rounded-lg hover:bg-slate-600 text-xs">
                {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                {copied ? "Copied!" : "Copy"}
              </button>
              <button onClick={downloadMarkdown} className="flex items-center gap-1 px-3 py-1.5 bg-green-600/20 text-green-400 rounded-lg hover:bg-green-600/30 text-xs border border-green-600/30">
                <Download className="h-3 w-3" /> Download .md
              </button>
            </div>
          </div>
          <pre className="bg-slate-900 border border-slate-700 rounded-lg p-4 text-sm text-slate-300 overflow-x-auto max-h-96">{exportResult}</pre>
        </div>
      )}

      {/* Export History */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-700">
          <h3 className="text-white font-semibold">Export History</h3>
        </div>
        {loading ? (
          <div className="p-8 text-center text-slate-400">Loading...</div>
        ) : jobs.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            <FileText className="h-12 w-12 mx-auto mb-3 opacity-30" />
            <p className="font-medium">No exports yet</p>
            <p className="text-sm mt-1">Create your first export above</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-800">
              <tr className="text-left text-slate-400 text-xs uppercase">
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Format</th>
                <th className="px-4 py-3">Size</th>
                <th className="px-4 py-3">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {jobs.map((j) => (
                <tr key={j.id} className="hover:bg-slate-700/30">
                  <td className="px-4 py-3 text-slate-300">{j.title || "Untitled"}</td>
                  <td className="px-4 py-3 text-slate-400">{j.content_type}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded-full text-xs bg-green-500/20 text-green-400">{j.export_type}</span>
                  </td>
                  <td className="px-4 py-3 text-slate-400">{(j.file_size_bytes / 1024).toFixed(1)} KB</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{j.created_at ? new Date(j.created_at).toLocaleString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
