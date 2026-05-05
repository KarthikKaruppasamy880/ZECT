import { useState, useEffect } from "react";
import { Scale, Plus, Trash2, Edit, Play, Shield } from "lucide-react";

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
  critical: "bg-red-500/20 text-red-400 border-red-500/30",
  high: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  medium: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  low: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  info: "bg-slate-500/20 text-slate-400 border-slate-500/30",
};

const ruleTypeColor: Record<string, string> = {
  review: "text-purple-400",
  quality_gate: "text-cyan-400",
  deploy: "text-green-400",
  naming: "text-yellow-400",
  security: "text-red-400",
};

export default function RulesEngine() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Scale className="h-6 w-6 text-yellow-400" />
            Rules Engine
          </h1>
          <p className="text-sm text-slate-400 mt-1">Create custom rules for code review, quality gates, and deployment</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} className="flex items-center gap-2 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-500 text-sm font-medium">
          <Plus className="h-4 w-4" /> New Rule
        </button>
      </div>

      {/* Create Rule Form */}
      {showCreate && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 space-y-4">
          <h3 className="text-white font-semibold">Create New Rule</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Rule name" className="bg-slate-900 border border-slate-700 text-white rounded-lg px-3 py-2 text-sm" />
            <select value={form.rule_type} onChange={(e) => setForm({ ...form, rule_type: e.target.value })} className="bg-slate-900 border border-slate-700 text-slate-300 rounded-lg px-3 py-2 text-sm">
              <option value="review">Code Review</option>
              <option value="quality_gate">Quality Gate</option>
              <option value="deploy">Deployment</option>
              <option value="naming">Naming Convention</option>
              <option value="security">Security</option>
            </select>
            <select value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })} className="bg-slate-900 border border-slate-700 text-slate-300 rounded-lg px-3 py-2 text-sm">
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="info">Info</option>
            </select>
            <select value={form.action} onChange={(e) => setForm({ ...form, action: e.target.value })} className="bg-slate-900 border border-slate-700 text-slate-300 rounded-lg px-3 py-2 text-sm">
              <option value="warn">Warn</option>
              <option value="block">Block</option>
              <option value="auto_fix">Auto Fix</option>
              <option value="notify">Notify</option>
            </select>
          </div>
          <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Rule description" rows={2} className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg px-3 py-2 text-sm" />
          <textarea value={form.condition} onChange={(e) => setForm({ ...form, condition: e.target.value })} placeholder="Regex pattern (e.g. console\.log|debugger)" rows={2} className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg px-3 py-2 text-sm font-mono" />
          <div className="flex gap-3">
            <button onClick={createRule} className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-500 text-sm font-medium">Create Rule</button>
            <button onClick={() => setShowCreate(false)} className="px-4 py-2 bg-slate-700 text-slate-300 rounded-lg hover:bg-slate-600 text-sm">Cancel</button>
          </div>
        </div>
      )}

      {/* Rules List */}
      <div className="space-y-3">
        {loading ? (
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-8 text-center text-slate-400">Loading rules...</div>
        ) : rules.length === 0 ? (
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-8 text-center text-slate-400">
            <Shield className="h-12 w-12 mx-auto mb-3 opacity-30" />
            <p className="font-medium">No rules configured</p>
            <p className="text-sm mt-1">Create rules to enforce code quality, security patterns, and deployment gates</p>
          </div>
        ) : (
          rules.map((rule) => (
            <div key={rule.id} className="bg-slate-800/50 border border-slate-700 rounded-xl p-4 flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3">
                  <h3 className="text-white font-medium">{rule.name}</h3>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${severityColor[rule.severity] || severityColor.info}`}>
                    {rule.severity}
                  </span>
                  <span className={`text-xs ${ruleTypeColor[rule.rule_type] || "text-slate-400"}`}>
                    {rule.rule_type.replace("_", " ")}
                  </span>
                  {!rule.is_active && <span className="text-xs text-slate-500">(disabled)</span>}
                </div>
                <p className="text-sm text-slate-400 mt-1">{rule.description}</p>
                <code className="text-xs text-slate-500 font-mono mt-1 block">{rule.condition}</code>
              </div>
              <div className="flex items-center gap-2 ml-4">
                <button onClick={() => deleteRule(rule.id)} className="p-2 text-slate-400 hover:text-red-400 transition-colors">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Test Rules */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 space-y-4">
        <h3 className="text-white font-semibold flex items-center gap-2">
          <Play className="h-4 w-4 text-green-400" /> Test Rules Against Code
        </h3>
        <textarea
          value={testCode}
          onChange={(e) => setTestCode(e.target.value)}
          placeholder="Paste code here to test against active rules..."
          rows={6}
          className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg px-3 py-2 text-sm font-mono"
        />
        <button onClick={evaluateRules} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500 text-sm font-medium">
          Evaluate Rules
        </button>
        {testResults.length > 0 && (
          <div className="space-y-2 mt-4">
            {testResults.map((r, i) => (
              <div key={i} className={`p-3 rounded-lg border ${r.matched ? "bg-red-500/10 border-red-500/30" : "bg-green-500/10 border-green-500/30"}`}>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-white">{r.rule_name}</span>
                  <span className={`text-xs font-medium ${r.matched ? "text-red-400" : "text-green-400"}`}>
                    {r.matched ? "MATCHED" : "PASS"}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1">{r.message}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
