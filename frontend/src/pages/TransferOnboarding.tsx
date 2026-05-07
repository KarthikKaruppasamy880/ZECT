import { useEffect, useState } from "react";
import {
  ArrowRightLeft,
  Download,
  Upload,
  UserCheck,
  Settings,
  CheckCircle,
  Brain,
  BookOpen,
} from "lucide-react";
import { showToast } from "@/components/Toast";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function TransferOnboarding() {
  const [activeTab, setActiveTab] = useState<"onboarding" | "export" | "import" | "history">("onboarding");
  const [questions, setQuestions] = useState<any[]>([]);
  const [toggles, setToggles] = useState<any[]>([]);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [onboardingStatus, setOnboardingStatus] = useState<any>(null);
  const [bundles, setBundles] = useState<any[]>([]);
  const [exportResult, setExportResult] = useState<any>(null);
  const [importData, setImportData] = useState("");
  const [importResult, setImportResult] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [projectId, setProjectId] = useState(1);
  const [userId, setUserId] = useState(1);

  const fetchQuestions = async () => {
    try {
      const res = await fetch(`${API}/api/transfer/onboarding/questions`);
      if (res.ok) {
        const data = await res.json();
        setQuestions(data.questions || []);
        setToggles(data.feature_toggles || []);
      }
    } catch (err) { showToast("error", "Failed to load onboarding questions"); }
  };

  const fetchOnboardingStatus = async () => {
    try {
      const res = await fetch(`${API}/api/transfer/onboarding/status/${userId}`);
      if (res.ok) setOnboardingStatus(await res.json());
      else showToast("error", `Failed to load onboarding status (${res.status})`);
    } catch (err) { showToast("error", "Network error loading status"); }
  };

  const fetchBundles = async () => {
    try {
      const res = await fetch(`${API}/api/transfer/bundles?limit=20`);
      if (res.ok) setBundles(await res.json());
      else showToast("error", `Failed to load bundles (${res.status})`);
    } catch (err) { showToast("error", "Network error loading bundles"); }
  };

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchQuestions(), fetchOnboardingStatus(), fetchBundles()])
      .finally(() => setLoading(false));
  }, [userId]);

  const handleAnswer = async (key: string, value: any) => {
    setAnswers({ ...answers, [key]: value });
    try {
      await fetch(`${API}/api/transfer/onboarding/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, project_id: projectId, question_key: key, answer: value }),
      });
      fetchOnboardingStatus();
    } catch (err) { showToast("error", "Failed to save answer"); }
  };

  const handleCompleteOnboarding = async () => {
    try {
      const res = await fetch(`${API}/api/transfer/onboarding/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, project_id: projectId }),
      });
      if (res.ok) {
        fetchOnboardingStatus();
        showToast("success", "Onboarding complete! Preferences saved.");
      } else {
        showToast("error", `Onboarding failed (${res.status})`);
      }
    } catch (err) { showToast("error", "Failed to complete onboarding"); }
  };

  const handleExport = async (bundleType: string) => {
    try {
      const res = await fetch(`${API}/api/transfer/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: projectId, user_id: userId, bundle_type: bundleType, include_preferences: true }),
      });
      if (res.ok) {
        const data = await res.json();
        setExportResult(data);
        showToast("success", `${bundleType} export successful`);
        fetchBundles();
      } else {
        const errData = await res.json().catch(() => ({}));
        showToast("error", errData.detail || `Export failed (${res.status})`);
      }
    } catch (err) { showToast("error", "Network error during export"); }
  };

  const handleImport = async () => {
    if (!importData.trim()) return;
    try {
      const bundleData = JSON.parse(importData);
      const res = await fetch(`${API}/api/transfer/import`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_project_id: projectId, user_id: userId, bundle_data: bundleData, merge_strategy: "skip_duplicates" }),
      });
      if (res.ok) {
        const data = await res.json();
        setImportResult(data);
        fetchBundles();
      }
    } catch (err) {
      showToast("error", "Invalid JSON bundle data");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  const tabs = [
    { key: "onboarding" as const, label: "Onboarding Wizard", icon: UserCheck },
    { key: "export" as const, label: "Export Brain", icon: Download },
    { key: "import" as const, label: "Import Brain", icon: Upload },
    { key: "history" as const, label: "Transfer History", icon: ArrowRightLeft },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <ArrowRightLeft className="h-6 w-6 text-indigo-600" /> Transfer & Onboarding
          </h1>
          <p className="text-slate-500 text-sm">Brain state export/import and user onboarding wizard</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-sm text-slate-600">User:</label>
          <input type="number" value={userId} onChange={(e) => setUserId(Number(e.target.value))} className="w-16 px-2 py-1 border rounded text-sm" />
          <label className="text-sm text-slate-600">Project:</label>
          <input type="number" value={projectId} onChange={(e) => setProjectId(Number(e.target.value))} className="w-16 px-2 py-1 border rounded text-sm" />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-slate-100 rounded-lg p-1">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === t.key ? "bg-white text-indigo-700 shadow-sm" : "text-slate-600 hover:text-slate-900"}`}>
            <t.icon className="h-4 w-4" /> {t.label}
          </button>
        ))}
      </div>

      {/* Onboarding Tab */}
      {activeTab === "onboarding" && (
        <div>
          {/* Progress */}
          {onboardingStatus && (
            <div className="bg-white rounded-xl border border-slate-200 p-4 mb-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-slate-700">Onboarding Progress</span>
                <span className="text-sm text-slate-500">{onboardingStatus.answered}/{onboardingStatus.total} questions</span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-2">
                <div className="bg-indigo-600 h-2 rounded-full" style={{ width: `${(onboardingStatus.answered / Math.max(onboardingStatus.total, 1)) * 100}%` }} />
              </div>
            </div>
          )}

          {/* Questions */}
          <div className="space-y-4 mb-6">
            {questions.map((q) => (
              <div key={q.key} className="bg-white rounded-xl border border-slate-200 p-5">
                <h3 className="text-sm font-semibold text-slate-800 mb-3">{q.question}</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                  {q.options.map((opt: any) => {
                    const selected = answers[q.key]?.value === opt.value;
                    return (
                      <button
                        key={opt.value}
                        onClick={() => handleAnswer(q.key, { value: opt.value, label: opt.label })}
                        className={`p-3 rounded-lg border text-left text-sm transition-colors ${selected ? "border-indigo-500 bg-indigo-50 text-indigo-700" : "border-slate-200 hover:border-slate-300 text-slate-600"}`}
                      >
                        <span className="font-medium">{opt.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          {/* Feature Toggles */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Feature Toggles</h3>
            <div className="space-y-3">
              {toggles.map((t) => (
                <label key={t.key} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg cursor-pointer hover:bg-slate-100">
                  <div>
                    <p className="text-sm font-medium text-slate-800">{t.label}</p>
                  </div>
                  <input
                    type="checkbox"
                    defaultChecked={t.default}
                    onChange={(e) => handleAnswer(`toggle_${t.key}`, { enabled: e.target.checked })}
                    className="h-4 w-4 text-indigo-600 rounded border-slate-300"
                  />
                </label>
              ))}
            </div>
          </div>

          <button onClick={handleCompleteOnboarding} className="w-full py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700">
            Complete Onboarding & Save Preferences
          </button>
        </div>
      )}

      {/* Export Tab */}
      {activeTab === "export" && (
        <div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
            <h3 className="text-sm font-semibold text-slate-700 mb-4">Export Brain State</h3>
            <p className="text-xs text-slate-500 mb-4">Export your project's learned knowledge, decisions, and episodes as a portable bundle. Security scan blocks any accidental secret leaks.</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <button onClick={() => handleExport("full")} className="flex flex-col items-center gap-2 p-4 border rounded-xl hover:bg-indigo-50 hover:border-indigo-300">
                <Brain className="h-8 w-8 text-indigo-600" />
                <span className="text-sm font-medium">Full Export</span>
                <span className="text-xs text-slate-400">Everything</span>
              </button>
              <button onClick={() => handleExport("memory_only")} className="flex flex-col items-center gap-2 p-4 border rounded-xl hover:bg-blue-50 hover:border-blue-300">
                <BookOpen className="h-8 w-8 text-blue-600" />
                <span className="text-sm font-medium">Memory Only</span>
                <span className="text-xs text-slate-400">Lessons + episodes</span>
              </button>
              <button onClick={() => handleExport("lessons_only")} className="flex flex-col items-center gap-2 p-4 border rounded-xl hover:bg-green-50 hover:border-green-300">
                <CheckCircle className="h-8 w-8 text-green-600" />
                <span className="text-sm font-medium">Lessons Only</span>
                <span className="text-xs text-slate-400">Graduated lessons</span>
              </button>
              <button onClick={() => handleExport("skills_only")} className="flex flex-col items-center gap-2 p-4 border rounded-xl hover:bg-purple-50 hover:border-purple-300">
                <Settings className="h-8 w-8 text-purple-600" />
                <span className="text-sm font-medium">Skills Only</span>
                <span className="text-xs text-slate-400">Skill definitions</span>
              </button>
            </div>
          </div>

          {exportResult && (
            <div className="bg-green-50 rounded-xl border border-green-200 p-5">
              <h3 className="text-sm font-semibold text-green-700 mb-2 flex items-center gap-2">
                <CheckCircle className="h-4 w-4" /> Export Successful
              </h3>
              <div className="grid grid-cols-4 gap-3 mb-3 text-xs">
                <div><span className="text-slate-500">Lessons:</span> {exportResult.counts?.lessons}</div>
                <div><span className="text-slate-500">Decisions:</span> {exportResult.counts?.decisions}</div>
                <div><span className="text-slate-500">Episodes:</span> {exportResult.counts?.episodes}</div>
                <div><span className="text-slate-500">Skills:</span> {exportResult.counts?.skills}</div>
              </div>
              <p className="text-xs text-slate-500 mb-2">Checksum: <span className="font-mono">{exportResult.checksum?.substring(0, 16)}...</span></p>
              <button
                onClick={() => {
                  const json = JSON.stringify(exportResult.bundle, null, 2);
                  const blob = new Blob([json], { type: "application/json" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `brain-state-${projectId}.json`;
                  a.click();
                  URL.revokeObjectURL(url);
                }}
                className="px-3 py-1.5 bg-green-600 text-white rounded text-xs font-medium hover:bg-green-700"
              >
                Download JSON Bundle
              </button>
            </div>
          )}
        </div>
      )}

      {/* Import Tab */}
      {activeTab === "import" && (
        <div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Import Brain State</h3>
            <p className="text-xs text-slate-500 mb-3">Paste a JSON bundle from an export to import knowledge into this project. Duplicate lessons are skipped automatically.</p>
            <textarea
              value={importData}
              onChange={(e) => setImportData(e.target.value)}
              placeholder='Paste JSON bundle here (e.g., {"version": "1.0", "lessons": [...], ...})'
              className="w-full h-40 px-3 py-2 border rounded-lg text-sm font-mono"
            />
            <button onClick={handleImport} disabled={!importData.trim()} className="mt-3 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
              Import Bundle
            </button>
          </div>

          {importResult && (
            <div className="bg-blue-50 rounded-xl border border-blue-200 p-5">
              <h3 className="text-sm font-semibold text-blue-700 mb-2 flex items-center gap-2">
                <CheckCircle className="h-4 w-4" /> Import Successful
              </h3>
              <div className="grid grid-cols-4 gap-3 text-xs">
                <div><span className="text-slate-500">Lessons:</span> {importResult.imported?.lessons}</div>
                <div><span className="text-slate-500">Decisions:</span> {importResult.imported?.decisions}</div>
                <div><span className="text-slate-500">Episodes:</span> {importResult.imported?.episodes}</div>
                <div><span className="text-slate-500">Skills:</span> {importResult.imported?.skills}</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* History Tab */}
      {activeTab === "history" && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Transfer History</h3>
          {bundles.length === 0 ? (
            <p className="text-slate-400 text-sm py-8 text-center">No transfers yet.</p>
          ) : (
            <div className="space-y-2">
              {bundles.map((b) => (
                <div key={b.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    {b.direction === "export" ? <Download className="h-4 w-4 text-green-600" /> : <Upload className="h-4 w-4 text-blue-600" />}
                    <div>
                      <p className="text-sm font-medium text-slate-800">{b.direction.toUpperCase()} — {b.bundle_type}</p>
                      <p className="text-xs text-slate-500">
                        {b.lessons_count} lessons, {b.decisions_count} decisions, {b.episodes_count} episodes, {b.skills_count} skills
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded ${b.status === "completed" ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}`}>
                      {b.status}
                    </span>
                    <p className="text-xs text-slate-400 mt-0.5">{b.created_at?.split("T")[0]}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
