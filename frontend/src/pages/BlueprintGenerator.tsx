import { useState } from "react";
import { generateBlueprint } from "@/lib/api";
import type { BlueprintResult } from "@/types";
import {
  Sparkles,
  Plus,
  Trash2,
  Copy,
  Check,
  Loader2,
  AlertCircle,
  FileCode,
} from "lucide-react";

export default function BlueprintGenerator() {
  const [repos, setRepos] = useState<{ owner: string; repo: string }[]>([
    { owner: "", repo: "" },
  ]);
  const [result, setResult] = useState<BlueprintResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const addRepo = () => setRepos([...repos, { owner: "", repo: "" }]);
  const removeRepo = (idx: number) => setRepos(repos.filter((_, i) => i !== idx));
  const updateRepo = (idx: number, field: "owner" | "repo", val: string) =>
    setRepos(repos.map((r, i) => (i === idx ? { ...r, [field]: val } : r)));

  const handleGenerate = async () => {
    const valid = repos.filter((r) => r.owner.trim() && r.repo.trim());
    if (valid.length === 0) {
      setError("Add at least one repo with owner and name.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await generateBlueprint(
        valid.map((r) => ({ owner: r.owner.trim(), repo: r.repo.trim() }))
      );
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Blueprint generation failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!result) return;
    await navigator.clipboard.writeText(result.prompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Blueprint Generator</h1>
        <p className="text-gray-500 mt-1">
          Synthesize a GitHub repository into a single copy-paste prompt for AI tools (Cursor,
          Claude Code, Codex, Windsurf, etc.) to vibe-code the project from scratch.
        </p>
      </div>

      {/* Input */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <h2 className="text-sm font-semibold text-gray-700">Repositories to Analyze</h2>
        {repos.map((r, idx) => (
          <div key={idx} className="flex gap-3 items-end">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Owner</label>
              <input
                type="text"
                value={r.owner}
                onChange={(e) => updateRepo(idx, "owner", e.target.value)}
                placeholder="e.g. KarthikKaruppasamy880"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
              />
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Repository</label>
              <input
                type="text"
                value={r.repo}
                onChange={(e) => updateRepo(idx, "repo", e.target.value)}
                placeholder="e.g. ZECT"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
              />
            </div>
            {repos.length > 1 && (
              <button
                onClick={() => removeRepo(idx)}
                className="p-2 text-red-500 hover:bg-red-50 rounded-lg"
              >
                <Trash2 size={16} />
              </button>
            )}
          </div>
        ))}
        <div className="flex gap-3">
          <button
            onClick={addRepo}
            className="px-4 py-2 border border-dashed border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50 flex items-center gap-2"
          >
            <Plus size={14} /> Add Another Repo
          </button>
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="px-5 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2"
          >
            {loading ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Sparkles size={16} />
            )}
            Generate Blueprint
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
          <AlertCircle size={18} className="text-red-500" />
          <span className="text-sm text-red-700">{error}</span>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="p-5 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FileCode size={20} className="text-purple-600" />
              <div>
                <h2 className="font-semibold text-gray-900">Generated Blueprint</h2>
                <p className="text-xs text-gray-500">
                  {result.repos_analyzed} repo(s) analyzed &middot; ~{result.token_estimate.toLocaleString()} tokens
                </p>
              </div>
            </div>
            <button
              onClick={handleCopy}
              className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition ${
                copied
                  ? "bg-green-100 text-green-700"
                  : "bg-purple-600 text-white hover:bg-purple-700"
              }`}
            >
              {copied ? <Check size={16} /> : <Copy size={16} />}
              {copied ? "Copied!" : "Copy to Clipboard"}
            </button>
          </div>
          <div className="p-5">
            <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
              <pre className="text-xs text-gray-700 font-mono whitespace-pre-wrap">
                {result.prompt}
              </pre>
            </div>
            <p className="text-xs text-gray-400 mt-3">
              Paste this prompt into any AI coding tool (Cursor, Claude Code, Codex, Windsurf, etc.)
              to recreate the project structure and start coding.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
