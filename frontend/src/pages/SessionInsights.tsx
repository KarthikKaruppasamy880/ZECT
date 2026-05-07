import { useState, useEffect } from "react";
import {
  BarChart3, Zap, DollarSign, Clock, Activity, TrendingUp,
} from "lucide-react";
import {
  getSessionInsightsOverview, getSessionDailyBreakdown,
  getSessionModelUsage, getSessionFeatureUsage,
} from "@/lib/api";

export default function SessionInsights() {
  const [overview, setOverview] = useState<any>(null);
  const [daily, setDaily] = useState<any[]>([]);
  const [modelUsage, setModelUsage] = useState<any[]>([]);
  const [featureUsage, setFeatureUsage] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [days, setDays] = useState(30);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError("");
        const [ov, dl, mu, fu] = await Promise.all([
          getSessionInsightsOverview(days),
          getSessionDailyBreakdown(Math.min(days, 14)),
          getSessionModelUsage(days),
          getSessionFeatureUsage(days),
        ]);
        setOverview(ov);
        setDaily(dl || []);
        setModelUsage(mu || []);
        setFeatureUsage(fu || []);
      } catch (e: any) {
        setError(e.message || "Failed to load insights");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [days]);

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <BarChart3 className="h-6 w-6 text-emerald-600" /> Session Insights
          </h1>
          <p className="text-sm text-slate-500 mt-1">Usage analytics, cost tracking, and quality metrics</p>
        </div>
        <select
          value={days}
          onChange={e => setDays(Number(e.target.value))}
          className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm"
        >
          <option value={7}>Last 7 days</option>
          <option value={14}>Last 14 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">{error}</div>
      )}

      {/* Overview Cards */}
      {overview && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            icon={<Activity className="h-5 w-5 text-blue-600" />}
            label="Total Sessions"
            value={overview.sessions?.total ?? 0}
            sub={`${overview.sessions?.active ?? 0} active`}
            bg="bg-blue-50"
          />
          <StatCard
            icon={<Zap className="h-5 w-5 text-amber-600" />}
            label="Total Tokens"
            value={formatNumber(overview.tokens?.total ?? 0)}
            sub={`${overview.tokens?.total_requests ?? 0} requests`}
            bg="bg-amber-50"
          />
          <StatCard
            icon={<DollarSign className="h-5 w-5 text-emerald-600" />}
            label="Total Cost"
            value={`$${(overview.tokens?.total_cost_usd ?? 0).toFixed(2)}`}
            sub={`$${(overview.tokens?.avg_cost_per_request ?? 0).toFixed(4)}/req`}
            bg="bg-emerald-50"
          />
          <StatCard
            icon={<TrendingUp className="h-5 w-5 text-purple-600" />}
            label="Quality Score"
            value={`${(overview.quality?.avg_review_score ?? 0).toFixed(0)}%`}
            sub={`${overview.quality?.reviews_completed ?? 0} reviews`}
            bg="bg-purple-50"
          />
        </div>
      )}

      {/* Daily Breakdown */}
      {daily.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <h3 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <Clock className="h-4 w-4" /> Daily Usage
          </h3>
          <div className="space-y-2">
            {daily.map((d: any) => {
              const maxTokens = Math.max(...daily.map((x: any) => x.tokens || 0), 1);
              const pct = Math.round(((d.tokens || 0) / maxTokens) * 100);
              return (
                <div key={d.date} className="flex items-center gap-3">
                  <span className="text-xs text-slate-500 w-20">{d.date}</span>
                  <div className="flex-1 bg-slate-100 rounded-full h-5 overflow-hidden">
                    <div
                      className="bg-emerald-500 h-full rounded-full transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-xs text-slate-600 w-24 text-right">
                    {formatNumber(d.tokens)} tokens
                  </span>
                  <span className="text-xs text-slate-400 w-16 text-right">
                    ${(d.cost_usd || 0).toFixed(2)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        {/* Model Usage */}
        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <h3 className="font-semibold text-slate-900 mb-4">Model Usage</h3>
          {modelUsage.length === 0 ? (
            <p className="text-sm text-slate-500">No model usage data yet</p>
          ) : (
            <div className="space-y-3">
              {modelUsage.map((m: any) => (
                <div key={m.model} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-slate-700">{m.model || "Unknown"}</p>
                    <p className="text-xs text-slate-400">{m.requests} requests</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-slate-700">{formatNumber(m.tokens)} tokens</p>
                    <p className="text-xs text-slate-400">${(m.cost_usd || 0).toFixed(4)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Feature Usage */}
        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <h3 className="font-semibold text-slate-900 mb-4">Feature Usage</h3>
          {featureUsage.length === 0 ? (
            <p className="text-sm text-slate-500">No feature usage data yet</p>
          ) : (
            <div className="space-y-3">
              {featureUsage.map((f: any) => (
                <div key={f.feature} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-slate-700 capitalize">{f.feature?.replace(/_/g, " ") || "Unknown"}</p>
                    <p className="text-xs text-slate-400">{f.requests} requests</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-slate-700">{formatNumber(f.tokens)} tokens</p>
                    <p className="text-xs text-slate-400">${(f.cost_usd || 0).toFixed(4)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, sub, bg }: { icon: React.ReactNode; label: string; value: string | number; sub: string; bg: string }) {
  return (
    <div className={`${bg} rounded-xl p-4`}>
      <div className="flex items-center gap-2 mb-2">{icon}<span className="text-xs text-slate-500">{label}</span></div>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
      <p className="text-xs text-slate-500 mt-1">{sub}</p>
    </div>
  );
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}
