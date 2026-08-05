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
import { showToast } from "@/components/Toast";
import { apiFetch } from "@/lib/api";
import Pagination from "@/components/Pagination";

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
  const [activeTab, setActiveTab] = useState<"rules" | "check" | "audits" | "pending" | "grants">("rules");
  const [checkAction, setCheckAction] = useState("");
  const [checkResult, setCheckResult] = useState<any>(null);
  const [showAddRule, setShowAddRule] = useState(false);
  const [newRule, setNewRule] = useState({ action_pattern: "", permission_level: "require_approval", category: "general", description: "" });
  const [rulesPage, setRulesPage] = useState(1);
  const rulesPerPage = 10;
  const [grants, setGrants] = useState<any[]>([]);
  const [capabilities, setCapabilities] = useState<Record<string, string[]>>({});
  const [showAddGrant, setShowAddGrant] = useState(false);
  const [newGrant, setNewGrant] = useState({
    capability: "pull_request:create",
    subject_type: "user",
    subject_id: "",
    permission_level: "allow",
    reason: "",
    expires_hours: 24,
  });

  const fetchRules = async () => {
    try {
      const res = await apiFetch(`/api/permissions/rules`);
      if (res.ok) setRules(await res.json());
      else showToast("error", `Failed to load rules (${res.status})`);
    } catch (err) { showToast("error", "Network error loading rules"); }
  };

  const fetchAudits = async () => {
    try {
      const res = await apiFetch(`/api/permissions/audits?limit=50`);
      if (res.ok) setAudits(await res.json());
      else showToast("error", `Failed to load audits (${res.status})`);
    } catch (err) { showToast("error", "Network error loading audits"); }
  };

  const fetchPending = async () => {
    try {
      const res = await apiFetch(`/api/permissions/audits/pending`);
      if (res.ok) setPending(await res.json());
      else showToast("error", `Failed to load pending (${res.status})`);
    } catch (err) { showToast("error", "Network error loading pending"); }
  };

  const fetchGrants = async () => {
    try {
      const [gRes, cRes] = await Promise.all([
        apiFetch(`/api/permissions/grants?active_only=false`),
        apiFetch(`/api/permissions/capabilities`),
      ]);
      if (gRes.ok) setGrants(await gRes.json());
      if (cRes.ok) {
        const body = await cRes.json();
        setCapabilities(body.capabilities || {});
      }
    } catch (err) { showToast("error", "Network error loading grants"); }
  };

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchRules(), fetchAudits(), fetchPending(), fetchGrants()]).finally(() => setLoading(false));
  }, []);

  const handleCheck = async () => {
    if (!checkAction.trim()) return;
    try {
      const res = await apiFetch(`/api/permissions/check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: checkAction }),
      });
      if (res.ok) {
        setCheckResult(await res.json());
        fetchAudits();
        fetchPending();
      } else {
        showToast("error", `Permission check failed (${res.status})`);
      }
    } catch (err) { showToast("error", "Network error checking permission"); }
  };

  const handleAddRule = async () => {
    if (!newRule.action_pattern.trim()) return;
    try {
      await apiFetch(`/api/permissions/rules`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newRule),
      });
      setShowAddRule(false);
      setNewRule({ action_pattern: "", permission_level: "require_approval", category: "general", description: "" });
      showToast("success", "Rule added successfully");
      fetchRules();
    } catch (err) { showToast("error", "Failed to add rule"); }
  };

  const handleApproval = async (auditId: number, approved: boolean) => {
    try {
      await apiFetch(`/api/permissions/audits/${auditId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved, approved_by: "admin", reason: approved ? "Approved via dashboard" : "Rejected via dashboard" }),
      });
      showToast("success", approved ? "Action approved" : "Action rejected");
      fetchAudits();
      fetchPending();
    } catch (err) { showToast("error", "Failed to process approval"); }
  };

  const handleDeleteRule = async (ruleId: number) => {
    try {
      await apiFetch(`/api/permissions/rules/${ruleId}`, { method: "DELETE" });
      showToast("info", "Rule deleted");
      fetchRules();
    } catch (err) { showToast("error", "Failed to delete rule"); }
  };

  const handleAddGrant = async () => {
    if (!newGrant.capability.trim()) return;
    const expires = new Date(Date.now() + Number(newGrant.expires_hours || 24) * 3600_000).toISOString();
    try {
      const res = await apiFetch(`/api/permissions/grants`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          capability: newGrant.capability,
          subject_type: newGrant.subject_type,
          subject_id: newGrant.subject_id,
          permission_level: newGrant.permission_level,
          reason: newGrant.reason,
          expires_at: expires,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        showToast("error", err.detail || `Failed to create grant (${res.status})`);
        return;
      }
      setShowAddGrant(false);
      showToast("success", "Temporary grant created");
      fetchGrants();
    } catch (err) { showToast("error", "Failed to create grant"); }
  };

  const handleRevokeGrant = async (grantId: number) => {
    try {
      const res = await apiFetch(`/api/permissions/grants/${grantId}/revoke`, { method: "POST" });
      if (!res.ok) {
        showToast("error", `Revoke failed (${res.status})`);
        return;
      }
      showToast("info", "Grant revoked");
      fetchGrants();
    } catch (err) { showToast("error", "Failed to revoke grant"); }
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
    { key: "grants" as const, label: `Grants (${grants.filter((g) => g.active).length})`, icon: Clock },
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
        <button onClick={() => { fetchRules(); fetchAudits(); fetchPending(); fetchGrants(); }} className="p-2 rounded hover:bg-slate-100">
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
              <>
                <div className="space-y-2">
                  {rules.slice((rulesPage - 1) * rulesPerPage, rulesPage * rulesPerPage).map((r) => (
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
                <Pagination currentPage={rulesPage} totalItems={rules.length} pageSize={rulesPerPage} onPageChange={setRulesPage} />
              </>
            )}
          </div>
        </div>
      )}

      {/* Temporary Grants Tab */}
      {activeTab === "grants" && (
        <div>
          <div className="flex justify-between items-center mb-3 gap-3 flex-wrap">
            <p className="text-sm text-slate-500">Temporary capability grants expire automatically and can override baseline rules while active.</p>
            <button onClick={() => setShowAddGrant(!showAddGrant)} className="flex items-center gap-1 px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700">
              <Plus className="h-3.5 w-3.5" /> Add Grant
            </button>
          </div>
          {showAddGrant && (
            <div className="bg-indigo-50 rounded-xl border border-indigo-200 p-5 mb-4 space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <select
                  value={newGrant.capability}
                  onChange={(e) => setNewGrant({ ...newGrant, capability: e.target.value })}
                  className="px-3 py-2 border rounded-lg text-sm"
                >
                  {Object.keys(capabilities).length === 0 ? (
                    <option value={newGrant.capability}>{newGrant.capability}</option>
                  ) : (
                    Object.keys(capabilities).map((cap) => (
                      <option key={cap} value={cap}>{cap}</option>
                    ))
                  )}
                </select>
                <select value={newGrant.subject_type} onChange={(e) => setNewGrant({ ...newGrant, subject_type: e.target.value })} className="px-3 py-2 border rounded-lg text-sm">
                  <option value="user">User</option>
                  <option value="agent">Agent</option>
                  <option value="tool">Tool</option>
                  <option value="workspace">Workspace</option>
                </select>
                <input value={newGrant.subject_id} onChange={(e) => setNewGrant({ ...newGrant, subject_id: e.target.value })} placeholder="Subject id (user id / agent key / workspace path)" className="px-3 py-2 border rounded-lg text-sm" />
                <select value={newGrant.permission_level} onChange={(e) => setNewGrant({ ...newGrant, permission_level: e.target.value })} className="px-3 py-2 border rounded-lg text-sm">
                  <option value="allow">Allow</option>
                  <option value="require_approval">Require Approval</option>
                  <option value="never">Never</option>
                </select>
                <input type="number" min={1} value={newGrant.expires_hours} onChange={(e) => setNewGrant({ ...newGrant, expires_hours: Number(e.target.value) })} placeholder="Expires in hours" className="px-3 py-2 border rounded-lg text-sm" />
                <input value={newGrant.reason} onChange={(e) => setNewGrant({ ...newGrant, reason: e.target.value })} placeholder="Reason" className="px-3 py-2 border rounded-lg text-sm" />
              </div>
              <button onClick={handleAddGrant} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700">Save Grant</button>
            </div>
          )}
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2">
            {grants.length === 0 ? (
              <p className="text-slate-400 text-sm py-8 text-center">No capability grants yet.</p>
            ) : (
              grants.map((g) => (
                <div key={g.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-mono text-slate-800 truncate">{g.capability}</p>
                    <p className="text-xs text-slate-500">
                      {g.subject_type}:{g.subject_id || "*"} · expires {g.expires_at ? new Date(g.expires_at).toLocaleString() : "—"}
                      {g.reason ? ` · ${g.reason}` : ""}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {levelBadge(g.permission_level)}
                    <span className={`text-xs px-2 py-0.5 rounded ${g.active ? "bg-green-100 text-green-700" : "bg-slate-200 text-slate-600"}`}>
                      {g.active ? "active" : g.revoked_at ? "revoked" : "expired"}
                    </span>
                    {g.active && (
                      <button onClick={() => handleRevokeGrant(g.id)} className="text-xs text-red-600 hover:text-red-700">Revoke</button>
                    )}
                  </div>
                </div>
              ))
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
              {checkResult.grant_applied && (
                <p className="text-xs text-slate-600 mt-2">
                  Temporary grant applied: <span className="font-mono">{checkResult.grant_applied.capability}</span> (#{checkResult.grant_applied.id})
                </p>
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
