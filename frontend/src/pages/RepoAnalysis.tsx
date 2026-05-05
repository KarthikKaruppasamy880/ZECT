import { useState } from "react";
import { analyzeRepo, analyzeMultiRepo } from "@/lib/api";
import type { RepoAnalysisResult } from "@/types";
import {
  Search,
  GitBranch,
  Star,
  GitFork,
  AlertCircle,
  FileText,
  FolderTree,
  Package,
  Plus,
  Trash2,
  Loader2,
} from "lucide-react";
import { parseGitHubInput } from "@/lib/utils";

export default function RepoAnalysis() {
  const [mode, setMode] = useState<"single" | "multi">("single");
  const [owner, setOwner] = useState("");
  const [repo, setRepo] = useState("");
  const [multiRepos, setMultiRepos] = useState<{ owner: string; repo: string }[]>([
    { owner: "", repo: "" },
  ]);
  const [results, setResults] = useState<RepoAnalysisResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedRepo, setExpandedRepo] = useState<string | null>(null);

  const handleSingleAnalysis = async () => {
    if (!owner.trim() || !repo.trim()) {
      setError("Please enter both owner and repo name.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeRepo(owner.trim(), repo.trim());
      setResults([result]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleMultiAnalysis = async () => {
    const valid = multiRepos.filter((r) => r.owner.trim() && r.repo.trim());
    if (valid.length === 0) {
      setError("Add at least one repo with owner and name.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeMultiRepo(
        valid.map((r) => ({ owner: r.owner.trim(), repo: r.repo.trim() }))
      );
      setResults(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Multi-repo analysis failed.");
    } finally {
      setLoading(false);
    }
  };

  const addMultiRepo = () => setMultiRepos([...multiRepos, { owner: "", repo: "" }]);
  const removeMultiRepo = (idx: number) =>
    setMultiRepos(multiRepos.filter((_, i) => i !== idx));
  const updateMultiRepo = (idx: number, field: "owner" | "repo", val: string) =>
    setMultiRepos(multiRepos.map((r, i) => (i === idx ? { ...r, [field]: val } : r)));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Repo Analysis</h1>
        <p className="text-gray-500 mt-1">
          Analyze GitHub repositories — fetch structure, README, dependencies, and architecture.
        </p>
      </div>

      {/* Mode Tabs */}
      <div className="flex gap-2">
        <button
          onClick={() => setMode("single")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
            mode === "single"
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          Single Repo
        </button>
        <button
          onClick={() => setMode("multi")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
            mode === "multi"
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          Multi-Repo
        </button>
      </div>

      {/* Input Form */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        {mode === "single" ? (
          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Owner</label>
              <input
                type="text"
                value={owner}
                onChange={(e) => {
                  const val = e.target.value;
                  const parsed = parseGitHubInput(val);
                  if (parsed && parsed.owner && parsed.repo && parsed.repo !== val) {
                    setOwner(parsed.owner);
                    setRepo(parsed.repo);
                  } else {
                    setOwner(val);
                  }
                }}
                placeholder="e.g. facebook or paste full URL"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Repository</label>
              <input
                type="text"
                value={repo}
                onChange={(e) => {
                  const val = e.target.value;
                  const parsed = parseGitHubInput(val);
                  if (parsed && parsed.owner && parsed.repo !== val) {
                    setOwner(parsed.owner);
                    setRepo(parsed.repo);
                  } else {
                    setRepo(val);
                  }
                }}
                placeholder="e.g. react or https://github.com/owner/repo"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <button
              onClick={handleSingleAnalysis}
              disabled={loading}
              className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
              Analyze
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {multiRepos.map((r, idx) => (
              <div key={idx} className="flex gap-3 items-end">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Owner {idx + 1}
                  </label>
                  <input
                    type="text"
                    value={r.owner}
                    onChange={(e) => {
                      const val = e.target.value;
                      const parsed = parseGitHubInput(val);
                      if (parsed && parsed.owner && parsed.repo && parsed.repo !== val) {
                        updateMultiRepo(idx, "owner", parsed.owner);
                        updateMultiRepo(idx, "repo", parsed.repo);
                      } else {
                        updateMultiRepo(idx, "owner", val);
                      }
                    }}
                    placeholder="e.g. facebook or paste URL"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Repo {idx + 1}
                  </label>
                  <input
                    type="text"
                    value={r.repo}
                    onChange={(e) => {
                      const val = e.target.value;
                      const parsed = parseGitHubInput(val);
                      if (parsed && parsed.owner && parsed.repo !== val) {
                        updateMultiRepo(idx, "owner", parsed.owner);
                        updateMultiRepo(idx, "repo", parsed.repo);
                      } else {
                        updateMultiRepo(idx, "repo", val);
                      }
                    }}
                    placeholder="e.g. react or https://github.com/owner/repo"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                {multiRepos.length > 1 && (
                  <button
                    onClick={() => removeMultiRepo(idx)}
                    className="p-2 text-red-500 hover:bg-red-50 rounded-lg"
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
            ))}
            <div className="flex gap-3">
              <button
                onClick={addMultiRepo}
                className="px-4 py-2 border border-dashed border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50 flex items-center gap-2"
              >
                <Plus size={14} /> Add Repo
              </button>
              <button
                onClick={handleMultiAnalysis}
                disabled={loading}
                className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
              >
                {loading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
                Analyze All
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
          <AlertCircle size={18} className="text-red-500" />
          <span className="text-sm text-red-700">{error}</span>
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Analysis Results ({results.length} {results.length === 1 ? "repo" : "repos"})
          </h2>
          {results.map((r) => {
            const expanded = expandedRepo === r.full_name;
            return (
              <div key={r.full_name} className="bg-white rounded-xl border border-gray-200">
                <button
                  onClick={() => setExpandedRepo(expanded ? null : r.full_name)}
                  className="w-full p-5 flex items-center justify-between text-left"
                >
                  <div className="flex items-center gap-3">
                    <GitBranch size={20} className="text-blue-600" />
                    <div>
                      <p className="font-semibold text-gray-900">{r.full_name}</p>
                      <p className="text-sm text-gray-500">{r.description || "No description"}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-gray-500">
                    {r.language && (
                      <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs font-medium">
                        {r.language}
                      </span>
                    )}
                    <span className="flex items-center gap-1">
                      <Star size={14} /> {r.stars}
                    </span>
                    <span className="flex items-center gap-1">
                      <GitFork size={14} /> {r.forks}
                    </span>
                    <span className="flex items-center gap-1">
                      <AlertCircle size={14} /> {r.open_issues}
                    </span>
                  </div>
                </button>
                {expanded && (
                  <div className="border-t border-gray-200 p-5 space-y-5">
                    {/* Architecture Notes */}
                    {r.architecture_notes.length > 0 && (
                      <div>
                        <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2 mb-2">
                          <FileText size={14} /> Architecture Notes
                        </h3>
                        <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                          {r.architecture_notes.map((n, i) => (
                            <li key={i}>{n}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Dependencies */}
                    {Object.keys(r.dependencies).length > 0 && (
                      <div>
                        <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2 mb-2">
                          <Package size={14} /> Dependencies
                        </h3>
                        {Object.entries(r.dependencies).map(([source, deps]) => (
                          <div key={source} className="mb-2">
                            <p className="text-xs font-medium text-gray-500 uppercase mb-1">
                              {source}
                            </p>
                            <div className="flex flex-wrap gap-1">
                              {deps.map((d) => (
                                <span
                                  key={d}
                                  className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs"
                                >
                                  {d}
                                </span>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* File Tree */}
                    {r.tree.length > 0 && (
                      <div>
                        <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2 mb-2">
                          <FolderTree size={14} /> File Structure ({r.tree.length} items)
                        </h3>
                        <div className="bg-gray-50 rounded-lg p-3 max-h-64 overflow-y-auto">
                          <pre className="text-xs text-gray-600 font-mono whitespace-pre-wrap">
                            {r.tree.join("\n")}
                          </pre>
                        </div>
                      </div>
                    )}

                    {/* README */}
                    {r.readme_content && (
                      <div>
                        <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2 mb-2">
                          <FileText size={14} /> README (excerpt)
                        </h3>
                        <div className="bg-gray-50 rounded-lg p-3 max-h-48 overflow-y-auto">
                          <pre className="text-xs text-gray-600 whitespace-pre-wrap">
                            {r.readme_content.slice(0, 3000)}
                          </pre>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
