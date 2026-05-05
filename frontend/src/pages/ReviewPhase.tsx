import { useState } from "react";
import { reviewAnalyze, reviewFixPrompt } from "@/lib/api";
import CodeOutput from "@/components/CodeOutput";
import ModelSelector from "@/components/ModelSelector";
import { Shield, Play, Loader2, AlertTriangle, CheckCircle, XCircle, Wand2 } from "lucide-react";

export default function ReviewPhase() {
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("typescript");
  const [severity, setSeverity] = useState("medium");
  const [selectedModel, setSelectedModel] = useState("gpt-4o-mini");
  const [loading, setLoading] = useState(false);
  const [fixLoading, setFixLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [fixResult, setFixResult] = useState<any>(null);
  const [error, setError] = useState("");

  const handleReview = async () => {
    if (!code.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    setFixResult(null);
    try {
      const res = await reviewAnalyze(code, language, severity);
      setResult(res);
    } catch (e: any) {
      setError(e.message || "Failed to analyze code");
    } finally {
      setLoading(false);
    }
  };

  const handleFixPrompt = async () => {
    if (!result?.findings?.length) return;
    setFixLoading(true);
    try {
      const res = await reviewFixPrompt(code, result.findings, language);
      setFixResult(res);
    } catch (e: any) {
      setError(e.message || "Failed to generate fix");
    } finally {
      setFixLoading(false);
    }
  };

  const severityColor = (s: string) => {
    switch (s) {
      case "critical": return "bg-red-100 text-red-800 border-red-200";
      case "high": return "bg-orange-100 text-orange-800 border-orange-200";
      case "medium": return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "low": return "bg-blue-100 text-blue-800 border-blue-200";
      default: return "bg-slate-100 text-slate-800 border-slate-200";
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-3 bg-purple-100 rounded-xl">
          <Shield className="h-6 w-6 text-purple-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Review Phase</h1>
          <p className="text-slate-500">AI code quality gate — analyze code for security, performance, and maintainability</p>
        </div>
      </div>

      {/* Input Form */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Code to Review *
          </label>
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Paste your code here for AI quality review..."
            className="w-full h-48 p-3 border border-slate-300 rounded-lg text-sm font-mono focus:ring-2 focus:ring-purple-500 focus:border-purple-500 resize-none"
          />
        </div>

        <ModelSelector value={selectedModel} onChange={setSelectedModel} />

        <div className="flex flex-wrap gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Language</label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="p-2 border border-slate-300 rounded-lg text-sm"
            >
              <option value="typescript">TypeScript</option>
              <option value="javascript">JavaScript</option>
              <option value="python">Python</option>
              <option value="java">Java</option>
              <option value="go">Go</option>
              <option value="rust">Rust</option>
              <option value="csharp">C#</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Min Severity</label>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
              className="p-2 border border-slate-300 rounded-lg text-sm"
            >
              <option value="critical">Critical only</option>
              <option value="high">High+</option>
              <option value="medium">Medium+</option>
              <option value="low">Low+</option>
              <option value="info">All (incl. info)</option>
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={handleReview}
              disabled={loading || !code.trim()}
              className="flex items-center gap-2 px-5 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-slate-300 text-white rounded-lg font-medium transition"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {loading ? "Analyzing..." : "Run Review"}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">{error}</div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Score Card */}
          <div className={`rounded-xl border p-5 ${result.passed ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {result.passed ? (
                  <CheckCircle className="h-8 w-8 text-green-600" />
                ) : (
                  <XCircle className="h-8 w-8 text-red-600" />
                )}
                <div>
                  <h2 className="text-lg font-bold">{result.passed ? "PASSED" : "FAILED"} — Quality Gate</h2>
                  <p className="text-sm text-slate-600">{result.summary}</p>
                </div>
              </div>
              <div className="text-center">
                <div className={`text-3xl font-bold ${result.score >= 70 ? "text-green-600" : result.score >= 50 ? "text-yellow-600" : "text-red-600"}`}>
                  {result.score}
                </div>
                <div className="text-xs text-slate-500">/ 100</div>
              </div>
            </div>
          </div>

          {/* Findings */}
          {result.findings?.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
              <div className="p-4 border-b border-slate-200 flex items-center justify-between">
                <h3 className="font-semibold text-slate-900">
                  <AlertTriangle className="inline h-4 w-4 mr-1" />
                  Findings ({result.findings.length})
                </h3>
                <button
                  onClick={handleFixPrompt}
                  disabled={fixLoading}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white rounded-lg text-sm font-medium transition"
                >
                  {fixLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Wand2 className="h-3.5 w-3.5" />}
                  Generate Fix Prompt
                </button>
              </div>
              <div className="divide-y divide-slate-100">
                {result.findings.map((f: any, i: number) => (
                  <div key={i} className="p-4 flex items-start gap-3">
                    <span className={`px-2 py-0.5 text-xs font-medium rounded border ${severityColor(f.severity)}`}>
                      {f.severity.toUpperCase()}
                    </span>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-slate-900">{f.message}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{f.category} {f.line ? `• Line ${f.line}` : ""}</p>
                      {f.suggestion && (
                        <p className="text-xs text-green-700 mt-1 bg-green-50 p-2 rounded">
                          Fix: {f.suggestion}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Fix Prompt Result */}
          {fixResult && (
            <div className="space-y-4">
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
                <h3 className="font-semibold text-slate-900 mb-2">Fix Prompt (paste into AI tool)</h3>
                <CodeOutput code={fixResult.fix_prompt} language="markdown" title="Fix Prompt" maxHeight="200px" />
              </div>
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
                <h3 className="font-semibold text-slate-900 mb-2">Auto-Fixed Code</h3>
                <p className="text-sm text-slate-600 mb-2">{fixResult.changes_summary}</p>
                <CodeOutput code={fixResult.fixed_code} language={language} title="Fixed Code" maxHeight="400px" />
              </div>
            </div>
          )}

          <div className="text-xs text-slate-400 text-right">
            {result.tokens_used} tokens • {result.model}
          </div>
        </div>
      )}
    </div>
  );
}
