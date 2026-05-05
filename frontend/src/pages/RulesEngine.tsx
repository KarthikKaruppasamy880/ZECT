import { useState, useEffect } from "react";
import { Scale, Plus, Trash2, Play, Shield, Info } from "lucide-react";

interface Rule {
  id: number;
  repo_id: number | null;
  name: string;
  description: string;
  rule_type: string;
  condition: string;
  action: string;
  severity: string;
  is_active: boolean;
  created_by: number | null;
  created_at: string;
  updated_at: string;
}

const API = import.meta.env.VITE_API_URL ?? "";

const severityColor: Record<string, string> = {
  critical: "bg-red-100 text-red-700 border-red-200",
  high: "bg-orange-100 text-orange-700 border-orange-200",
  medium: "bg-yellow-100 text-yellow-700 border-yellow-200",
  low: "bg-blue-100 text-blue-700 border-blue-200",
  info: "bg-slate-100 text-slate-600 border-slate-200",
};

const ruleTypeColor: Record<string, string> = {
  review: "text-purple-600 bg-purple-50",
  quality_gate: "text-cyan-600 bg-cyan-50",
  deploy: "text-green-600 bg-green-50",
  naming: "text-amber-600 bg-amber-50",
  security: "text-red-600 bg-red-50",
};

export default function RulesEngine() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [showGuide, setShowGuide] = useState(false);
  const [testCode, setTestCode] = useState("");
  const [testResults, setTestResults] = useState<any[]>([]);
  const [form, setForm] = useState({
    name: "", description: "", rule_type: "review", condition: "",
    action: "warn", severity: "medium", is_active: true,
  });

  const fetchRules = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/rules`);
      if (res.ok) setRules(await res.json());
    } catch { /* API not available */ }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchRules(); }, []);

  const createRule = async () => {
    try {
      const res = await fetch(`${API}/api/rules`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (res.ok) {
        setShowCreate(false);
        setForm({ name: "", description: "", rule_type: "review", condition: "", action: "warn", severity: "medium", is_active: true });
        fetchRules();
      }
    } catch { /* error */ }
  };

  const deleteRule = async (id: number) => {
    try {
      await fetch(`${API}/api/rules/${id}`, { method: "DELETE" });
      fetchRules();
    } catch { /* error */ }
  };

  const evaluateRules = async () => {
    if (!testCode.trim()) return;
    try {
      const res = await fetch(`${API}/api/rules/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: testCode }),
      });
      if (res.ok) setTestResults(await res.json());
    } catch { /* error */ }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-amber-100 rounded-xl">
            <Scale className="h-6 w-6 text-amber-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Rules Engine</h1>
            <p className="text-sm text-slate-500">Create custom rules for code review, quality gates, and deployment</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowGuide(!showGuide)} className="flex items-center gap-1.5 px-3 py-2 bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200 text-sm">
            <Info className="h-4 w-4" /> Guide
          </button>
          <button onClick={() => setShowCreate(!showCreate)} className="flex items-center gap-2 px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 text-sm font-medium">
            <Plus className="h-4 w-4" /> New Rule
          </button>
        </div>
      </div>

      {/* Usage Guide */}
      {showGuide && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 space-y-2">
          <h3 className="font-semibold text-amber-900">How to use Rules Engine</h3>
          <ul className="text-sm text-amber-800 space-y-1 list-disc list-inside">
            <li><strong>Create a rule</strong> — Click "New Rule", give it a name, select the type (review, quality gate, deployment, naming, security), set the severity and action.</li>
            <li><strong>Regex patterns</strong> — The "condition" field takes a regex pattern. Example: <code className="bg-amber-100 px-1 rounded">console\.log|debugger</code> matches debug statements.</li>
            <li><strong>Actions</strong> — <strong>Warn</strong> shows a warning, <strong>Block</strong> prevents merge/deploy, <strong>Auto Fix</strong> suggests corrections, <strong>Notify</strong> sends alerts.</li>
            <li><strong>Test rules</strong> — Paste code in the "Test Rules" section below to see which rules match before deploying them.</li>
            <li><strong>Severity levels</strong> — Critical and High rules are shown prominently in code reviews. Medium/Low are informational.</li>
          </ul>
        </div>
      )}

      {/* Create Rule Form */}
      {showCreate && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-sm">
          <h3 className="text-slate-900 font-semibold">Create New Rule</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Rule name" className="border border-slate-300 text-slate-900 rounded-lg px-3 py-2 text-sm" />
            <select value={form.rule_type} onChange={(e) => setForm({ ...form, rule_type: e.target.value })} className="border border-slate-300 text-slate-700 rounded-lg px-3 py-2 text-sm bg-white">
              <option value="review">Code Review</option>
              <option value="quality_gate">Quality Gate</option>
              <option value="deploy">Deployment</option>
              <option value="naming">Naming Convention</option>
              <option value="security">Security</option>
            </select>
            <select value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })} className="border border-slate-300 text-slate-700 rounded-lg px-3 py-2 text-sm bg-white">
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="info">Info</option>
            </select>
            <select value={form.action} onChange={(e) => setForm({ ...form, action: e.target.value })} className="border border-slate-300 text-slate-700 rounded-lg px-3 py-2 text-sm bg-white">
              <option value="warn">Warn</option>
              <option value="block">Block</option>
              <option value="auto_fix">Auto Fix</option>
              <option value="notify">Notify</option>
            </select>
          </div>
          <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Rule description" rows={2} className="w-full border border-slate-300 text-slate-900 rounded-lg px-3 py-2 text-sm" />
          <textarea value={form.condition} onChange={(e) => setForm({ ...form, condition: e.target.value })} placeholder="Regex pattern (e.g. console\.log|debugger)" rows={2} className="w-full border border-slate-300 text-slate-900 rounded-lg px-3 py-2 text-sm font-mono" />
          <div className="flex gap-3">
            <button onClick={createRule} className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 text-sm font-medium">Create Rule</button>
            <button onClick={() => setShowCreate(false)} className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 text-sm">Cancel</button>
          </div>
        </div>
      )}

      {/* Rules List */}
      <div className="space-y-3">
        {loading ? (
          <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-400">Loading rules...</div>
        ) : rules.length === 0 ? (
          <div className="bg-white border border-slate-200 rounded-xl p-12 text-center shadow-sm">
            <Shield className="h-12 w-12 mx-auto mb-3 text-slate-300" />
            <p className="font-medium text-slate-700">No rules configured</p>
            <p className="text-sm text-slate-500 mt-1">Create rules to enforce code quality, security patterns, and deployment gates.</p>
            <p className="text-sm text-slate-500">Click "New Rule" above to get started.</p>
          </div>
        ) : (
          rules.map((rule) => (
            <div key={rule.id} className="bg-white border border-slate-200 rounded-xl p-4 flex items-center justify-between shadow-sm hover:border-slate-300 transition-colors">
              <div className="flex-1">
                <div className="flex items-center gap-3 flex-wrap">
                  <h3 className="text-slate-900 font-medium">{rule.name}</h3>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${severityColor[rule.severity] || severityColor.info}`}>
                    {rule.severity}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${ruleTypeColor[rule.rule_type] || "text-slate-500 bg-slate-50"}`}>
                    {rule.rule_type.replace("_", " ")}
                  </span>
                  {!rule.is_active && <span className="text-xs text-slate-400 italic">(disabled)</span>}
                </div>
                <p className="text-sm text-slate-500 mt-1">{rule.description}</p>
                {rule.condition && <code className="text-xs text-slate-400 font-mono mt-1 block bg-slate-50 px-2 py-1 rounded">{rule.condition}</code>}
              </div>
              <div className="flex items-center gap-2 ml-4">
                <button onClick={() => deleteRule(rule.id)} className="p-2 text-slate-400 hover:text-red-500 transition-colors">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Test Rules */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-sm">
        <h3 className="text-slate-900 font-semibold flex items-center gap-2">
          <Play className="h-4 w-4 text-green-600" /> Test Rules Against Code
        </h3>
        <textarea
          value={testCode}
          onChange={(e) => setTestCode(e.target.value)}
          placeholder="Paste code here to test against active rules..."
          rows={6}
          className="w-full border border-slate-300 text-slate-900 rounded-lg px-3 py-2 text-sm font-mono"
        />
        <button onClick={evaluateRules} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium">
          Evaluate Rules
        </button>
        {testResults.length > 0 && (
          <div className="space-y-2 mt-4">
            {testResults.map((r, i) => (
              <div key={i} className={`p-3 rounded-lg border ${r.matched ? "bg-red-50 border-red-200" : "bg-green-50 border-green-200"}`}>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-900">{r.rule_name}</span>
                  <span className={`text-xs font-semibold ${r.matched ? "text-red-600" : "text-green-600"}`}>
                    {r.matched ? "MATCHED" : "PASS"}
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-1">{r.message}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
