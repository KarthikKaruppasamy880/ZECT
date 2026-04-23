import { useEffect, useState } from "react";
import { getSettings, updateSetting } from "@/lib/api";
import type { Setting } from "@/types";
import { Settings as SettingsIcon, ToggleLeft, ToggleRight, ChevronDown } from "lucide-react";

export default function Settings() {
  const [settings, setSettings] = useState<Setting[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSettings()
      .then(setSettings)
      .finally(() => setLoading(false));
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
    </div>
  );
}
