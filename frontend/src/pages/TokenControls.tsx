import { useState, useEffect } from "react";
import {
  getTokenUsageFull,
  getTokenBudget,
  updateTokenBudget,
  getModelBreakdown,
  getUsersActivity,
  getUserActivityDetail,
  getTeamUsage,
  getUsageTrends,
} from "@/lib/api";
import {
  Coins,
  Save,
  Loader2,
  AlertTriangle,
  TrendingUp,
  PieChart,
  Settings2,
  Users,
  Activity,
  BarChart3,
  Clock,
  Shield,
  Filter,
  ChevronRight,
  Zap,
  DollarSign,
  Calendar,
} from "lucide-react";

type TabType = "overview" | "users" | "teams" | "budget" | "trends";

export default function TokenControls() {
  const [activeTab, setActiveTab] = useState<TabType>("overview");
  const [usage, setUsage] = useState<any>(null);
  const [budget, setBudget] = useState<any>(null);
  const [models, setModels] = useState<any[]>([]);
  const [usersActivity, setUsersActivity] = useState<any[]>([]);
  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [teamUsage, setTeamUsage] = useState<any[]>([]);
  const [trends, setTrends] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Budget form
  const [dailyLimit, setDailyLimit] = useState(0);
  const [monthlyLimit, setMonthlyLimit] = useState(0);
  const [monthlyCostLimit, setMonthlyCostLimit] = useState(0);
  const [alertThreshold, setAlertThreshold] = useState(80);
  const [preferredModel, setPreferredModel] = useState("gpt-4o-mini");
  const [enforceLimits, setEnforceLimits] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [usageRes, budgetRes, modelsRes] = await Promise.all([
        getTokenUsageFull(),
        getTokenBudget(),
        getModelBreakdown(),
      ]);
      setUsage(usageRes);
      setBudget(budgetRes);
      setModels(modelsRes);

      // Pre-fill form
      if (budgetRes) {
        setDailyLimit(budgetRes.daily_tokens_limit || 0);
        setMonthlyLimit(budgetRes.monthly_tokens_limit || 0);
        setMonthlyCostLimit(budgetRes.monthly_cost_limit || 0);
        setAlertThreshold(80);
        setPreferredModel(budgetRes.preferred_model || "gpt-4o-mini");
      }

      // Load user activity (non-blocking)
      getUsersActivity().then(setUsersActivity).catch(() => setUsersActivity([]));
      getTeamUsage().then(setTeamUsage).catch(() => setTeamUsage([]));
      getUsageTrends(30).then(setTrends).catch(() => setTrends([]));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const loadUserDetail = async (userId: number) => {
    try {
      const detail = await getUserActivityDetail(userId);
      setSelectedUser(detail);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleSaveBudget = async () => {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      await updateTokenBudget({
        daily_token_limit: dailyLimit,
        monthly_token_limit: monthlyLimit,
        monthly_cost_limit_usd: monthlyCostLimit,
        alert_threshold_percent: alertThreshold,
        preferred_model: preferredModel,
        allowed_models: ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo", "claude-3.5-sonnet", "llama-3.1-8b"],
        enforce_limits: enforceLimits,
      });
      setSuccess("Budget updated successfully!");
      loadData();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
      </div>
    );
  }

  const tabs: { key: TabType; label: string; icon: any }[] = [
    { key: "overview", label: "Overview", icon: BarChart3 },
    { key: "users", label: "User Activity", icon: Users },
    { key: "teams", label: "Teams", icon: Shield },
    { key: "budget", label: "Budget", icon: Settings2 },
    { key: "trends", label: "Trends", icon: TrendingUp },
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 sm:p-3 bg-emerald-100 rounded-xl">
            <Coins className="h-5 w-5 sm:h-6 sm:w-6 text-emerald-600" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900">Token Controls</h1>
            <p className="text-xs sm:text-sm text-slate-500">Per-user monitoring, budgets, and model spending analytics</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Shield className="h-4 w-4" />
          <span>SSO-Ready</span>
        </div>
      </div>

      {/* Alert */}
      {budget?.alert_triggered && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0" />
          <span className="text-sm text-amber-800 font-medium">{budget.alert_message}</span>
        </div>
      )}

      {/* Tab Navigation — scrollable on mobile */}
      <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl overflow-x-auto scrollbar-hide">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 rounded-lg text-xs sm:text-sm font-medium transition-all whitespace-nowrap ${
                activeTab === tab.key
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              <Icon className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
              <span className="hidden sm:inline">{tab.label}</span>
              <span className="sm:hidden">{tab.label.split(" ")[0]}</span>
            </button>
          );
        })}
      </div>

      {/* ================================================================ */}
      {/* OVERVIEW TAB */}
      {/* ================================================================ */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Usage Overview Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <div className="flex items-center gap-2 mb-1">
                <Zap className="h-4 w-4 text-blue-500" />
                <p className="text-xs text-slate-500 uppercase">Total Calls</p>
              </div>
              <p className="text-2xl font-bold text-slate-900">{usage?.total_calls || 0}</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <div className="flex items-center gap-2 mb-1">
                <Activity className="h-4 w-4 text-purple-500" />
                <p className="text-xs text-slate-500 uppercase">Total Tokens</p>
              </div>
              <p className="text-2xl font-bold text-slate-900">{(usage?.total_tokens || 0).toLocaleString()}</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <div className="flex items-center gap-2 mb-1">
                <DollarSign className="h-4 w-4 text-emerald-500" />
                <p className="text-xs text-slate-500 uppercase">Total Cost</p>
              </div>
              <p className="text-2xl font-bold text-emerald-600">${(usage?.total_cost_usd || 0).toFixed(4)}</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <div className="flex items-center gap-2 mb-1">
                <Calendar className="h-4 w-4 text-orange-500" />
                <p className="text-xs text-slate-500 uppercase">Today's Tokens</p>
              </div>
              <p className="text-2xl font-bold text-blue-600">{(budget?.daily_tokens_used || 0).toLocaleString()}</p>
            </div>
          </div>

          {/* Budget Progress */}
          {budget && (budget.monthly_tokens_limit > 0 || budget.monthly_cost_limit > 0) && (
            <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
              <h2 className="font-semibold text-slate-900 flex items-center gap-2">
                <TrendingUp className="h-5 w-5" /> Budget Progress
              </h2>
              {budget.monthly_tokens_limit > 0 && (
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-600">Monthly Tokens</span>
                    <span className="font-medium">{budget.monthly_tokens_used.toLocaleString()} / {budget.monthly_tokens_limit.toLocaleString()}</span>
                  </div>
                  <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        (budget.monthly_tokens_used / budget.monthly_tokens_limit) * 100 >= 80 ? "bg-red-500" :
                        (budget.monthly_tokens_used / budget.monthly_tokens_limit) * 100 >= 50 ? "bg-amber-500" : "bg-emerald-500"
                      }`}
                      style={{ width: `${Math.min((budget.monthly_tokens_used / budget.monthly_tokens_limit) * 100, 100)}%` }}
                    />
                  </div>
                </div>
              )}
              {budget.monthly_cost_limit > 0 && (
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-600">Monthly Cost</span>
                    <span className="font-medium">${budget.monthly_cost_used.toFixed(4)} / ${budget.monthly_cost_limit.toFixed(2)}</span>
                  </div>
                  <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        (budget.monthly_cost_used / budget.monthly_cost_limit) * 100 >= 80 ? "bg-red-500" : "bg-emerald-500"
                      }`}
                      style={{ width: `${Math.min((budget.monthly_cost_used / budget.monthly_cost_limit) * 100, 100)}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Model Breakdown */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
              <h2 className="font-semibold text-slate-900 flex items-center gap-2">
                <PieChart className="h-5 w-5" /> Model Breakdown
              </h2>
              {models.length === 0 ? (
                <p className="text-sm text-slate-400 py-8 text-center">No usage data yet. Use Ask/Plan/Build features to generate data.</p>
              ) : (
                <div className="space-y-3">
                  {models.map((m: any) => (
                    <div key={m.model} className="flex items-center gap-3">
                      <div className="flex-1">
                        <div className="flex justify-between text-sm mb-1">
                          <span className="font-medium text-slate-700">{m.model}</span>
                          <span className="text-slate-500">{m.percentage}%</span>
                        </div>
                        <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                          <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${m.percentage}%` }} />
                        </div>
                        <div className="flex justify-between text-xs text-slate-400 mt-0.5">
                          <span>{m.calls} calls</span>
                          <span>{m.tokens.toLocaleString()} tokens</span>
                          <span>${m.cost.toFixed(4)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Active Users Quick View */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
              <h2 className="font-semibold text-slate-900 flex items-center gap-2">
                <Users className="h-5 w-5" /> Active Users
              </h2>
              {usersActivity.length === 0 ? (
                <div className="text-center py-8">
                  <Users className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm text-slate-400">No users registered yet.</p>
                  <p className="text-xs text-slate-400 mt-1">Users will appear here once SSO is configured.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {usersActivity.slice(0, 5).map((u: any) => (
                    <div
                      key={u.user_id}
                      onClick={() => { setActiveTab("users"); loadUserDetail(u.user_id); }}
                      className="flex items-center justify-between p-2 hover:bg-slate-50 rounded-lg cursor-pointer transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <div className="h-8 w-8 bg-indigo-100 rounded-full flex items-center justify-center">
                          <span className="text-xs font-bold text-indigo-600">{u.name.charAt(0).toUpperCase()}</span>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-slate-700">{u.name}</p>
                          <p className="text-xs text-slate-400">{u.team || u.role}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-mono text-slate-600">{u.total_tokens.toLocaleString()}</p>
                        <p className="text-xs text-emerald-500">${u.total_cost.toFixed(4)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Recent Usage */}
          {usage?.recent?.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
              <div className="p-4 border-b border-slate-200">
                <h3 className="font-semibold text-slate-900">Recent Usage Log</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="text-left px-4 py-2 font-medium text-slate-600">Action</th>
                      <th className="text-left px-4 py-2 font-medium text-slate-600">Feature</th>
                      <th className="text-left px-4 py-2 font-medium text-slate-600">Model</th>
                      <th className="text-right px-4 py-2 font-medium text-slate-600">Tokens</th>
                      <th className="text-right px-4 py-2 font-medium text-slate-600">Cost</th>
                      <th className="text-right px-4 py-2 font-medium text-slate-600">Time</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {usage.recent.slice(0, 20).map((r: any) => (
                      <tr key={r.id} className="hover:bg-slate-50">
                        <td className="px-4 py-2 text-slate-700">{r.action}</td>
                        <td className="px-4 py-2"><span className="px-1.5 py-0.5 bg-slate-100 rounded text-xs">{r.feature}</span></td>
                        <td className="px-4 py-2 text-slate-500">{r.model}</td>
                        <td className="px-4 py-2 text-right font-mono">{r.total_tokens.toLocaleString()}</td>
                        <td className="px-4 py-2 text-right font-mono text-emerald-600">${r.estimated_cost_usd.toFixed(5)}</td>
                        <td className="px-4 py-2 text-right text-slate-400 text-xs">{r.created_at ? new Date(r.created_at).toLocaleTimeString() : ""}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ================================================================ */}
      {/* USER ACTIVITY TAB */}
      {/* ================================================================ */}
      {activeTab === "users" && (
        <div className="space-y-6">
          {selectedUser ? (
            /* User Detail View */
            <div className="space-y-6">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setSelectedUser(null)}
                  className="text-sm text-slate-500 hover:text-slate-700 flex items-center gap-1"
                >
                  <ChevronRight className="h-4 w-4 rotate-180" /> Back to all users
                </button>
              </div>

              {/* User Header */}
              <div className="bg-white rounded-xl border border-slate-200 p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="h-14 w-14 bg-indigo-100 rounded-full flex items-center justify-center">
                      <span className="text-xl font-bold text-indigo-600">{selectedUser.name.charAt(0).toUpperCase()}</span>
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-slate-900">{selectedUser.name}</h2>
                      <p className="text-sm text-slate-500">{selectedUser.email}</p>
                      <p className="text-xs text-slate-400 mt-0.5">Team: {selectedUser.team || "Unassigned"}</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* User Stats Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-white rounded-xl border border-slate-200 p-4">
                  <p className="text-xs text-slate-500 uppercase">Total Tokens</p>
                  <p className="text-xl font-bold text-slate-900">{selectedUser.total_tokens.toLocaleString()}</p>
                </div>
                <div className="bg-white rounded-xl border border-slate-200 p-4">
                  <p className="text-xs text-slate-500 uppercase">Total Cost</p>
                  <p className="text-xl font-bold text-emerald-600">${selectedUser.total_cost.toFixed(4)}</p>
                </div>
                <div className="bg-white rounded-xl border border-slate-200 p-4">
                  <p className="text-xs text-slate-500 uppercase">Today</p>
                  <p className="text-xl font-bold text-blue-600">{selectedUser.daily_tokens.toLocaleString()}</p>
                </div>
                <div className="bg-white rounded-xl border border-slate-200 p-4">
                  <p className="text-xs text-slate-500 uppercase">This Month</p>
                  <p className="text-xl font-bold text-purple-600">{selectedUser.monthly_tokens.toLocaleString()}</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Top Models Used */}
                <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
                  <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                    <PieChart className="h-4 w-4" /> Models Used
                  </h3>
                  {selectedUser.top_models.length === 0 ? (
                    <p className="text-sm text-slate-400 text-center py-4">No model usage yet</p>
                  ) : (
                    <div className="space-y-2">
                      {selectedUser.top_models.map((m: any) => (
                        <div key={m.model} className="flex items-center justify-between text-sm">
                          <span className="text-slate-700 font-medium">{m.model}</span>
                          <div className="flex items-center gap-3">
                            <span className="text-slate-400">{m.calls} calls</span>
                            <span className="font-mono text-slate-600">{m.tokens.toLocaleString()}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Top Features Used */}
                <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
                  <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                    <Activity className="h-4 w-4" /> Features Used
                  </h3>
                  {selectedUser.top_features.length === 0 ? (
                    <p className="text-sm text-slate-400 text-center py-4">No feature usage yet</p>
                  ) : (
                    <div className="space-y-2">
                      {selectedUser.top_features.map((f: any) => (
                        <div key={f.feature} className="flex items-center justify-between text-sm">
                          <span className="px-2 py-0.5 bg-slate-100 rounded text-slate-700">{f.feature}</span>
                          <div className="flex items-center gap-3">
                            <span className="text-slate-400">{f.calls} calls</span>
                            <span className="font-mono text-slate-600">{f.tokens.toLocaleString()}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* User's Recent Activity */}
              {selectedUser.recent_activity.length > 0 && (
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
                  <div className="p-4 border-b border-slate-200">
                    <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                      <Clock className="h-4 w-4" /> Recent Activity
                    </h3>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-50">
                        <tr>
                          <th className="text-left px-4 py-2 font-medium text-slate-600">Action</th>
                          <th className="text-left px-4 py-2 font-medium text-slate-600">Feature</th>
                          <th className="text-left px-4 py-2 font-medium text-slate-600">Model</th>
                          <th className="text-right px-4 py-2 font-medium text-slate-600">Tokens</th>
                          <th className="text-right px-4 py-2 font-medium text-slate-600">Cost</th>
                          <th className="text-left px-4 py-2 font-medium text-slate-600">Status</th>
                          <th className="text-right px-4 py-2 font-medium text-slate-600">Time</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {selectedUser.recent_activity.map((a: any) => (
                          <tr key={a.id} className="hover:bg-slate-50">
                            <td className="px-4 py-2 text-slate-700">{a.action}</td>
                            <td className="px-4 py-2"><span className="px-1.5 py-0.5 bg-slate-100 rounded text-xs">{a.feature}</span></td>
                            <td className="px-4 py-2 text-slate-500">{a.model}</td>
                            <td className="px-4 py-2 text-right font-mono">{a.tokens.toLocaleString()}</td>
                            <td className="px-4 py-2 text-right font-mono text-emerald-600">${a.cost.toFixed(5)}</td>
                            <td className="px-4 py-2">
                              <span className={`px-1.5 py-0.5 rounded text-xs ${
                                a.status === "success" ? "bg-green-100 text-green-700" :
                                a.status === "error" ? "bg-red-100 text-red-700" : "bg-slate-100 text-slate-600"
                              }`}>{a.status}</span>
                            </td>
                            <td className="px-4 py-2 text-right text-slate-400 text-xs">{a.created_at ? new Date(a.created_at).toLocaleTimeString() : ""}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* User Sessions */}
              {selectedUser.sessions.length > 0 && (
                <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
                  <h3 className="font-semibold text-slate-900">Work Sessions</h3>
                  <div className="space-y-2">
                    {selectedUser.sessions.map((s: any) => (
                      <div key={s.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                        <div>
                          <p className="text-sm font-medium text-slate-700">{s.title}</p>
                          <p className="text-xs text-slate-400">{s.type} | {s.messages} messages</p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-mono text-slate-600">{s.tokens.toLocaleString()} tokens</p>
                          <span className={`text-xs px-1.5 py-0.5 rounded ${
                            s.status === "active" ? "bg-green-100 text-green-700" :
                            s.status === "completed" ? "bg-blue-100 text-blue-700" : "bg-slate-100 text-slate-600"
                          }`}>{s.status}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Users List View */
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900">All User Activity</h2>
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <Filter className="h-4 w-4" />
                  <span>{usersActivity.length} users tracked</span>
                </div>
              </div>

              {usersActivity.length === 0 ? (
                <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
                  <Users className="h-12 w-12 text-slate-300 mx-auto mb-3" />
                  <h3 className="text-lg font-medium text-slate-700 mb-2">No Users Yet</h3>
                  <p className="text-sm text-slate-400 max-w-md mx-auto">
                    Users will appear here once SSO integration is configured.
                    The system is ready to track per-user activity, token usage, model preferences, and costs.
                  </p>
                  <div className="mt-6 p-4 bg-slate-50 rounded-lg text-left max-w-sm mx-auto">
                    <p className="text-xs font-medium text-slate-600 mb-2">What will be tracked per user:</p>
                    <ul className="text-xs text-slate-500 space-y-1">
                      <li className="flex items-center gap-1"><Zap className="h-3 w-3" /> Token consumption per model</li>
                      <li className="flex items-center gap-1"><DollarSign className="h-3 w-3" /> Cost attribution</li>
                      <li className="flex items-center gap-1"><Activity className="h-3 w-3" /> Feature usage (Ask, Plan, Build, Review)</li>
                      <li className="flex items-center gap-1"><Clock className="h-3 w-3" /> Session history and duration</li>
                      <li className="flex items-center gap-1"><Shield className="h-3 w-3" /> Per-user budget enforcement</li>
                    </ul>
                  </div>
                </div>
              ) : (
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-50">
                      <tr>
                        <th className="text-left px-4 py-3 font-medium text-slate-600">User</th>
                        <th className="text-left px-4 py-3 font-medium text-slate-600">Team</th>
                        <th className="text-right px-4 py-3 font-medium text-slate-600">Calls</th>
                        <th className="text-right px-4 py-3 font-medium text-slate-600">Tokens</th>
                        <th className="text-right px-4 py-3 font-medium text-slate-600">Cost</th>
                        <th className="text-left px-4 py-3 font-medium text-slate-600">Models</th>
                        <th className="text-right px-4 py-3 font-medium text-slate-600">Last Active</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {usersActivity.map((u: any) => (
                        <tr
                          key={u.user_id}
                          onClick={() => loadUserDetail(u.user_id)}
                          className="hover:bg-slate-50 cursor-pointer"
                        >
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <div className="h-8 w-8 bg-indigo-100 rounded-full flex items-center justify-center">
                                <span className="text-xs font-bold text-indigo-600">{u.name.charAt(0).toUpperCase()}</span>
                              </div>
                              <div>
                                <p className="font-medium text-slate-700">{u.name}</p>
                                <p className="text-xs text-slate-400">{u.email}</p>
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-slate-500">{u.team || "—"}</td>
                          <td className="px-4 py-3 text-right font-mono">{u.total_calls}</td>
                          <td className="px-4 py-3 text-right font-mono">{u.total_tokens.toLocaleString()}</td>
                          <td className="px-4 py-3 text-right font-mono text-emerald-600">${u.total_cost.toFixed(4)}</td>
                          <td className="px-4 py-3">
                            <div className="flex flex-wrap gap-1">
                              {u.models_used.slice(0, 2).map((m: string) => (
                                <span key={m} className="px-1.5 py-0.5 bg-slate-100 rounded text-xs text-slate-600">{m}</span>
                              ))}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-right text-xs text-slate-400">
                            {u.last_active ? new Date(u.last_active).toLocaleDateString() : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ================================================================ */}
      {/* TEAMS TAB */}
      {/* ================================================================ */}
      {activeTab === "teams" && (
        <div className="space-y-6">
          <h2 className="text-lg font-semibold text-slate-900">Team Usage Breakdown</h2>

          {teamUsage.length === 0 ? (
            <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
              <Shield className="h-12 w-12 text-slate-300 mx-auto mb-3" />
              <h3 className="text-lg font-medium text-slate-700 mb-2">No Team Data Yet</h3>
              <p className="text-sm text-slate-400">Teams will appear once users are assigned to teams via SSO attributes.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {teamUsage.map((t: any) => (
                <div key={t.team} className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-slate-900">{t.team}</h3>
                    <span className="text-xs text-slate-400">{t.members} members</span>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <p className="text-xs text-slate-500">Tokens</p>
                      <p className="text-lg font-bold text-slate-900">{t.total_tokens.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">Cost</p>
                      <p className="text-lg font-bold text-emerald-600">${t.total_cost.toFixed(4)}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-slate-400">
                    <span>Top model: <strong className="text-slate-600">{t.top_model}</strong></span>
                    <span>Top feature: <strong className="text-slate-600">{t.top_feature}</strong></span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ================================================================ */}
      {/* BUDGET TAB */}
      {/* ================================================================ */}
      {activeTab === "budget" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Budget Settings */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
              <h2 className="font-semibold text-slate-900 flex items-center gap-2">
                <Settings2 className="h-5 w-5" /> Global Budget Configuration
              </h2>
              <p className="text-xs text-slate-400">These limits apply globally. Per-user limits can be set when SSO is active.</p>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Daily Token Limit (0 = unlimited)</label>
                  <input type="number" value={dailyLimit} onChange={(e) => setDailyLimit(Number(e.target.value))} className="w-full p-2 border border-slate-300 rounded-lg text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Monthly Token Limit</label>
                  <input type="number" value={monthlyLimit} onChange={(e) => setMonthlyLimit(Number(e.target.value))} className="w-full p-2 border border-slate-300 rounded-lg text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Monthly Cost Limit (USD)</label>
                  <input type="number" step="0.01" value={monthlyCostLimit} onChange={(e) => setMonthlyCostLimit(Number(e.target.value))} className="w-full p-2 border border-slate-300 rounded-lg text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Alert Threshold (%)</label>
                  <input type="number" min="0" max="100" value={alertThreshold} onChange={(e) => setAlertThreshold(Number(e.target.value))} className="w-full p-2 border border-slate-300 rounded-lg text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Preferred Model</label>
                  <select value={preferredModel} onChange={(e) => setPreferredModel(e.target.value)} className="w-full p-2 border border-slate-300 rounded-lg text-sm">
                    <option value="gpt-4o-mini">GPT-4o Mini (cheapest)</option>
                    <option value="gpt-4o">GPT-4o (best quality)</option>
                    <option value="gpt-3.5-turbo">GPT-3.5 Turbo (fast)</option>
                    <option value="claude-3.5-sonnet">Claude 3.5 Sonnet</option>
                    <option value="llama-3.1-8b">Llama 3.1 8B (free)</option>
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="enforce-limits"
                    checked={enforceLimits}
                    onChange={(e) => setEnforceLimits(e.target.checked)}
                    className="rounded border-slate-300"
                  />
                  <label htmlFor="enforce-limits" className="text-xs text-slate-600">
                    Enforce limits (block requests when budget exceeded)
                  </label>
                </div>
              </div>
              <button
                onClick={handleSaveBudget}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white rounded-lg text-sm font-medium"
              >
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                Save Budget
              </button>
              {success && <p className="text-sm text-green-600">{success}</p>}
              {error && <p className="text-sm text-red-600">{error}</p>}
            </div>

            {/* Budget Status */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
              <h2 className="font-semibold text-slate-900 flex items-center gap-2">
                <TrendingUp className="h-5 w-5" /> Current Status
              </h2>
              <div className="space-y-4">
                <div className="p-3 bg-slate-50 rounded-lg">
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-600">Daily Tokens</span>
                    <span className="font-medium font-mono">
                      {(budget?.daily_tokens_used || 0).toLocaleString()}
                      {budget?.daily_tokens_limit > 0 ? ` / ${budget.daily_tokens_limit.toLocaleString()}` : " (unlimited)"}
                    </span>
                  </div>
                  {budget?.daily_tokens_limit > 0 && (
                    <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 rounded-full"
                        style={{ width: `${Math.min((budget.daily_tokens_used / budget.daily_tokens_limit) * 100, 100)}%` }}
                      />
                    </div>
                  )}
                </div>
                <div className="p-3 bg-slate-50 rounded-lg">
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-600">Monthly Tokens</span>
                    <span className="font-medium font-mono">
                      {(budget?.monthly_tokens_used || 0).toLocaleString()}
                      {budget?.monthly_tokens_limit > 0 ? ` / ${budget.monthly_tokens_limit.toLocaleString()}` : " (unlimited)"}
                    </span>
                  </div>
                  {budget?.monthly_tokens_limit > 0 && (
                    <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-purple-500 rounded-full"
                        style={{ width: `${Math.min((budget.monthly_tokens_used / budget.monthly_tokens_limit) * 100, 100)}%` }}
                      />
                    </div>
                  )}
                </div>
                <div className="p-3 bg-slate-50 rounded-lg">
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-600">Monthly Cost</span>
                    <span className="font-medium font-mono">
                      ${(budget?.monthly_cost_used || 0).toFixed(4)}
                      {budget?.monthly_cost_limit > 0 ? ` / $${budget.monthly_cost_limit.toFixed(2)}` : " (unlimited)"}
                    </span>
                  </div>
                  {budget?.monthly_cost_limit > 0 && (
                    <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 rounded-full"
                        style={{ width: `${Math.min((budget.monthly_cost_used / budget.monthly_cost_limit) * 100, 100)}%` }}
                      />
                    </div>
                  )}
                </div>
                <div className="p-3 bg-slate-50 rounded-lg">
                  <p className="text-xs text-slate-500 mb-1">Allowed Models</p>
                  <div className="flex flex-wrap gap-1">
                    {(budget?.allowed_models || []).map((m: string) => (
                      <span key={m} className="px-2 py-0.5 bg-white border border-slate-200 rounded text-xs text-slate-600">{m}</span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ================================================================ */}
      {/* TRENDS TAB */}
      {/* ================================================================ */}
      {activeTab === "trends" && (
        <div className="space-y-6">
          <h2 className="text-lg font-semibold text-slate-900">Usage Trends (Last 30 Days)</h2>

          {trends.length === 0 ? (
            <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
              <TrendingUp className="h-12 w-12 text-slate-300 mx-auto mb-3" />
              <h3 className="text-lg font-medium text-slate-700 mb-2">No Trend Data</h3>
              <p className="text-sm text-slate-400">Usage trends will appear here once you start using AI features.</p>
            </div>
          ) : (
            <>
              {/* Simple Bar Chart */}
              <div className="bg-white rounded-xl border border-slate-200 p-5">
                <h3 className="font-semibold text-slate-900 mb-4">Daily Token Usage</h3>
                <div className="flex items-end gap-0.5 h-40">
                  {trends.map((day: any) => {
                    const maxTokens = Math.max(...trends.map((d: any) => d.tokens), 1);
                    const height = (day.tokens / maxTokens) * 100;
                    return (
                      <div
                        key={day.date}
                        className="flex-1 group relative"
                        title={`${day.date}: ${day.tokens.toLocaleString()} tokens, $${day.cost.toFixed(4)}`}
                      >
                        <div
                          className="bg-indigo-400 hover:bg-indigo-500 rounded-t transition-all mx-px"
                          style={{ height: `${Math.max(height, 1)}%` }}
                        />
                      </div>
                    );
                  })}
                </div>
                <div className="flex justify-between text-xs text-slate-400 mt-2">
                  <span>{trends[0]?.date}</span>
                  <span>{trends[trends.length - 1]?.date}</span>
                </div>
              </div>

              {/* Trend Table */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="p-4 border-b border-slate-200">
                  <h3 className="font-semibold text-slate-900">Daily Breakdown</h3>
                </div>
                <div className="overflow-x-auto max-h-80 overflow-y-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-50 sticky top-0">
                      <tr>
                        <th className="text-left px-4 py-2 font-medium text-slate-600">Date</th>
                        <th className="text-right px-4 py-2 font-medium text-slate-600">Calls</th>
                        <th className="text-right px-4 py-2 font-medium text-slate-600">Tokens</th>
                        <th className="text-right px-4 py-2 font-medium text-slate-600">Cost</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {[...trends].reverse().filter((d: any) => d.tokens > 0).map((d: any) => (
                        <tr key={d.date} className="hover:bg-slate-50">
                          <td className="px-4 py-2 text-slate-700">{d.date}</td>
                          <td className="px-4 py-2 text-right font-mono">{d.calls}</td>
                          <td className="px-4 py-2 text-right font-mono">{d.tokens.toLocaleString()}</td>
                          <td className="px-4 py-2 text-right font-mono text-emerald-600">${d.cost.toFixed(4)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
