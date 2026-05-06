import { useEffect, useState } from "react";
import {
  Wrench,
  Plus,
  Search,
  CheckCircle,
  XCircle,
  RefreshCw,
  Zap,
  Clock,
} from "lucide-react";
import { showToast } from "@/components/Toast";
import Pagination from "@/components/Pagination";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface Skill {
  id: number;
  name: string;
  version: string;
  description: string;
  category: string;
  trigger_pattern: string;
  manifest: Record<string, any>;
  is_seed: boolean;
  is_active: boolean;
  execution_count: number;
  last_executed_at: string | null;
  created_at: string;
}

export default function SkillsEngine() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [categories, setCategories] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"registry" | "match" | "logs" | "create">("registry");
  const [matchIntent, setMatchIntent] = useState("");
  const [matchResults, setMatchResults] = useState<any>(null);
  const [execLogs, setExecLogs] = useState<any[]>([]);
  const [filterCategory, setFilterCategory] = useState("");
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [skillsPage, setSkillsPage] = useState(1);
  const skillsPerPage = 10;

  // New skill form
  const [newSkill, setNewSkill] = useState({
    name: "", description: "", category: "general", trigger_pattern: "", version: "1.0.0",
  });

  const fetchSkills = async () => {
    try {
      const params = new URLSearchParams();
      if (filterCategory) params.set("category", filterCategory);
      const res = await fetch(`${API}/api/skills-engine/skills?${params}`);
      if (res.ok) setSkills(await res.json());
      else showToast("error", `Failed to load skills (${res.status})`);
    } catch (err) { showToast("error", "Network error loading skills"); }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API}/api/skills-engine/stats`);
      if (res.ok) setStats(await res.json());
      else showToast("error", `Failed to load stats (${res.status})`);
    } catch (err) { showToast("error", "Network error loading stats"); }
  };

  const fetchCategories = async () => {
    try {
      const res = await fetch(`${API}/api/skills-engine/categories`);
      if (res.ok) setCategories(await res.json());
      else showToast("error", `Failed to load categories (${res.status})`);
    } catch (err) { showToast("error", "Network error loading categories"); }
  };

  const fetchLogs = async () => {
    try {
      const res = await fetch(`${API}/api/skills-engine/executions?limit=50`);
      if (res.ok) setExecLogs(await res.json());
      else showToast("error", `Failed to load logs (${res.status})`);
    } catch (err) { showToast("error", "Network error loading logs"); }
  };

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchSkills(), fetchStats(), fetchCategories(), fetchLogs()])
      .finally(() => setLoading(false));
  }, [filterCategory]);

  const handleMatch = async () => {
    if (!matchIntent.trim()) return;
    try {
      const res = await fetch(`${API}/api/skills-engine/match`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ intent: matchIntent }),
      });
      if (res.ok) setMatchResults(await res.json());
      else showToast("error", `Match failed (${res.status})`);
    } catch (err) { showToast("error", "Network error during match"); }
  };

  const handleCreateSkill = async () => {
    if (!newSkill.name.trim()) return;
    try {
      const res = await fetch(`${API}/api/skills-engine/skills`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newSkill),
      });
      if (res.ok) {
        setNewSkill({ name: "", description: "", category: "general", trigger_pattern: "", version: "1.0.0" });
        setActiveTab("registry");
        fetchSkills();
        fetchStats();
        showToast("success", "Skill created successfully");
        fetchCategories();
      } else {
        showToast("error", `Failed to create skill (${res.status})`);
      }
    } catch (err) { showToast("error", "Network error creating skill"); }
  };

  const handleDeactivate = async (skillId: number) => {
    try {
      await fetch(`${API}/api/skills-engine/skills/${skillId}`, { method: "DELETE" });
      showToast("info", "Skill deactivated");
      fetchSkills();
      fetchStats();
    } catch (err) { showToast("error", "Failed to deactivate skill"); }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600" />
      </div>
    );
  }

  const tabs = [
    { key: "registry" as const, label: "Skill Registry", icon: Wrench },
    { key: "match" as const, label: "Trigger Match", icon: Search },
    { key: "logs" as const, label: "Execution Logs", icon: Clock },
    { key: "create" as const, label: "Create Skill", icon: Plus },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Wrench className="h-6 w-6 text-emerald-600" /> Skills Engine
          </h1>
          <p className="text-slate-500 text-sm">Skill registry, trigger-based matching, and execution tracking</p>
        </div>
        <button onClick={() => { fetchSkills(); fetchStats(); fetchCategories(); fetchLogs(); }} className="p-2 rounded hover:bg-slate-100">
          <RefreshCw className="h-4 w-4 text-slate-500" />
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
          <MiniStat label="Total Skills" value={stats.total_skills} />
          <MiniStat label="Seed Skills" value={stats.seed_skills} />
          <MiniStat label="Custom Skills" value={stats.custom_skills} />
          <MiniStat label="Categories" value={stats.categories} />
          <MiniStat label="Executions" value={stats.total_executions} />
          <MiniStat label="Successful" value={stats.successful_executions} />
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-slate-100 rounded-lg p-1">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === t.key ? "bg-white text-emerald-700 shadow-sm" : "text-slate-600 hover:text-slate-900"}`}>
            <t.icon className="h-4 w-4" /> {t.label}
          </button>
        ))}
      </div>

      {/* Registry Tab */}
      {activeTab === "registry" && (
        <div>
          {/* Category filter */}
          <div className="flex gap-2 mb-4 flex-wrap">
            <button onClick={() => setFilterCategory("")} className={`text-xs px-3 py-1.5 rounded-full font-medium ${!filterCategory ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}>
              All
            </button>
            {categories.map((c) => (
              <button key={c.category} onClick={() => setFilterCategory(c.category)}
                className={`text-xs px-3 py-1.5 rounded-full font-medium ${filterCategory === c.category ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}>
                {c.category} ({c.count})
              </button>
            ))}
          </div>

          <>
          <div className="space-y-3">
            {skills.slice((skillsPage - 1) * skillsPerPage, skillsPage * skillsPerPage).map((s) => (
              <div key={s.id} className="bg-white rounded-xl border border-slate-200 p-4 hover:border-emerald-300 transition-colors cursor-pointer" onClick={() => setSelectedSkill(selectedSkill?.id === s.id ? null : s)}>
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-sm font-semibold text-slate-800">{s.name}</h3>
                      <span className="text-xs text-slate-400">v{s.version}</span>
                      {s.is_seed && <span className="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">seed</span>}
                      <span className="text-xs px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded">{s.category}</span>
                    </div>
                    <p className="text-xs text-slate-500">{s.description}</p>
                    {s.trigger_pattern && (
                      <div className="flex items-center gap-1 mt-1">
                        <Zap className="h-3 w-3 text-amber-500" />
                        <span className="text-xs text-amber-600 font-mono">{s.trigger_pattern}</span>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 ml-3">
                    <span className="text-xs text-slate-400">{s.execution_count} runs</span>
                    <button onClick={(e) => { e.stopPropagation(); handleDeactivate(s.id); }} className="p-1 rounded hover:bg-red-100 text-slate-400 hover:text-red-600" title="Deactivate">
                      <XCircle className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {/* Expanded manifest */}
                {selectedSkill?.id === s.id && s.manifest && (
                  <div className="mt-3 pt-3 border-t border-slate-100">
                    <p className="text-xs font-semibold text-slate-600 mb-2">Manifest</p>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                      {s.manifest.inputs && (
                        <div>
                          <p className="font-medium text-slate-500 mb-1">Inputs</p>
                          {s.manifest.inputs.map((inp: string) => <p key={inp} className="text-slate-600">- {inp}</p>)}
                        </div>
                      )}
                      {s.manifest.outputs && (
                        <div>
                          <p className="font-medium text-slate-500 mb-1">Outputs</p>
                          {s.manifest.outputs.map((out: string) => <p key={out} className="text-slate-600">- {out}</p>)}
                        </div>
                      )}
                      {s.manifest.config && (
                        <div>
                          <p className="font-medium text-slate-500 mb-1">Config</p>
                          {Object.entries(s.manifest.config).map(([k, v]) => (
                            <p key={k} className="text-slate-600">{k}: {String(v)}</p>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
          <Pagination currentPage={skillsPage} totalItems={skills.length} pageSize={skillsPerPage} onPageChange={setSkillsPage} />
          </>
        </div>
      )}

      {/* Match Tab */}
      {activeTab === "match" && (
        <div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Trigger Match — Find Skills by Intent</h3>
            <div className="flex gap-2">
              <input value={matchIntent} onChange={(e) => setMatchIntent(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleMatch()}
                placeholder="Describe what you want to do (e.g., 'debug a failing test', 'deploy to production')"
                className="flex-1 px-3 py-2 border rounded-lg text-sm" />
              <button onClick={handleMatch} className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700">
                Match
              </button>
            </div>
          </div>

          {matchResults && (
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">
                {matchResults.total_matches} skill(s) matched for "{matchResults.intent}"
              </h3>
              {matchResults.matches.length === 0 ? (
                <p className="text-slate-400 text-sm">No skills match this intent. Create a new skill to handle it.</p>
              ) : (
                <div className="space-y-2">
                  {matchResults.matches.map((m: any, i: number) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                      <div className="flex items-center gap-3 flex-1">
                        <span className={`text-lg font-bold ${i === 0 ? "text-emerald-600" : "text-slate-400"}`}>#{i + 1}</span>
                        <div>
                          <p className="text-sm font-medium text-slate-800">{m.skill.name}</p>
                          <p className="text-xs text-slate-500">{m.skill.description}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold text-emerald-600">Score: {m.score}</p>
                        <p className="text-xs text-slate-400 font-mono">{m.trigger_pattern}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Logs Tab */}
      {activeTab === "logs" && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Execution Logs</h3>
          {execLogs.length === 0 ? (
            <p className="text-slate-400 text-sm py-8 text-center">No executions logged yet. Skills will log executions as they run.</p>
          ) : (
            <div className="space-y-2">
              {execLogs.map((l) => (
                <div key={l.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    {l.success ? <CheckCircle className="h-4 w-4 text-green-500" /> : <XCircle className="h-4 w-4 text-red-500" />}
                    <div>
                      <p className="text-sm font-medium text-slate-800">{l.skill_name}</p>
                      {l.error_message && <p className="text-xs text-red-500">{l.error_message}</p>}
                    </div>
                  </div>
                  <div className="text-right text-xs text-slate-400">
                    <p>{l.duration_seconds}s</p>
                    <p>{l.created_at?.split("T")[0]}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Create Tab */}
      {activeTab === "create" && (
        <div className="bg-white rounded-xl border border-emerald-200 p-5">
          <h3 className="text-sm font-semibold text-emerald-700 mb-4">Create New Skill</h3>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <input value={newSkill.name} onChange={(e) => setNewSkill({ ...newSkill, name: e.target.value })} placeholder="Skill name (e.g., zinnia-test-runner)" className="px-3 py-2 border rounded-lg text-sm" />
              <input value={newSkill.version} onChange={(e) => setNewSkill({ ...newSkill, version: e.target.value })} placeholder="Version" className="px-3 py-2 border rounded-lg text-sm" />
            </div>
            <textarea value={newSkill.description} onChange={(e) => setNewSkill({ ...newSkill, description: e.target.value })} placeholder="Description" className="w-full px-3 py-2 border rounded-lg text-sm h-20" />
            <div className="grid grid-cols-2 gap-3">
              <select value={newSkill.category} onChange={(e) => setNewSkill({ ...newSkill, category: e.target.value })} className="px-3 py-2 border rounded-lg text-sm">
                <option value="general">General</option>
                <option value="quality">Quality</option>
                <option value="debugging">Debugging</option>
                <option value="deployment">Deployment</option>
                <option value="git">Git</option>
                <option value="memory">Memory</option>
                <option value="meta">Meta</option>
                <option value="architecture">Architecture</option>
                <option value="migration">Migration</option>
                <option value="testing">Testing</option>
              </select>
              <input value={newSkill.trigger_pattern} onChange={(e) => setNewSkill({ ...newSkill, trigger_pattern: e.target.value })} placeholder="Trigger patterns (pipe-separated)" className="px-3 py-2 border rounded-lg text-sm" />
            </div>
            <button onClick={handleCreateSkill} disabled={!newSkill.name.trim()} className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50">
              Register Skill
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-3 text-center">
      <p className="text-lg font-bold text-slate-900">{value}</p>
      <p className="text-xs text-slate-500">{label}</p>
    </div>
  );
}
