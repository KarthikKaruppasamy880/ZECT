import { useState } from "react";
import { Box, ShieldAlert } from "lucide-react";
import { sandboxPrReadiness } from "@/lib/api";

export default function SandboxGate() {
  const [code, setCode] = useState('print("hello from Mentrix sandbox")\n');
  const [language, setLanguage] = useState("python");
  const [qualityScore, setQualityScore] = useState(80);
  const [critical, setCritical] = useState(0);
  const [acknowledge, setAcknowledge] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setError("");
    setLoading(true);
    try {
      setResult(
        await sandboxPrReadiness({
          code,
          language,
          quality_score: qualityScore,
          critical_findings: critical,
          acknowledge_issues: acknowledge,
        })
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gate check failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 p-1" data-testid="sandbox-page">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-slate-800 text-amber-300">
          <Box className="h-6 w-6" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Sandbox Gate</h1>
          <p className="text-sm text-slate-600">
            Hard gate before PR — sandbox must pass; critical review findings require acknowledge.
          </p>
        </div>
      </div>

      <label className="block text-sm">
        <span className="text-slate-600">Code under test</span>
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          rows={8}
          className="mt-1 w-full font-mono text-sm rounded-lg border border-slate-300 px-3 py-2"
        />
      </label>

      <div className="grid gap-3 md:grid-cols-3">
        <label className="text-sm">
          Language
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
          >
            <option value="python">python</option>
            <option value="javascript">javascript</option>
            <option value="typescript">typescript</option>
          </select>
        </label>
        <label className="text-sm">
          Quality score
          <input
            type="number"
            value={qualityScore}
            onChange={(e) => setQualityScore(Number(e.target.value))}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
          />
        </label>
        <label className="text-sm">
          Critical findings
          <input
            type="number"
            value={critical}
            onChange={(e) => setCritical(Number(e.target.value))}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
          />
        </label>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={acknowledge}
          onChange={(e) => setAcknowledge(e.target.checked)}
        />
        Acknowledge issues (required for critical / low score)
      </label>

      <button
        data-testid="sandbox-check"
        onClick={run}
        disabled={loading}
        className="rounded-lg bg-slate-900 px-4 py-2 text-white disabled:opacity-50"
      >
        Check PR readiness
      </button>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {result && (
        <div
          data-testid="sandbox-result"
          className={`rounded-xl border p-4 ${
            result.ready
              ? "border-teal-200 bg-teal-50"
              : "border-amber-200 bg-amber-50"
          }`}
        >
          <div className="flex items-center gap-2 font-semibold">
            <ShieldAlert className="h-4 w-4" />
            {result.ready ? "Ready to open PR" : "PR hard-blocked"}
          </div>
          {(result.blockers || []).length > 0 && (
            <ul className="mt-2 list-disc pl-5 text-sm">
              {result.blockers.map((b: string, i: number) => (
                <li key={i}>{b}</li>
              ))}
            </ul>
          )}
          {result.sandbox && (
            <pre className="mt-3 text-xs overflow-auto bg-white/70 p-2 rounded">
              {JSON.stringify(result.sandbox, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
