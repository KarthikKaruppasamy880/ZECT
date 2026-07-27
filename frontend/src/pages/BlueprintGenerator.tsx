import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  generateBlueprint,
  generateFocusedBlueprint,
  enhanceBlueprint,
  latticeBlueprintPrompt,
  saveContext,
  loadContext,
} from "@/lib/api";
import { useWorkspaceRepoContext } from "@/hooks/useWorkspaceRepoContext";
import type { BlueprintResult, FocusedBlueprintResult, EnhanceBlueprintResponse } from "@/types";
import {
  Sparkles,
  Plus,
  Trash2,
  Copy,
  Check,
  Loader2,
  AlertCircle,
  FileCode,
  Target,
  Network,
  ArrowRight,
} from "lucide-react";
import { parseGitHubInput } from "@/lib/utils";

type Mode = "standard" | "focused" | "lattice";

export default function BlueprintGenerator() {
  const navigate = useNavigate();
  const { projectKey, localPath, latticeStatus: idxStatus } = useWorkspaceRepoContext();
  const [mode, setMode] = useState<Mode>("standard");

  // Standard mode state
  const [repos, setRepos] = useState<{ owner: string; repo: string }[]>([
    { owner: "", repo: "" },
  ]);
  const [result, setResult] = useState<BlueprintResult | null>(null);

  // Focused mode state
  const [focusOwner, setFocusOwner] = useState("");
  const [focusRepo, setFocusRepo] = useState("");
  const [focusArea, setFocusArea] = useState("");
  const [focusGoal, setFocusGoal] = useState("");
  const [focusedResult, setFocusedResult] = useState<FocusedBlueprintResult | null>(null);

  // From Lattice mode
  const [latticeKey, setLatticeKey] = useState("");
  const [latticePath, setLatticePath] = useState("");
  const [latticeResult, setLatticeResult] = useState<{
    prompt: string;
    token_estimate: number;
    stats?: Record<string, unknown>;
  } | null>(null);

  // Shared state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [enhancing, setEnhancing] = useState(false);
  const [enhanced, setEnhanced] = useState<EnhanceBlueprintResponse | null>(null);
  const [enhanceCopied, setEnhanceCopied] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem("zect_mentrix_workspace");
      if (!raw) return;
      const ws = JSON.parse(raw) as {
        project_key?: string;
        projectKey?: string;
        path?: string;
        workspace?: string;
      };
      const pk = ws.project_key || ws.projectKey;
      const wp = ws.path || ws.workspace;
      if (pk) {
        setLatticeKey(pk);
        setMode("lattice");
      }
      if (wp) setLatticePath(wp);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    if (projectKey) setLatticeKey(projectKey);
    if (localPath) setLatticePath(localPath);
  }, [projectKey, localPath]);

  useEffect(() => {
    void (async () => {
      const session = await loadContext("workspace", ["blueprint_prompt"]).catch(() => null);
      const saved = session?.entries.find((e) => e.key === "blueprint_prompt")?.value;
      if (saved) {
        setLatticeResult({
          prompt: saved,
          token_estimate: Math.max(1, Math.floor(saved.length / 4)),
        });
        setMode("lattice");
      }
    })();
  }, []);

  const persistBlueprint = async (prompt: string) => {
    await saveContext("workspace", "blueprint_prompt", prompt).catch(() => {});
    await saveContext("blueprint", "repo_analysis", prompt.slice(0, 12000)).catch(() => {});
  };

  const handleUseInAsk = async (prompt: string) => {
    await persistBlueprint(prompt);
    navigate("/ask", { state: { repoContext: prompt } });
  };

  const handleUseInPlan = async (prompt: string) => {
    await persistBlueprint(prompt);
    navigate("/plan", {
      state: {
        repoContext: prompt,
        projectDescription: `Implement using this Lattice blueprint context:\n\n${prompt.slice(0, 2000)}…`,
      },
    });
  };

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

  const handleFocusedGenerate = async () => {
    if (!focusOwner.trim() || !focusRepo.trim()) {
      setError("Enter both owner and repository name.");
      return;
    }
    if (!focusArea.trim()) {
      setError("Enter a focus area (e.g. authentication, API layer, database).");
      return;
    }
    setLoading(true);
    setError(null);
    setFocusedResult(null);
    try {
      const data = await generateFocusedBlueprint(
        focusOwner.trim(),
        focusRepo.trim(),
        focusArea.trim(),
        focusGoal.trim() || undefined
      );
      setFocusedResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Focused blueprint generation failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleLatticeGenerate = async () => {
    if (!latticeKey.trim()) {
      setError("Enter a Lattice project key (from Repo Workspace clone or Lattice ingest).");
      return;
    }
    setLoading(true);
    setError(null);
    setLatticeResult(null);
    try {
      const data = await latticeBlueprintPrompt(
        latticeKey.trim(),
        latticePath.trim(),
        Boolean(latticePath.trim()),
      );
      setLatticeResult(data);
      await persistBlueprint(data.prompt);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Lattice blueprint failed — ingest the workspace first.",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const activePrompt =
    mode === "standard"
      ? result?.prompt
      : mode === "focused"
        ? focusedResult?.prompt
        : latticeResult?.prompt;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Blueprint Generator</h1>
        <p className="text-gray-500 mt-1">
          Deep structural blueprints from Lattice (local index) or GitHub Standard/Focused modes
          for remote-only repos.
        </p>
        {latticeKey && (
          <p className="text-xs mt-2" data-testid="blueprint-index-status">
            {idxStatus?.indexed ? (
              <span className="text-teal-700">Indexed for <code>{latticeKey}</code></span>
            ) : (
              <span className="text-amber-700">Not indexed — clone & ingest in Repo Workspace first</span>
            )}
          </p>
        )}
      </div>

      {/* Mode Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit flex-wrap">
        <button
          onClick={() => { setMode("lattice"); setError(null); }}
          className={`px-4 py-2 rounded-md text-sm font-medium transition flex items-center gap-2 ${
            mode === "lattice"
              ? "bg-white text-teal-700 shadow-sm"
              : "text-gray-600 hover:text-gray-900"
          }`}
        >
          <Network size={14} />
          From Lattice
        </button>
        <button
          onClick={() => { setMode("standard"); setError(null); }}
          className={`px-4 py-2 rounded-md text-sm font-medium transition flex items-center gap-2 ${
            mode === "standard"
              ? "bg-white text-purple-700 shadow-sm"
              : "text-gray-600 hover:text-gray-900"
          }`}
        >
          <Sparkles size={14} />
          GitHub Standard
        </button>
        <button
          onClick={() => { setMode("focused"); setError(null); }}
          className={`px-4 py-2 rounded-md text-sm font-medium transition flex items-center gap-2 ${
            mode === "focused"
              ? "bg-white text-purple-700 shadow-sm"
              : "text-gray-600 hover:text-gray-900"
          }`}
        >
          <Target size={14} />
          Focused
        </button>
      </div>

      {mode === "lattice" && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4" data-testid="blueprint-lattice-mode">
          <h2 className="text-sm font-semibold text-gray-700">From Lattice structural blueprint</h2>
          <p className="text-xs text-gray-500">
            Uses Mentrix RepoBlueprint: APIs, symbols, deps, tech stack, god nodes — not README-only.
          </p>
          <div className="flex gap-3 flex-wrap">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm font-medium text-gray-700 mb-1">Project key</label>
              <input
                data-testid="blueprint-lattice-key"
                type="text"
                value={latticeKey}
                onChange={(e) => setLatticeKey(e.target.value)}
                placeholder="e.g. owner-repo from Workspace clone"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
              />
            </div>
            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Local path <span className="text-gray-400 font-normal">(rebuild if missing)</span>
              </label>
              <input
                data-testid="blueprint-lattice-path"
                type="text"
                value={latticePath}
                onChange={(e) => setLatticePath(e.target.value)}
                placeholder="optional workspace path"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
              />
            </div>
          </div>
          <button
            data-testid="blueprint-lattice-generate"
            onClick={handleLatticeGenerate}
            disabled={loading}
            className="px-5 py-2 bg-teal-700 text-white rounded-lg text-sm font-medium hover:bg-teal-800 disabled:opacity-50 flex items-center gap-2"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Network size={16} />}
            Generate deep prompt
          </button>
        </div>
      )}

      {/* Standard Mode Input */}
      {mode === "standard" && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700">Repositories to Analyze</h2>
          {repos.map((r, idx) => (
            <div key={idx} className="flex gap-3 items-end">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">Owner</label>
                <input
                  type="text"
                  value={r.owner}
                  onChange={(e) => {
                    const val = e.target.value;
                    const parsed = parseGitHubInput(val);
                    if (parsed && parsed.owner && parsed.repo && parsed.repo !== val) {
                      updateRepo(idx, "owner", parsed.owner);
                      updateRepo(idx, "repo", parsed.repo);
                    } else {
                      updateRepo(idx, "owner", val);
                    }
                  }}
                  placeholder="e.g. KarthikKaruppasamy880 or paste URL"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                />
              </div>
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">Repository</label>
                <input
                  type="text"
                  value={r.repo}
                  onChange={(e) => {
                    const val = e.target.value;
                    const parsed = parseGitHubInput(val);
                    if (parsed && parsed.owner && parsed.repo !== val) {
                      updateRepo(idx, "owner", parsed.owner);
                      updateRepo(idx, "repo", parsed.repo);
                    } else {
                      updateRepo(idx, "repo", val);
                    }
                  }}
                  placeholder="e.g. ZECT or https://github.com/owner/repo"
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
      )}

      {/* Focused Mode Input */}
      {mode === "focused" && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700">Focused Repository Analysis</h2>
          <p className="text-xs text-gray-500">
            Generate a prompt scoped to a specific feature or layer of a repository —
            ideal for understanding authentication, API routes, database schemas, etc.
          </p>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Owner</label>
              <input
                type="text"
                value={focusOwner}
                onChange={(e) => {
                  const val = e.target.value;
                  const parsed = parseGitHubInput(val);
                  if (parsed && parsed.owner && parsed.repo && parsed.repo !== val) {
                    setFocusOwner(parsed.owner);
                    setFocusRepo(parsed.repo);
                  } else {
                    setFocusOwner(val);
                  }
                }}
                placeholder="e.g. KarthikKaruppasamy880 or paste URL"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
              />
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Repository</label>
              <input
                type="text"
                value={focusRepo}
                onChange={(e) => {
                  const val = e.target.value;
                  const parsed = parseGitHubInput(val);
                  if (parsed && parsed.owner && parsed.repo !== val) {
                    setFocusOwner(parsed.owner);
                    setFocusRepo(parsed.repo);
                  } else {
                    setFocusRepo(val);
                  }
                }}
                placeholder="e.g. ZECT or https://github.com/owner/repo"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Focus Area</label>
            <input
              type="text"
              value={focusArea}
              onChange={(e) => setFocusArea(e.target.value)}
              placeholder="e.g. authentication, API layer, database schema, CI/CD pipeline"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Goal <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <input
              type="text"
              value={focusGoal}
              onChange={(e) => setFocusGoal(e.target.value)}
              placeholder="e.g. understand and replicate, migrate to new framework, add tests"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
            />
          </div>
          <button
            onClick={handleFocusedGenerate}
            disabled={loading}
            className="px-5 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2"
          >
            {loading ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Target size={16} />
            )}
            Generate Focused Blueprint
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
          <AlertCircle size={18} className="text-red-500" />
          <span className="text-sm text-red-700">{error}</span>
        </div>
      )}

      {/* Standard Result */}
      {mode === "standard" && result && (
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
              onClick={() => handleCopy(result.prompt)}
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
            <div className="mt-4 flex items-center gap-3">
              <button
                onClick={async () => {
                  if (!result) return;
                  setEnhancing(true);
                  try {
                    const res = await enhanceBlueprint(result.prompt);
                    setEnhanced(res);
                  } catch {
                    setError("Failed to enhance blueprint. Check your OpenAI API key in Settings.");
                  } finally {
                    setEnhancing(false);
                  }
                }}
                disabled={enhancing}
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 flex items-center gap-2"
              >
                {enhancing ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Sparkles size={14} />
                )}
                {enhancing ? "Enhancing..." : "Enhance with AI"}
              </button>
              <p className="text-xs text-gray-400">
                Uses OpenAI to improve clarity, add priorities, and optimize for AI comprehension.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Enhanced Result */}
      {enhanced && (
        <div className="bg-white rounded-xl border border-emerald-200">
          <div className="p-5 border-b border-emerald-200 flex items-center justify-between bg-emerald-50">
            <div className="flex items-center gap-3">
              <Sparkles size={20} className="text-emerald-600" />
              <div>
                <h2 className="font-semibold text-gray-900">AI-Enhanced Blueprint</h2>
                <p className="text-xs text-gray-500">
                  Enhanced by {enhanced.model} &middot; ~{enhanced.tokens_used.toLocaleString()} tokens
                </p>
              </div>
            </div>
            <button
              onClick={async () => {
                await navigator.clipboard.writeText(enhanced.enhanced_prompt);
                setEnhanceCopied(true);
                setTimeout(() => setEnhanceCopied(false), 2000);
              }}
              className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition ${
                enhanceCopied
                  ? "bg-green-100 text-green-700"
                  : "bg-emerald-600 text-white hover:bg-emerald-700"
              }`}
            >
              {enhanceCopied ? <Check size={16} /> : <Copy size={16} />}
              {enhanceCopied ? "Copied!" : "Copy Enhanced"}
            </button>
          </div>
          <div className="p-5">
            <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
              <pre className="text-xs text-gray-700 font-mono whitespace-pre-wrap">
                {enhanced.enhanced_prompt}
              </pre>
            </div>
            <p className="text-xs text-gray-400 mt-3">
              This AI-enhanced prompt is optimized for maximum comprehension by any AI coding tool.
            </p>
          </div>
        </div>
      )}

      {/* Lattice Result */}
      {mode === "lattice" && latticeResult && (
        <div className="bg-white rounded-xl border border-teal-200" data-testid="blueprint-lattice-result">
          <div className="p-5 border-b border-teal-200 flex items-center justify-between bg-teal-50">
            <div className="flex items-center gap-3">
              <Network size={20} className="text-teal-700" />
              <div>
                <h2 className="font-semibold text-gray-900">Lattice deep blueprint</h2>
                <p className="text-xs text-gray-500">
                  ~{latticeResult.token_estimate.toLocaleString()} tokens
                  {latticeResult.stats
                    ? ` · endpoints=${String((latticeResult.stats as any).api_endpoints ?? "—")} · functions=${String((latticeResult.stats as any).functions ?? "—")}`
                    : ""}
                </p>
              </div>
            </div>
            <button
              onClick={() => handleCopy(latticeResult.prompt)}
              className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition ${
                copied
                  ? "bg-green-100 text-green-700"
                  : "bg-teal-700 text-white hover:bg-teal-800"
              }`}
            >
              {copied ? <Check size={16} /> : <Copy size={16} />}
              {copied ? "Copied!" : "Copy to Clipboard"}
            </button>
          </div>
          <div className="p-5">
            <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
              <pre className="text-xs text-gray-700 font-mono whitespace-pre-wrap">
                {latticeResult.prompt}
              </pre>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                data-testid="blueprint-use-in-ask"
                onClick={() => handleUseInAsk(latticeResult.prompt)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 flex items-center gap-2"
              >
                Use in Ask <ArrowRight size={14} />
              </button>
              <button
                type="button"
                data-testid="blueprint-use-in-plan"
                onClick={() => handleUseInPlan(latticeResult.prompt)}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 flex items-center gap-2"
              >
                Use in Plan <ArrowRight size={14} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Focused Result */}
      {mode === "focused" && focusedResult && (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="p-5 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Target size={20} className="text-purple-600" />
              <div>
                <h2 className="font-semibold text-gray-900">Focused Blueprint: {focusedResult.focus_area}</h2>
                <p className="text-xs text-gray-500">
                  {focusedResult.repo_name} &middot; ~{focusedResult.token_estimate.toLocaleString()} tokens
                </p>
              </div>
            </div>
            <button
              onClick={() => handleCopy(focusedResult.prompt)}
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
                {focusedResult.prompt}
              </pre>
            </div>
            <p className="text-xs text-gray-400 mt-3">
              This prompt is scoped to &quot;{focusedResult.focus_area}&quot; — paste it into any AI tool
              for targeted analysis and implementation guidance.
            </p>
          </div>
        </div>
      )}

      {/* Usage Tips */}
      {!activePrompt && !loading && (
        <div className="bg-gray-50 rounded-xl border border-gray-100 p-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">How It Works</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-600">
            <div>
              <p className="font-medium text-gray-800 mb-1">From Lattice</p>
              <p>Deep structural prompt from local Lattice index (APIs, symbols, deps, tech stack).
              Prefer this when the repo is cloned or ingested.</p>
            </div>
            <div>
              <p className="font-medium text-gray-800 mb-1">GitHub Standard</p>
              <p>Remote tree + README vibe prompt when you only have a GitHub URL.</p>
            </div>
            <div>
              <p className="font-medium text-gray-800 mb-1">Focused Mode</p>
              <p>Scopes analysis to a specific feature or layer (e.g. auth, API, database).</p>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-gray-200">
            <p className="text-xs text-gray-500">
              <strong>AI-Agnostic:</strong> Generated prompts work with any AI coding tool —
              paste into any AI coding tool of your choice.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
