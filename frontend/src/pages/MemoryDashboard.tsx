import { useEffect, useState } from "react";
import {
  Brain,
  Layers,
  BookOpen,
  CheckCircle,
  XCircle,
  Clock,
  Search,
  Plus,
  RefreshCw,
  Lightbulb,
  FileText,
  AlertTriangle,
} from "lucide-react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface BrainState {
  project_id: number;
  summary: {
    working_tasks: number;
    episodes_total: number;
    episodes_active: number;
    lessons_staged: number;
    lessons_accepted: number;
    lessons_rejected: number;
    decisions_active: number;
  };
  recent_episodes: any[];
  pending_review: any[];
}

export default function MemoryDashboard() {
  const [projectId, setProjectId] = useState(1);
  const [brainState, setBrainState] = useState<BrainState | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "episodes" | "lessons" | "decisions" | "search">("overview");
  const [episodes, setEpisodes] = useState<any[]>([]);
  const [lessons, setLessons] = useState<any[]>([]);
  const [decisions, setDecisions] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [learnClaim, setLearnClaim] = useState("");
  const [learnConditions, setLearnConditions] = useState("");

  const fetchBrainState = async () => {
    try {
      const res = await fetch(`${API}/api/memory/brain-state/${projectId}`);
      if (res.ok) setBrainState(await res.json());
    } catch { /* ignore */ }
  };

  const fetchEpisodes = async () => {
    try {
      const res = await fetch(`${API}/api/memory/episodic/${projectId}?limit=50`);
      if (res.ok) setEpisodes(await res.json());
    } catch { /* ignore */ }
  };

  const fetchLessons = async () => {
    try {
      const res = await fetch(`${API}/api/memory/lessons/${projectId}`);
      if (res.ok) setLessons(await res.json());
    } catch { /* ignore */ }
  };

  const fetchDecisions = async () => {
    try {
      const res = await fetch(`${API}/api/memory/decisions/${projectId}`);
      if (res.ok) setDecisions(await res.json());
    } catch { /* ignore */ }
  };

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchBrainState(), fetchEpisodes(), fetchLessons(), fetchDecisions()])
      .finally(() => setLoading(false));
  }, [projectId]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    try {
      const res = await fetch(`${API}/api/memory/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: searchQuery, project_id: projectId }),
      });
      if (res.ok) setSearchResults(await res.json());
    } catch { /* ignore */ }
  };

  const handleLearn = async () => {
    if (!learnClaim.trim()) return;
    try {
      await fetch(`${API}/api/memory/learn`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: projectId,
          claim: learnClaim,
          conditions: learnConditions ? learnConditions.split(",").map((s) => s.trim()) : [],
          rationale: "Manually taught via Memory Dashboard",
          reviewer: "user",
        }),
      });
      setLearnClaim("");
      setLearnConditions("");
      fetchLessons();
      fetchBrainState();
    } catch { /* ignore */ }
  };

  const handleGraduate = async (lessonId: number) => {
    try {
      await fetch(`${API}/api/memory/lessons/${lessonId}/graduate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rationale: "Graduated via dashboard", reviewer: "user" }),
      });
      fetchLessons();
      fetchBrainState();
    } catch { /* ignore */ }
  };

  const handleReject = async (lessonId: number) => {
    try {
      await fetch(`${API}/api/memory/lessons/${lessonId}/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: "Rejected via dashboard", reviewer: "user" }),
      });
      fetchLessons();
      fetchBrainState();
    } catch { /* ignore */ }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  const tabs = [
    { key: "overview" as const, label: "Brain State", icon: Brain },
    { key: "episodes" as const, label: "Episodes", icon: Clock },
    { key: "lessons" as const, label: "Lessons", icon: BookOpen },
    { key: "decisions" as const, label: "Decisions", icon: Lightbulb },
    { key: "search" as const, label: "Search", icon: Search },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Zinnia Memory System</h1>
          <p className="text-slate-500 text-sm">4-layer memory: working, episodic, semantic, personal</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-sm text-slate-600">Project ID:</label>
          <input
            type="number"
            value={projectId}
            onChange={(e) => setProjectId(Number(e.target.value))}
            className="w-20 px-2 py-1 border rounded text-sm"
          />
          <button onClick={() => { fetchBrainState(); fetchEpisodes(); fetchLessons(); fetchDecisions(); }} className="p-2 rounded hover:bg-slate-100">
            <RefreshCw className="h-4 w-4 text-slate-500" />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-slate-100 rounded-lg p-1">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === t.key ? "bg-white text-indigo-700 shadow-sm" : "text-slate-600 hover:text-slate-900"}`}
          >
            <t.icon className="h-4 w-4" />
            {t.label}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === "overview" && brainState && (
        <div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <StatCard label="Active Tasks" value={brainState.summary.working_tasks} icon={Layers} color="bg-blue-500" />
            <StatCard label="Episodes (Active)" value={brainState.summary.episodes_active} icon={Clock} color="bg-green-500" />
            <StatCard label="Lessons Accepted" value={brainState.summary.lessons_accepted} icon={CheckCircle} color="bg-indigo-500" />
            <StatCard label="Pending Review" value={brainState.summary.lessons_staged} icon={AlertTriangle} color="bg-amber-500" />
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            <StatCard label="Total Episodes" value={brainState.summary.episodes_total} icon={FileText} color="bg-cyan-500" />
            <StatCard label="Lessons Rejected" value={brainState.summary.lessons_rejected} icon={XCircle} color="bg-red-500" />
            <StatCard label="Active Decisions" value={brainState.summary.decisions_active} icon={Lightbulb} color="bg-purple-500" />
          </div>

          {/* Recent Episodes */}
          {brainState.recent_episodes.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Recent Episodes</h3>
              <div className="space-y-2">
                {brainState.recent_episodes.map((ep: any) => (
                  <div key={ep.id} className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg">
                    <span className={`mt-1 h-2 w-2 rounded-full flex-shrink-0 ${ep.success ? "bg-green-500" : "bg-red-500"}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-800 truncate">{ep.action}</p>
                      <p className="text-xs text-slate-500 truncate">{ep.outcome}</p>
                    </div>
                    <span className="text-xs text-slate-400">{ep.harness}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Pending Review */}
          {brainState.pending_review.length > 0 && (
            <div className="bg-white rounded-xl border border-amber-200 p-5">
              <h3 className="text-sm font-semibold text-amber-700 mb-3">Pending Review Queue</h3>
              <div className="space-y-2">
                {brainState.pending_review.map((l: any) => (
                  <div key={l.id} className="flex items-center justify-between p-3 bg-amber-50 rounded-lg">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-800 truncate">{l.claim}</p>
                      <p className="text-xs text-slate-500">Confidence: {(l.confidence * 100).toFixed(0)}% | Evidence: {l.evidence_count}</p>
                    </div>
                    <div className="flex gap-2 ml-3">
                      <button onClick={() => handleGraduate(l.id)} className="p-1.5 rounded bg-green-100 hover:bg-green-200 text-green-700" title="Graduate">
                        <CheckCircle className="h-4 w-4" />
                      </button>
                      <button onClick={() => handleReject(l.id)} className="p-1.5 rounded bg-red-100 hover:bg-red-200 text-red-700" title="Reject">
                        <XCircle className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Episodes Tab */}
      {activeTab === "episodes" && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Episodic Memory — Raw Experience Log</h3>
          {episodes.length === 0 ? (
            <p className="text-slate-400 text-sm py-8 text-center">No episodes recorded yet. Actions will appear here as ZECT logs them.</p>
          ) : (
            <div className="space-y-2">
              {episodes.map((ep) => (
                <div key={ep.id} className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors">
                  <span className={`mt-1.5 h-2 w-2 rounded-full flex-shrink-0 ${ep.success ? "bg-green-500" : "bg-red-500"}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-slate-800">{ep.action}</p>
                      <span className="text-xs px-1.5 py-0.5 rounded bg-slate-200 text-slate-600">{ep.harness}</span>
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5">{ep.outcome}</p>
                    {ep.reflection && <p className="text-xs text-indigo-500 mt-1 italic">{ep.reflection}</p>}
                    <div className="flex gap-3 mt-1 text-xs text-slate-400">
                      <span>Importance: {ep.importance}/10</span>
                      <span>Salience: {(ep.salience * 100).toFixed(0)}%</span>
                      <span>Pain: {ep.pain_score}/5</span>
                      {ep.tokens_in > 0 && <span>Tokens: {ep.tokens_in + ep.tokens_out}</span>}
                    </div>
                  </div>
                  <span className="text-xs text-slate-400 whitespace-nowrap">{ep.created_at?.split("T")[0]}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Lessons Tab */}
      {activeTab === "lessons" && (
        <div>
          {/* Quick Learn */}
          <div className="bg-white rounded-xl border border-indigo-200 p-5 mb-6">
            <h3 className="text-sm font-semibold text-indigo-700 mb-3 flex items-center gap-2">
              <Plus className="h-4 w-4" /> Teach a Lesson (One-Shot Learn)
            </h3>
            <div className="space-y-3">
              <input
                value={learnClaim}
                onChange={(e) => setLearnClaim(e.target.value)}
                placeholder="What should ZECT learn? (e.g., 'Always run tests before pushing')"
                className="w-full px-3 py-2 border rounded-lg text-sm"
              />
              <input
                value={learnConditions}
                onChange={(e) => setLearnConditions(e.target.value)}
                placeholder="Conditions (comma-separated, e.g., 'TypeScript projects, CI pipeline')"
                className="w-full px-3 py-2 border rounded-lg text-sm"
              />
              <button onClick={handleLearn} disabled={!learnClaim.trim()} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
                Teach Lesson
              </button>
            </div>
          </div>

          {/* Lessons List */}
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">All Lessons</h3>
            {lessons.length === 0 ? (
              <p className="text-slate-400 text-sm py-8 text-center">No lessons yet. Teach one above or run a Dream Cycle to extract patterns.</p>
            ) : (
              <div className="space-y-2">
                {lessons.map((l) => (
                  <div key={l.id} className={`p-3 rounded-lg border ${l.status === "accepted" ? "bg-green-50 border-green-200" : l.status === "rejected" ? "bg-red-50 border-red-200" : l.status === "provisional" ? "bg-yellow-50 border-yellow-200" : "bg-slate-50 border-slate-200"}`}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-800">{l.claim}</p>
                        {l.conditions?.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1">
                            {l.conditions.map((c: string, i: number) => (
                              <span key={i} className="text-xs px-1.5 py-0.5 bg-slate-200 rounded text-slate-600">{c}</span>
                            ))}
                          </div>
                        )}
                        <div className="flex gap-3 mt-1 text-xs text-slate-400">
                          <span className={`font-medium ${l.status === "accepted" ? "text-green-600" : l.status === "rejected" ? "text-red-600" : l.status === "staged" ? "text-amber-600" : "text-slate-600"}`}>
                            {l.status}
                          </span>
                          <span>Confidence: {(l.confidence * 100).toFixed(0)}%</span>
                          <span>Evidence: {l.evidence_count}</span>
                        </div>
                      </div>
                      {l.status === "staged" && (
                        <div className="flex gap-1">
                          <button onClick={() => handleGraduate(l.id)} className="p-1.5 rounded bg-green-100 hover:bg-green-200 text-green-700">
                            <CheckCircle className="h-4 w-4" />
                          </button>
                          <button onClick={() => handleReject(l.id)} className="p-1.5 rounded bg-red-100 hover:bg-red-200 text-red-700">
                            <XCircle className="h-4 w-4" />
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Decisions Tab */}
      {activeTab === "decisions" && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Architectural Decisions</h3>
          {decisions.length === 0 ? (
            <p className="text-slate-400 text-sm py-8 text-center">No decisions recorded yet.</p>
          ) : (
            <div className="space-y-3">
              {decisions.map((d) => (
                <div key={d.id} className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                  <h4 className="text-sm font-semibold text-slate-800">{d.title}</h4>
                  <p className="text-sm text-slate-600 mt-1">{d.decision}</p>
                  {d.rationale && <p className="text-xs text-indigo-600 mt-2">Rationale: {d.rationale}</p>}
                  {d.alternatives && <p className="text-xs text-slate-400 mt-1">Alternatives: {d.alternatives}</p>}
                  <div className="flex gap-3 mt-2 text-xs text-slate-400">
                    <span className={`font-medium ${d.status === "active" ? "text-green-600" : "text-slate-500"}`}>{d.status}</span>
                    <span>{d.created_at?.split("T")[0]}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Search Tab */}
      {activeTab === "search" && (
        <div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Search Memory</h3>
            <div className="flex gap-2">
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="Search across all memory layers..."
                className="flex-1 px-3 py-2 border rounded-lg text-sm"
              />
              <button onClick={handleSearch} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700">
                Search
              </button>
            </div>
          </div>

          {searchResults.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Results ({searchResults.length})</h3>
              <div className="space-y-2">
                {searchResults.map((r, i) => (
                  <div key={i} className="p-3 bg-slate-50 rounded-lg">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded ${r.layer === "episodic" ? "bg-blue-100 text-blue-700" : r.layer === "semantic" ? "bg-green-100 text-green-700" : "bg-purple-100 text-purple-700"}`}>
                      {r.layer}
                    </span>
                    <p className="text-sm text-slate-700 mt-1">
                      {r.data.claim || r.data.action || r.data.task_name || "—"}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, icon: Icon, color }: { label: string; value: number; icon: React.ElementType; color: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 flex items-start gap-3">
      <div className={`rounded-lg p-2 ${color}`}>
        <Icon className="h-4 w-4 text-white" />
      </div>
      <div>
        <p className="text-xl font-bold text-slate-900">{value}</p>
        <p className="text-xs text-slate-500">{label}</p>
      </div>
    </div>
  );
}
