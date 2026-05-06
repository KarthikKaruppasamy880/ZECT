import { useState, useEffect } from "react";
import { ScrollText, Filter, RefreshCw, Info } from "lucide-react";

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
  const [showGuide, setShowGuide] = useState(false);

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
      create: "bg-green-100 text-green-700",
      update: "bg-blue-100 text-blue-700",
      delete: "bg-red-100 text-red-700",
      login: "bg-purple-100 text-purple-700",
      export: "bg-amber-100 text-amber-700",
      review: "bg-cyan-100 text-cyan-700",
    };
    return colors[action] || "bg-slate-100 text-slate-600";
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-cyan-100 rounded-xl">
            <ScrollText className="h-6 w-6 text-cyan-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Audit Trail</h1>
            <p className="text-sm text-slate-500">Full history of all system operations and changes</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowGuide(!showGuide)} className="flex items-center gap-1.5 px-3 py-2 bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200 text-sm">
            <Info className="h-4 w-4" /> Guide
          </button>
          <button onClick={fetchData} className="flex items-center gap-1.5 px-3 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 text-sm font-medium">
            <RefreshCw className="h-4 w-4" /> Refresh
          </button>
        </div>
      </div>

      {/* Usage Guide */}
      {showGuide && (
        <div className="bg-cyan-50 border border-cyan-200 rounded-xl p-5 space-y-2">
          <h3 className="font-semibold text-cyan-900">How to use Audit Trail</h3>
          <ul className="text-sm text-cyan-800 space-y-1 list-disc list-inside">
            <li><strong>Automatic logging</strong> — Every create, update, delete, login, export, and review is recorded automatically.</li>
            <li><strong>Filter by action</strong> — Use the Action dropdown to see only specific operations (e.g., all deletes).</li>
            <li><strong>Filter by resource</strong> — Use the Resource dropdown to see changes to specific entity types (projects, skills, etc.).</li>
            <li><strong>Track users</strong> — When SSO is configured, each entry shows which user performed the action.</li>
            <li><strong>IP tracking</strong> — IP addresses are logged for security and compliance auditing.</li>
            <li><strong>Export for compliance</strong> — Use Export/Share to download audit logs for compliance reports.</li>
          </ul>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <p className="text-xs text-slate-500 uppercase font-medium">Total Entries</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">{stats?.total_entries ?? 0}</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <p className="text-xs text-slate-500 uppercase font-medium">Last 24h</p>
          <p className="text-2xl font-bold text-cyan-600 mt-1">{stats?.recent_24h ?? 0}</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <p className="text-xs text-slate-500 uppercase font-medium">Action Types</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">{stats ? Object.keys(stats.actions).length : 0}</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <p className="text-xs text-slate-500 uppercase font-medium">Resource Types</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">{stats ? Object.keys(stats.resource_types).length : 0}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-400" />
          <select value={filterAction} onChange={(e) => setFilterAction(e.target.value)} className="border border-slate-300 text-slate-700 rounded-lg px-3 py-2 text-sm bg-white">
            <option value="">All Actions</option>
            <option value="create">Create</option>
            <option value="update">Update</option>
            <option value="delete">Delete</option>
            <option value="login">Login</option>
            <option value="export">Export</option>
            <option value="review">Review</option>
          </select>
        </div>
        <select value={filterResource} onChange={(e) => setFilterResource(e.target.value)} className="border border-slate-300 text-slate-700 rounded-lg px-3 py-2 text-sm bg-white">
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
      <div className="bg-white border border-slate-200 rounded-xl overflow-x-auto shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-slate-400">Loading audit trail...</div>
        ) : entries.length === 0 ? (
          <div className="p-12 text-center">
            <ScrollText className="h-12 w-12 mx-auto mb-3 text-slate-300" />
            <p className="font-medium text-slate-700">No audit entries yet</p>
            <p className="text-sm text-slate-500 mt-1">System actions (create, update, delete, login) are logged here automatically.</p>
            <p className="text-sm text-slate-500">Start using ZECT features and entries will appear in real-time.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr className="text-left text-slate-500 text-xs uppercase">
                <th className="px-4 py-3 font-semibold">Timestamp</th>
                <th className="px-4 py-3 font-semibold">Action</th>
                <th className="px-4 py-3 font-semibold">Resource</th>
                <th className="px-4 py-3 font-semibold">Details</th>
                <th className="px-4 py-3 font-semibold">IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {entries.map((e) => (
                <tr key={e.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3 text-slate-500 whitespace-nowrap text-xs">
                    {e.created_at ? new Date(e.created_at).toLocaleString() : "\u2014"}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${actionColor(e.action)}`}>
                      {e.action}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-700 font-medium">
                    {e.resource_type}{e.resource_name ? `: ${e.resource_name}` : ""}
                  </td>
                  <td className="px-4 py-3 text-slate-500 max-w-xs truncate">{e.details}</td>
                  <td className="px-4 py-3 text-slate-400 text-xs font-mono">{e.ip_address || "\u2014"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
