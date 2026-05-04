import { useState, useEffect } from "react";
import { getTokenUsageFull, getTokenBudget, updateTokenBudget, getModelBreakdown } from "@/lib/api";
import { Coins, Save, Loader2, AlertTriangle, TrendingUp, PieChart, Settings2 } from "lucide-react";

export default function TokenControls() {
  const [usage, setUsage] = useState<any>(null);
  const [budget, setBudget] = useState<any>(null);
  const [models, setModels] = useState<any[]>([]);
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
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
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
        allowed_models: ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
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

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-3 bg-emerald-100 rounded-xl">
          <Coins className="h-6 w-6 text-emerald-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Token Controls</h1>
          <p className="text-slate-500">Monitor usage, set budgets, and control model spending</p>
        </div>
      </div>

      {/* Alert */}
      {budget?.alert_triggered && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0" />
          <span className="text-sm text-amber-800 font-medium">{budget.alert_message}</span>
        </div>
      )}

      {/* Usage Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-xs text-slate-500 uppercase">Total Calls</p>
          <p className="text-2xl font-bold text-slate-900">{usage?.total_calls || 0}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-xs text-slate-500 uppercase">Total Tokens</p>
          <p className="text-2xl font-bold text-slate-900">{(usage?.total_tokens || 0).toLocaleString()}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-xs text-slate-500 uppercase">Total Cost</p>
          <p className="text-2xl font-bold text-emerald-600">${(usage?.total_cost_usd || 0).toFixed(4)}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-xs text-slate-500 uppercase">Today's Tokens</p>
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
        {/* Budget Settings */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
          <h2 className="font-semibold text-slate-900 flex items-center gap-2">
            <Settings2 className="h-5 w-5" /> Budget Configuration
          </h2>
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
              </select>
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
  );
}
