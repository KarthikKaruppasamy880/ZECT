import { useState, useEffect } from "react";
import { Download, FileText, Copy, Check, Info } from "lucide-react";

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
  const [showGuide, setShowGuide] = useState(false);

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
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-green-100 rounded-xl">
            <Download className="h-6 w-6 text-green-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Export / Share</h1>
            <p className="text-sm text-slate-500">Export plans, reviews, and code as Markdown or PDF</p>
          </div>
        </div>
        <button onClick={() => setShowGuide(!showGuide)} className="flex items-center gap-1.5 px-3 py-2 bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200 text-sm">
          <Info className="h-4 w-4" /> Guide
        </button>
      </div>

      {/* Usage Guide */}
      {showGuide && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-5 space-y-2">
          <h3 className="font-semibold text-green-900">How to use Export / Share</h3>
          <ul className="text-sm text-green-800 space-y-1 list-disc list-inside">
            <li><strong>Create an export</strong> — Enter a title and paste any content (code, plans, reviews) into the text area, then click "Export as Markdown".</li>
            <li><strong>Copy to clipboard</strong> — After exporting, use the "Copy" button to copy the formatted Markdown to your clipboard.</li>
            <li><strong>Download as .md</strong> — Click "Download .md" to save the export as a Markdown file to your computer.</li>
            <li><strong>Export history</strong> — All previous exports are listed in the history table below with title, type, size, and timestamp.</li>
            <li><strong>From other pages</strong> — AI-generated content from Ask, Plan, Build, and Review can also be exported directly from those pages.</li>
          </ul>
        </div>
      )}

      {/* Create Export */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-sm">
        <h3 className="text-slate-900 font-semibold">Create Export</h3>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Export title"
          className="w-full border border-slate-300 text-slate-900 rounded-lg px-3 py-2 text-sm"
        />
        <textarea
          value={customContent}
          onChange={(e) => setCustomContent(e.target.value)}
          placeholder="Paste content to export as Markdown..."
          rows={8}
          className="w-full border border-slate-300 text-slate-900 rounded-lg px-3 py-2 text-sm font-mono"
        />
        <button onClick={createExport} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium">
          Export as Markdown
        </button>
      </div>

      {/* Export Result */}
      {exportResult && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="text-slate-900 font-semibold">Export Result</h3>
            <div className="flex gap-2">
              <button onClick={copyToClipboard} className="flex items-center gap-1 px-3 py-1.5 bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200 text-xs">
                {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                {copied ? "Copied!" : "Copy"}
              </button>
              <button onClick={downloadMarkdown} className="flex items-center gap-1 px-3 py-1.5 bg-green-50 text-green-600 rounded-lg hover:bg-green-100 text-xs border border-green-200">
                <Download className="h-3 w-3" /> Download .md
              </button>
            </div>
          </div>
          <pre className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-sm text-slate-700 overflow-x-auto max-h-96">{exportResult}</pre>
        </div>
      )}

      {/* Export History */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div className="px-4 py-3 border-b border-slate-200 bg-slate-50">
          <h3 className="text-slate-900 font-semibold">Export History</h3>
        </div>
        {loading ? (
          <div className="p-8 text-center text-slate-400">Loading...</div>
        ) : jobs.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="h-12 w-12 mx-auto mb-3 text-slate-300" />
            <p className="font-medium text-slate-700">No exports yet</p>
            <p className="text-sm text-slate-500 mt-1">Create your first export above or export content from Ask, Plan, Build, or Review pages.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr className="text-left text-slate-500 text-xs uppercase">
                <th className="px-4 py-3 font-semibold">Title</th>
                <th className="px-4 py-3 font-semibold">Type</th>
                <th className="px-4 py-3 font-semibold">Format</th>
                <th className="px-4 py-3 font-semibold">Size</th>
                <th className="px-4 py-3 font-semibold">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {jobs.map((j) => (
                <tr key={j.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3 text-slate-700 font-medium">{j.title || "Untitled"}</td>
                  <td className="px-4 py-3 text-slate-500">{j.content_type}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700">{j.export_type}</span>
                  </td>
                  <td className="px-4 py-3 text-slate-500">{(j.file_size_bytes / 1024).toFixed(1)} KB</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{j.created_at ? new Date(j.created_at).toLocaleString() : "\u2014"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
