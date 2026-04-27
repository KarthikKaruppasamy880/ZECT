import { useEffect, useState } from "react";
import { getSettings, updateSetting, configureApiKey, getApiKeyStatus, getTokenUsage } from "@/lib/api";
import type { Setting, ApiKeyStatus, TokenUsage } from "@/types";
import {
  Settings as SettingsIcon,
  ToggleLeft,
  ToggleRight,
  ChevronDown,
  Key,
  Activity,
  X,
  Check,
  AlertCircle,
  Loader2,
} from "lucide-react";

export default function Settings() {
  const [settings, setSettings] = useState<Setting[]>([]);
  const [loading, setLoading] = useState(true);

  // API Key Modal
  const [showApiModal, setShowApiModal] = useState(false);
  const [apiToken, setApiToken] = useState("");
  const [apiStatus, setApiStatus] = useState<ApiKeyStatus | null>(null);
  const [apiLoading, setApiLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // Token Counter Modal
  const [showTokenModal, setShowTokenModal] = useState(false);
  const [tokenUsage, setTokenUsage] = useState<TokenUsage | null>(null);
  const [tokenLoading, setTokenLoading] = useState(false);

  useEffect(() => {
    getSettings()
      .then(setSettings)
      .finally(() => setLoading(false));
    getApiKeyStatus()
      .then(setApiStatus)
      .catch(() => {});
  }, []);

  const handleToggle = async (s: Setting) => {
    const newVal = s.value === "true" ? "false" : "true";
    const updated = await updateSetting(s.key, newVal);
    setSettings((prev) => prev.map((x) => (x.key === updated.key ? updated : x)));
  };

  const handleSelect = async (s: Setting, value: string) => {
    const updated = await updateSetting(s.key, value);
    setSettings((prev) => prev.map((x) => (x.key === updated.key ? updated : x)));
  };

  const handleConfigureApiKey = async () => {
    if (!apiToken.trim()) {
      setApiError("Please enter a GitHub token.");
      return;
    }
    setApiLoading(true);
    setApiError(null);
    try {
      const status = await configureApiKey(apiToken.trim());
      setApiStatus(status);
      setApiToken("");
      setShowApiModal(false);
    } catch (e) {
      setApiError(e instanceof Error ? e.message : "Failed to configure API key.");
    } finally {
      setApiLoading(false);
    }
  };

  const handleOpenTokenModal = async () => {
    setShowTokenModal(true);
    setTokenLoading(true);
    try {
      const usage = await getTokenUsage();
      setTokenUsage(usage);
    } catch {
      setTokenUsage(null);
    } finally {
      setTokenLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-800" />
      </div>
    );
  }

  const toggles = settings.filter((s) => s.setting_type === "toggle");
  const selects = settings.filter((s) => s.setting_type === "select");

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
        <p className="text-slate-500 text-sm">Configure ZECT behavior and integrations</p>
      </div>

      {/* API Key & Token Counter Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {/* API Key Card */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-blue-50 rounded-lg">
              <Key size={18} className="text-blue-600" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-900">GitHub API Key</h3>
              <p className="text-xs text-slate-500">Configure your personal access token</p>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <div>
              {apiStatus?.configured ? (
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-green-500 rounded-full" />
                  <span className="text-sm text-green-700">Configured</span>
                  <span className="text-xs text-slate-400">
                    ({apiStatus.rate_limit_remaining}/{apiStatus.rate_limit_total} remaining)
                  </span>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-amber-500 rounded-full" />
                  <span className="text-sm text-amber-700">Not configured</span>
                </div>
              )}
            </div>
            <button
              onClick={() => setShowApiModal(true)}
              className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700"
            >
              {apiStatus?.configured ? "Update" : "Configure"}
            </button>
          </div>
        </div>

        {/* Token Counter Card */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-purple-50 rounded-lg">
              <Activity size={18} className="text-purple-600" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Token Usage</h3>
              <p className="text-xs text-slate-500">Track analysis token consumption</p>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-600">View usage log</span>
            <button
              onClick={handleOpenTokenModal}
              className="px-3 py-1.5 bg-purple-600 text-white rounded-lg text-xs font-medium hover:bg-purple-700"
            >
              View Log
            </button>
          </div>
        </div>
      </div>

      {/* Feature Toggles */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <div className="flex items-center gap-2 mb-5">
          <SettingsIcon className="h-5 w-5 text-slate-400" />
          <h2 className="text-sm font-semibold text-slate-700">Feature Toggles</h2>
        </div>
        <div className="divide-y divide-slate-100">
          {toggles.map((s) => (
            <div key={s.key} className="flex items-center justify-between py-4">
              <div>
                <p className="text-sm font-medium text-slate-900">{s.label}</p>
                <p className="text-xs text-slate-500 mt-0.5">{s.description}</p>
              </div>
              <button
                onClick={() => handleToggle(s)}
                className="shrink-0 ml-4"
                aria-label={`Toggle ${s.label}`}
              >
                {s.value === "true" ? (
                  <ToggleRight className="h-7 w-7 text-indigo-600" />
                ) : (
                  <ToggleLeft className="h-7 w-7 text-slate-300" />
                )}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Configuration Options */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <div className="flex items-center gap-2 mb-5">
          <ChevronDown className="h-5 w-5 text-slate-400" />
          <h2 className="text-sm font-semibold text-slate-700">Configuration Options</h2>
        </div>
        <div className="divide-y divide-slate-100">
          {selects.map((s) => {
            const options: string[] = s.options ? JSON.parse(s.options) : [];
            return (
              <div key={s.key} className="flex items-center justify-between py-4">
                <div>
                  <p className="text-sm font-medium text-slate-900">{s.label}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{s.description}</p>
                </div>
                <select
                  value={s.value}
                  onChange={(e) => handleSelect(s, e.target.value)}
                  className="ml-4 shrink-0 border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-700 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                >
                  {options.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>
            );
          })}
        </div>
      </div>

      {/* API Key Modal */}
      {showApiModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between p-5 border-b border-slate-200">
              <h3 className="text-lg font-semibold text-slate-900">Configure GitHub API Key</h3>
              <button onClick={() => setShowApiModal(false)} className="p-1 hover:bg-slate-100 rounded-lg">
                <X size={18} className="text-slate-400" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Personal Access Token
                </label>
                <input
                  type="password"
                  value={apiToken}
                  onChange={(e) => setApiToken(e.target.value)}
                  placeholder="ghp_xxxxxxxxxxxx"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="text-xs text-slate-400 mt-1">
                  Create a token at GitHub Settings &rarr; Developer settings &rarr; Personal access tokens.
                  Scopes needed: repo (read).
                </p>
              </div>
              {apiError && (
                <div className="flex items-center gap-2 text-sm text-red-600">
                  <AlertCircle size={14} />
                  {apiError}
                </div>
              )}
              {apiStatus?.configured && (
                <div className="bg-green-50 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-sm text-green-700">
                    <Check size={14} />
                    Currently configured — {apiStatus.rate_limit_remaining}/{apiStatus.rate_limit_total} requests remaining
                  </div>
                  {apiStatus.scopes.length > 0 && (
                    <p className="text-xs text-green-600 mt-1">
                      Scopes: {apiStatus.scopes.join(", ")}
                    </p>
                  )}
                </div>
              )}
            </div>
            <div className="flex justify-end gap-3 p-5 border-t border-slate-200">
              <button
                onClick={() => setShowApiModal(false)}
                className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleConfigureApiKey}
                disabled={apiLoading}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
              >
                {apiLoading && <Loader2 size={14} className="animate-spin" />}
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Token Usage Modal */}
      {showTokenModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4">
            <div className="flex items-center justify-between p-5 border-b border-slate-200">
              <h3 className="text-lg font-semibold text-slate-900">Token Usage Log</h3>
              <button onClick={() => setShowTokenModal(false)} className="p-1 hover:bg-slate-100 rounded-lg">
                <X size={18} className="text-slate-400" />
              </button>
            </div>
            <div className="p-5">
              {tokenLoading ? (
                <div className="flex items-center justify-center h-32">
                  <Loader2 size={24} className="animate-spin text-slate-400" />
                </div>
              ) : tokenUsage ? (
                <div className="space-y-4">
                  <div className="bg-purple-50 rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold text-purple-700">
                      {tokenUsage.total_tokens.toLocaleString()}
                    </p>
                    <p className="text-xs text-purple-500">Total tokens consumed</p>
                  </div>
                  {tokenUsage.log.length > 0 ? (
                    <div className="max-h-64 overflow-y-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-left text-xs text-slate-500 border-b border-slate-200">
                            <th className="pb-2 font-medium">Action</th>
                            <th className="pb-2 font-medium text-right">Tokens</th>
                            <th className="pb-2 font-medium text-right">Time</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {tokenUsage.log.map((entry, i) => (
                            <tr key={i}>
                              <td className="py-2 text-slate-700">{entry.action}</td>
                              <td className="py-2 text-right text-slate-600">
                                {entry.tokens.toLocaleString()}
                              </td>
                              <td className="py-2 text-right text-slate-400 text-xs">
                                {new Date(entry.ts * 1000).toLocaleTimeString()}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-sm text-slate-500 text-center py-4">
                      No usage recorded yet. Run a repo analysis or blueprint generation to see token usage.
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-slate-500 text-center py-4">
                  Unable to load token usage data.
                </p>
              )}
            </div>
            <div className="flex justify-end p-5 border-t border-slate-200">
              <button
                onClick={() => setShowTokenModal(false)}
                className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
