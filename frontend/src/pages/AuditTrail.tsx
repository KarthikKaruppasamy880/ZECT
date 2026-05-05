import { useState, useEffect } from "react";
import { ScrollText, Filter, RefreshCw } from "lucide-react";

interface AuditEntry {
  id: number;
  user_id: number | null;
  action: string;
  resource_type: string;
  resource_id: number | null;
  resource_name: string;
  details: string;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

interface AuditStats {
  total_entries: number;
  actions: Record<string, number>;
  resource_types: Record<string, number>;
  recent_24h: number;
}

const API = import.meta.env.VITE_API_URL ?? "";

export default function AuditTrail() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [stats, setStats] = useState<AuditStats | null>(null);
  const [filterAction, setFilterAction] = useState("");
  const [filterResource, setFilterResource] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filterAction) params.set("action", filterAction);
      if (filterResource) params.set("resource_type", filterResource);
      const [entriesRes, statsRes] = await Promise.all([
        fetch(`${API}/api/audit?${params}`),
        fetch(`${API}/api/audit/stats`),
      ]);
      if (entriesRes.ok) setEntries(await entriesRes.json());
      if (statsRes.ok) setStats(await statsRes.json());
    } catch {
      // API not available yet
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [filterAction, filterResource]);

  const actionColor = (action: string) => {
    const colors: Record<string, string> = {
      create: "bg-green-500/20 text-green-400",
      update: "bg-blue-500/20 text-blue-400",
      delete: "bg-red-500/20 text-red-400",
      login: "bg-purple-500/20 text-purple-400",
      export: "bg-yellow-500/20 text-yellow-400",
      review: "bg-cyan-500/20 text-cyan-400",
    };
    return colors[action] || "bg-slate-500/20 text-slate-400";
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <ScrollText className="h-6 w-6 text-cyan-400" />
            Audit Trail
          </h1>
          <p className="text-sm text-slate-400 mt-1">Full history of all system operations and changes</p>
        </div>
        <button onClick={fetchData} className="flex items-center gap-2 px-3 py-2 bg-slate-800 text-slate-300 rounded-lg hover:bg-slate-700 text-sm">
          <RefreshCw className="h-4 w-4" /> Refresh
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
            <p className="text-xs text-slate-400 uppercase">Total Entries</p>
            <p className="text-2xl font-bold text-white mt-1">{stats.total_entries}</p>
          </div>
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
            <p className="text-xs text-slate-400 uppercase">Last 24h</p>
            <p className="text-2xl font-bold text-cyan-400 mt-1">{stats.recent_24h}</p>
          </div>
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
            <p className="text-xs text-slate-400 uppercase">Action Types</p>
            <p className="text-2xl font-bold text-white mt-1">{Object.keys(stats.actions).length}</p>
          </div>
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
            <p className="text-xs text-slate-400 uppercase">Resource Types</p>
            <p className="text-2xl font-bold text-white mt-1">{Object.keys(stats.resource_types).length}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-400" />
          <select
            value={filterAction}
            onChange={(e) => setFilterAction(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-slate-300 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">All Actions</option>
            <option value="create">Create</option>
            <option value="update">Update</option>
            <option value="delete">Delete</option>
            <option value="login">Login</option>
            <option value="export">Export</option>
            <option value="review">Review</option>
          </select>
        </div>
        <select
          value={filterResource}
          onChange={(e) => setFilterResource(e.target.value)}
          className="bg-slate-800 border border-slate-700 text-slate-300 rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All Resources</option>
          <option value="project">Project</option>
          <option value="repo">Repo</option>
          <option value="skill">Skill</option>
          <option value="setting">Setting</option>
          <option value="review">Review</option>
          <option value="rule">Rule</option>
        </select>
      </div>

      {/* Entries Table */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-slate-400">Loading audit trail...</div>
        ) : entries.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            <ScrollText className="h-12 w-12 mx-auto mb-3 opacity-30" />
            <p className="font-medium">No audit entries yet</p>
            <p className="text-sm mt-1">System actions will be logged here automatically</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-800">
              <tr className="text-left text-slate-400 text-xs uppercase">
                <th className="px-4 py-3">Timestamp</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Resource</th>
                <th className="px-4 py-3">Details</th>
                <th className="px-4 py-3">IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {entries.map((e) => (
                <tr key={e.id} className="hover:bg-slate-700/30">
                  <td className="px-4 py-3 text-slate-400 whitespace-nowrap">
                    {e.created_at ? new Date(e.created_at).toLocaleString() : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${actionColor(e.action)}`}>
                      {e.action}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-300">
                    {e.resource_type}{e.resource_name ? `: ${e.resource_name}` : ""}
                  </td>
                  <td className="px-4 py-3 text-slate-400 max-w-xs truncate">{e.details}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{e.ip_address || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
