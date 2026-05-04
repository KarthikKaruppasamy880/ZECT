import { useState } from "react";
import { generatePlan } from "@/lib/api";
import {
  ClipboardList,
  Loader2,
  AlertCircle,
  Copy,
  Check,
  Zap,
} from "lucide-react";

export default function PlanMode() {
  const [description, setDescription] = useState("");
  const [repoContext, setRepoContext] = useState("");
  const [constraints, setConstraints] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [plan, setPlan] = useState<string | null>(null);
  const [phases, setPhases] = useState<string[]>([]);
  const [tokensUsed, setTokensUsed] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleGenerate = async () => {
    if (!description.trim()) {
      setError("Please describe the project or feature you want to plan.");
      return;
    }
    setLoading(true);
    setError(null);
    setPlan(null);
    try {
      const res = await generatePlan(
        description.trim(),
        repoContext.trim() || undefined,
        constraints.trim() || undefined
      );
      setPlan(res.plan);
      setPhases(res.phases);
      setTokensUsed(res.tokens_used);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Plan generation failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!plan) return;
    await navigator.clipboard.writeText(plan);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <ClipboardList size={24} className="text-indigo-600" />
          Plan Mode
        </h1>
        <p className="text-gray-500 mt-1">
          Generate a detailed, phased engineering plan for any project or feature.
          Powered by OpenAI GPT-4o-mini.
        </p>
      </div>

      {/* Input */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Project / Feature Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the project or feature you want to plan. Be as specific as possible — include goals, scope, and tech stack preferences..."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 h-32 resize-none"
          />
        </div>

        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
        >
          <Zap size={14} />
          {showAdvanced ? "Hide" : "Show"} advanced options
        </button>

        {showAdvanced && (
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Repo Context (optional)
              </label>
              <textarea
                value={repoContext}
                onChange={(e) => setRepoContext(e.target.value)}
                placeholder="Paste repo analysis or README content for context-aware planning..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 h-20 resize-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Constraints (optional)
              </label>
              <textarea
                value={constraints}
                onChange={(e) => setConstraints(e.target.value)}
                placeholder="Budget limits, timeline, team size, tech restrictions..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 h-16 resize-none"
              />
            </div>
          </div>
        )}

        <button
          onClick={handleGenerate}
          disabled={loading}
          className="px-5 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
        >
          {loading ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <ClipboardList size={16} />
          )}
          {loading ? "Generating Plan..." : "Generate Engineering Plan"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
          <AlertCircle size={18} className="text-red-500" />
          <span className="text-sm text-red-700">{error}</span>
        </div>
      )}

      {/* Result */}
      {plan && (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="p-5 border-b border-gray-200 flex items-center justify-between">
            <div>
              <h2 className="font-semibold text-gray-900">Engineering Plan</h2>
              <p className="text-xs text-gray-500">
                {phases.length} phases &middot; ~{tokensUsed.toLocaleString()} tokens
              </p>
            </div>
            <button
              onClick={handleCopy}
              className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition ${
                copied
                  ? "bg-green-100 text-green-700"
                  : "bg-indigo-600 text-white hover:bg-indigo-700"
              }`}
            >
              {copied ? <Check size={16} /> : <Copy size={16} />}
              {copied ? "Copied!" : "Copy Plan"}
            </button>
          </div>

          {/* Phases sidebar */}
          {phases.length > 0 && (
            <div className="p-4 border-b border-gray-200 bg-indigo-50">
              <p className="text-xs font-semibold text-indigo-700 mb-2">PHASES</p>
              <div className="flex flex-wrap gap-2">
                {phases.map((phase, idx) => (
                  <span
                    key={idx}
                    className="px-3 py-1 bg-white border border-indigo-200 rounded-full text-xs text-indigo-700"
                  >
                    {phase}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="p-5">
            <div className="bg-gray-50 rounded-lg p-4 max-h-[500px] overflow-y-auto">
              <pre className="text-sm text-gray-700 font-mono whitespace-pre-wrap">
                {plan}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
