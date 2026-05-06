import { useEffect, useState } from "react";
import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  Plus,
  CheckCircle,
  XCircle,
  Clock,
  Search,
  RefreshCw,
} from "lucide-react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface Rule {
  id: number;
  project_id: number | null;
  action_pattern: string;
  permission_level: string;
  category: string;
  description: string;
  requires_mfa: boolean;
  is_active: boolean;
  created_at: string;
}

interface Audit {
  id: number;
  user_id: number | null;
  project_id: number | null;
  action: string;
  permission_level: string;
  result: string;
  rule_id: number | null;
  approval_status: string | null;
  approved_by: string | null;
  reason: string;
  created_at: string;
}

export default function Permissions() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [audits, setAudits] = useState<Audit[]>([]);
  const [pending, setPending] = useState<Audit[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"rules" | "check" | "audits" | "pending">("rules");
  const [checkAction, setCheckAction] = useState("");
  const [checkResult, setCheckResult] = useState<any>(null);
  const [showAddRule, setShowAddRule] = useState(false);
  const [newRule, setNewRule] = useState({ action_pattern: "", permission_level: "require_approval", category: "general", description: "" });

  const fetchRules = async () => {
    try {
      const res = await fetch(`${API}/api/permissions/rules`);
      if (res.ok) setRules(await res.json());
    } catch { /* ignore */ }
  };

  const fetchAudits = async () => {
    try {
      const res = await fetch(`${API}/api/permissions/audits?limit=50`);
      if (res.ok) setAudits(await res.json());
    } catch { /* ignore */ }
  };

  const fetchPending = async () => {
    try {
      const res = await fetch(`${API}/api/permissions/audits/pending`);
      if (res.ok) setPending(await res.json());
    } catch { /* ignore */ }
  };

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchRules(), fetchAudits(), fetchPending()]).finally(() => setLoading(false));
  }, []);

  const handleCheck = async () => {
    if (!checkAction.trim()) return;
    try {
      const res = await fetch(`${API}/api/permissions/check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: checkAction }),
      });
      if (res.ok) {
        setCheckResult(await res.json());
        fetchAudits();
        fetchPending();
      }
    } catch { /* ignore */ }
  };

  const handleAddRule = async () => {
    if (!newRule.action_pattern.trim()) return;
    try {
      await fetch(`${API}/api/permissions/rules`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newRule),
      });
      setShowAddRule(false);
      setNewRule({ action_pattern: "", permission_level: "require_approval", category: "general", description: "" });
      fetchRules();
    } catch { /* ignore */ }
  };

  const handleApproval = async (auditId: number, approved: boolean) => {
    try {
      await fetch(`${API}/api/permissions/audits/${auditId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved, approved_by: "admin", reason: approved ? "Approved via dashboard" : "Rejected via dashboard" }),
      });
      fetchAudits();
      fetchPending();
    } catch { /* ignore */ }
  };

  const handleDeleteRule = async (ruleId: number) => {
    try {
      await fetch(`${API}/api/permissions/rules/${ruleId}`, { method: "DELETE" });
      fetchRules();
    } catch { /* ignore */ }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600" />
      </div>
    );
  }

  const tabs = [
    { key: "rules" as const, label: "Permission Rules", icon: Shield },
    { key: "check" as const, label: "Check Action", icon: Search },
    { key: "pending" as const, label: `Pending (${pending.length})`, icon: Clock },
    { key: "audits" as const, label: "Audit Log", icon: ShieldCheck },
  ];

  const levelIcon = (level: string) => {
    switch (level) {
      case "allow": return <ShieldCheck className="h-4 w-4 text-green-600" />;
      case "require_approval": return <ShieldAlert className="h-4 w-4 text-amber-600" />;
      case "never": return <ShieldX className="h-4 w-4 text-red-600" />;
      default: return <Shield className="h-4 w-4 text-slate-400" />;
    }
  };

  const levelBadge = (level: string) => {
    const cls = level === "allow" ? "bg-green-100 text-green-700" : level === "require_approval" ? "bg-amber-100 text-amber-700" : "bg-red-100 text-red-700";
    return <span className={`text-xs font-medium px-2 py-0.5 rounded ${cls}`}>{level.replace("_", " ")}</span>;
  };

  const resultBadge = (result: string) => {
    const cls = result === "granted" ? "bg-green-100 text-green-700" : result === "denied" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700";
    return <span className={`text-xs font-medium px-2 py-0.5 rounded ${cls}`}>{result}</span>;
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Shield className="h-6 w-6 text-red-600" /> Permissions Protocol
          </h1>
          <p className="text-slate-500 text-sm">Allow / Require Approval / Never — security enforcement for agent actions</p>
        </div>
        <button onClick={() => { fetchRules(); fetchAudits(); fetchPending(); }} className="p-2 rounded hover:bg-slate-100">
          <RefreshCw className="h-4 w-4 text-slate-500" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-slate-100 rounded-lg p-1">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === t.key ? "bg-white text-red-700 shadow-sm" : "text-slate-600 hover:text-slate-900"}`}>
            <t.icon className="h-4 w-4" /> {t.label}
          </button>
        ))}
      </div>

      {/* Rules Tab */}
      {activeTab === "rules" && (
        <div>
          <div className="flex justify-end mb-3">
            <button onClick={() => setShowAddRule(!showAddRule)} className="flex items-center gap-1 px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700">
              <Plus className="h-3.5 w-3.5" /> Add Rule
            </button>
          </div>

          {showAddRule && (
            <div className="bg-indigo-50 rounded-xl border border-indigo-200 p-5 mb-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                <input value={newRule.action_pattern} onChange={(e) => setNewRule({ ...newRule, action_pattern: e.target.value })} placeholder="Action pattern (regex or exact)" className="px-3 py-2 border rounded-lg text-sm" />
                <select value={newRule.permission_level} onChange={(e) => setNewRule({ ...newRule, permission_level: e.target.value })} className="px-3 py-2 border rounded-lg text-sm">
                  <option value="allow">Allow</option>
                  <option value="require_approval">Require Approval</option>
                  <option value="never">Never</option>
                </select>
                <select value={newRule.category} onChange={(e) => setNewRule({ ...newRule, category: e.target.value })} className="px-3 py-2 border rounded-lg text-sm">
                  <option value="general">General</option>
                  <option value="git">Git</option>
                  <option value="deploy">Deploy</option>
                  <option value="file">File</option>
                  <option value="network">Network</option>
                  <option value="security">Security</option>
                  <option value="memory">Memory</option>
                  <option value="admin">Admin</option>
                </select>
                <input value={newRule.description} onChange={(e) => setNewRule({ ...newRule, description: e.target.value })} placeholder="Description" className="px-3 py-2 border rounded-lg text-sm" />
              </div>
              <button onClick={handleAddRule} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700">Save Rule</button>
            </div>
          )}

          <div className="bg-white rounded-xl border border-slate-200 p-5">
            {rules.length === 0 ? (
              <p className="text-slate-400 text-sm py-8 text-center">No rules configured. Default rules will be seeded on first access.</p>
            ) : (
              <div className="space-y-2">
                {rules.map((r) => (
                  <div key={r.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg hover:bg-slate-100">
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      {levelIcon(r.permission_level)}
                      <div className="min-w-0">
                        <p className="text-sm font-mono text-slate-800 truncate">{r.action_pattern}</p>
                        <p className="text-xs text-slate-500">{r.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 ml-3">
                      <span className="text-xs px-1.5 py-0.5 bg-slate-200 rounded text-slate-600">{r.category}</span>
                      {levelBadge(r.permission_level)}
                      <button onClick={() => handleDeleteRule(r.id)} className="p-1 rounded hover:bg-red-100 text-slate-400 hover:text-red-600" title="Deactivate">
                        <XCircle className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Check Tab */}
      {activeTab === "check" && (
        <div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Check Action Permission</h3>
            <div className="flex gap-2">
              <input value={checkAction} onChange={(e) => setCheckAction(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleCheck()}
                placeholder="Action to check (e.g., merge_pr, deploy_production, read_file)" className="flex-1 px-3 py-2 border rounded-lg text-sm" />
              <button onClick={handleCheck} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700">Check</button>
            </div>
          </div>

          {checkResult && (
            <div className={`rounded-xl border p-5 ${checkResult.result === "granted" ? "bg-green-50 border-green-200" : checkResult.result === "denied" ? "bg-red-50 border-red-200" : "bg-amber-50 border-amber-200"}`}>
              <div className="flex items-center gap-3 mb-3">
                {checkResult.result === "granted" ? <ShieldCheck className="h-6 w-6 text-green-600" /> : checkResult.result === "denied" ? <ShieldX className="h-6 w-6 text-red-600" /> : <ShieldAlert className="h-6 w-6 text-amber-600" />}
                <div>
                  <p className="text-lg font-bold">{checkResult.result.toUpperCase()}</p>
                  <p className="text-sm text-slate-600">Action: <span className="font-mono">{checkResult.action}</span></p>
                </div>
              </div>
              {checkResult.matching_rules?.length > 0 && (
                <div className="mt-2">
                  <p className="text-xs text-slate-500 mb-1">Matching Rules:</p>
                  {checkResult.matching_rules.map((r: any) => (
                    <p key={r.id} className="text-xs text-slate-600">- {r.action_pattern} → {r.permission_level} ({r.description})</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Pending Tab */}
      {activeTab === "pending" && (
        <div className="bg-white rounded-xl border border-amber-200 p-5">
          <h3 className="text-sm font-semibold text-amber-700 mb-3">Pending Approvals</h3>
          {pending.length === 0 ? (
            <p className="text-slate-400 text-sm py-8 text-center">No actions pending approval.</p>
          ) : (
            <div className="space-y-2">
              {pending.map((a) => (
                <div key={a.id} className="flex items-center justify-between p-3 bg-amber-50 rounded-lg">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-mono text-slate-800">{a.action}</p>
                    <p className="text-xs text-slate-500">Audit #{a.id} | {a.created_at?.split("T")[0]}</p>
                  </div>
                  <div className="flex gap-2 ml-3">
                    <button onClick={() => handleApproval(a.id, true)} className="px-3 py-1.5 bg-green-600 text-white rounded text-xs font-medium hover:bg-green-700 flex items-center gap-1">
                      <CheckCircle className="h-3.5 w-3.5" /> Approve
                    </button>
                    <button onClick={() => handleApproval(a.id, false)} className="px-3 py-1.5 bg-red-600 text-white rounded text-xs font-medium hover:bg-red-700 flex items-center gap-1">
                      <XCircle className="h-3.5 w-3.5" /> Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Audits Tab */}
      {activeTab === "audits" && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Permission Audit Log</h3>
          {audits.length === 0 ? (
            <p className="text-slate-400 text-sm py-8 text-center">No audit entries yet. Run a permission check to create one.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-2 px-2 text-slate-500 font-medium">ID</th>
                    <th className="text-left py-2 px-2 text-slate-500 font-medium">Action</th>
                    <th className="text-left py-2 px-2 text-slate-500 font-medium">Level</th>
                    <th className="text-left py-2 px-2 text-slate-500 font-medium">Result</th>
                    <th className="text-left py-2 px-2 text-slate-500 font-medium">Approval</th>
                    <th className="text-left py-2 px-2 text-slate-500 font-medium">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {audits.map((a) => (
                    <tr key={a.id} className="border-b border-slate-50 hover:bg-slate-50">
                      <td className="py-2 px-2 font-mono text-slate-600">#{a.id}</td>
                      <td className="py-2 px-2 font-mono text-slate-800">{a.action}</td>
                      <td className="py-2 px-2">{levelBadge(a.permission_level)}</td>
                      <td className="py-2 px-2">{resultBadge(a.result)}</td>
                      <td className="py-2 px-2 text-xs text-slate-500">{a.approval_status || "—"}</td>
                      <td className="py-2 px-2 text-xs text-slate-400">{a.created_at?.split("T")[0]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
