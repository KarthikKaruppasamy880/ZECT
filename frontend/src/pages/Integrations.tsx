import { useState, useEffect } from "react";
import { Plug, CheckCircle, XCircle, Send, Settings, Info } from "lucide-react";

interface JiraStatus {
  configured: boolean;
  base_url: string;
  email: string;
  is_active: boolean;
  linked_tickets: number;
}

interface SlackStatus {
  configured: boolean;
  workspace_name: string;
  default_channel: string;
  is_active: boolean;
  notify_on_review: boolean;
  notify_on_deploy: boolean;
  notify_on_budget_alert: boolean;
}

const API = import.meta.env.VITE_API_URL ?? "";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("zect_token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export default function Integrations() {
  const [jiraStatus, setJiraStatus] = useState<JiraStatus | null>(null);
  const [slackStatus, setSlackStatus] = useState<SlackStatus | null>(null);
  const [mcpServers, setMcpServers] = useState<any[]>([]);
  const [mcpConfigs, setMcpConfigs] = useState<any[]>([]);
  const [showJiraForm, setShowJiraForm] = useState(false);
  const [showSlackForm, setShowSlackForm] = useState(false);
  const [showGuide, setShowGuide] = useState(false);
  const [toggling, setToggling] = useState("");
  const [jiraForm, setJiraForm] = useState({ base_url: "", email: "", api_token: "", default_project_key: "" });
  const [slackForm, setSlackForm] = useState({ bot_token: "", workspace_name: "", default_channel: "#zect-notifications" });
  const [testMsg, setTestMsg] = useState("");

  const fetchStatus = async () => {
    try {
      const headers = authHeaders();
      const [jRes, sRes, mRes, cRes] = await Promise.all([
        fetch(`${API}/api/jira/status`, { headers }),
        fetch(`${API}/api/slack/status`, { headers }),
        fetch(`${API}/api/mcp/servers`, { headers }),
        fetch(`${API}/api/mcp/configs`, { headers }),
      ]);
      if (jRes.ok) setJiraStatus(await jRes.json());
      if (sRes.ok) setSlackStatus(await sRes.json());
      if (mRes.ok) {
        const data = await mRes.json();
        setMcpServers(Array.isArray(data) ? data : data.servers || []);
      }
      if (cRes.ok) {
        const data = await cRes.json();
        setMcpConfigs(Array.isArray(data) ? data : data.configs || []);
      }
    } catch { /* API not available */ }
  };

  const toggleMcp = async (serverId: string, name: string, enabled: boolean) => {
    setToggling(serverId);
    try {
      await fetch(`${API}/api/mcp/configs`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ server_id: serverId, name, enabled }),
      });
      await fetchStatus();
    } catch { /* ignore */ }
    setToggling("");
  };

  useEffect(() => { fetchStatus(); }, []);

  const configureJira = async () => {
    try {
      const res = await fetch(`${API}/api/jira/config`, {
        method: "POST", headers: authHeaders(),
        body: JSON.stringify(jiraForm),
      });
      if (res.ok) { setShowJiraForm(false); fetchStatus(); }
    } catch { /* error */ }
  };

  const configureSlack = async () => {
    try {
      const res = await fetch(`${API}/api/slack/config`, {
        method: "POST", headers: authHeaders(),
        body: JSON.stringify(slackForm),
      });
      if (res.ok) { setShowSlackForm(false); fetchStatus(); }
    } catch { /* error */ }
  };

  const sendTestNotification = async () => {
    if (!testMsg.trim()) return;
    try {
      await fetch(`${API}/api/slack/notify`, {
        method: "POST", headers: authHeaders(),
        body: JSON.stringify({ message: testMsg }),
      });
      setTestMsg("");
    } catch { /* error */ }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6" data-testid="integrations-page">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-indigo-100 rounded-xl">
            <Plug className="h-6 w-6 text-indigo-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Integrations</h1>
            <p className="text-sm text-slate-500">Mentrix MCP hub — GitHub, Jira, Confluence, Slack, Datadog, Filesystem</p>
          </div>
        </div>
        <button onClick={() => setShowGuide(!showGuide)} className="flex items-center gap-1.5 px-3 py-2 bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200 text-sm">
          <Info className="h-4 w-4" /> Guide
        </button>
      </div>

      {/* Usage Guide */}
      {showGuide && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-5 space-y-2">
          <h3 className="font-semibold text-indigo-900">How to use Integrations</h3>
          <ul className="text-sm text-indigo-800 space-y-1 list-disc list-inside">
            <li><strong>Jira</strong> — Connect your Atlassian instance to create tickets from code review findings. You need a Jira API token (Settings &rarr; API tokens in Atlassian).</li>
            <li><strong>Slack</strong> — Get notifications when reviews complete, deployments happen, or budget alerts trigger. Create a Slack bot at api.slack.com/apps.</li>
            <li><strong>Test notifications</strong> — After configuring Slack, use the test message box to verify the connection works.</li>
            <li><strong>GitHub</strong> — Set GITHUB_TOKEN in your backend .env file for repo analysis and PR review features.</li>
            <li><strong>MCP hub</strong> — Mentrix Integrator/Ops <em>execute</em> outbound tools via <code>/api/mcp</code> (Rules Engine gates every call).</li>
            <li><strong>Slack / Email / Datadog (Wave 1 outbound)</strong> — Enable below; set <code>SLACK_BOT_TOKEN</code>, <code>SMTP_*</code>, <code>DATADOG_*</code> in backend <code>.env</code>.</li>
            <li><strong>Wave 2</strong> — Slack Events inbound reply bot and email inbox poll (not in this ship).</li>
          </ul>
        </div>
      )}

      {mcpServers.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-5" data-testid="mcp-enable-panel">
          <h3 className="font-semibold text-slate-900 mb-1">MCP adapters — enable for Mentrix</h3>
          <p className="text-xs text-slate-500 mb-3">
            Outbound-first: Slack send, email send, Datadog query_logs. Env: SLACK_BOT_TOKEN, SMTP_HOST/USER/PASSWORD, DATADOG_API_KEY / APP_KEY.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {mcpServers.map((s) => {
              const id = s.id || s.server_id || s.name;
              const cfg = mcpConfigs.find((c) => c.server_id === id);
              const enabled = Boolean(cfg?.enabled);
              return (
                <div key={id} className="rounded-lg border border-slate-200 px-3 py-2 text-sm flex items-center justify-between gap-2">
                  <div>
                    <div className="font-medium text-slate-800">{s.name || id}</div>
                    <div className="text-xs text-slate-500">
                      {s.status || "available"} · {s.tools_count ?? "—"} tools
                      {cfg?.last_health ? ` · ${cfg.last_health}` : ""}
                    </div>
                  </div>
                  <button
                    data-testid={`mcp-toggle-${id}`}
                    disabled={toggling === id}
                    onClick={() => toggleMcp(id, s.name || id, !enabled)}
                    className={`px-3 py-1 rounded-md text-xs font-medium border ${
                      enabled
                        ? "bg-teal-50 text-teal-800 border-teal-200"
                        : "bg-slate-50 text-slate-600 border-slate-200"
                    }`}
                  >
                    {enabled ? "Enabled" : "Enable"}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Jira Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-blue-100 flex items-center justify-center">
                <span className="text-blue-600 font-bold text-lg">J</span>
              </div>
              <div>
                <h3 className="text-slate-900 font-semibold">Jira</h3>
                <p className="text-xs text-slate-500">Issue tracking & project management</p>
              </div>
            </div>
            {jiraStatus?.configured ? (
              <CheckCircle className="h-5 w-5 text-green-500" />
            ) : (
              <XCircle className="h-5 w-5 text-slate-300" />
            )}
          </div>

          {jiraStatus?.configured ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-slate-500">URL:</span><span className="text-slate-700">{jiraStatus.base_url}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Email:</span><span className="text-slate-700">{jiraStatus.email}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Tickets:</span><span className="text-blue-600 font-medium">{jiraStatus.linked_tickets}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Status:</span><span className={jiraStatus.is_active ? "text-green-600 font-medium" : "text-red-600"}>{jiraStatus.is_active ? "Active" : "Inactive"}</span></div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Not configured. Connect your Jira instance to create tickets from code review findings.</p>
          )}

          <button onClick={() => setShowJiraForm(!showJiraForm)} className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 text-sm font-medium border border-blue-200">
            <Settings className="h-4 w-4" /> {jiraStatus?.configured ? "Update" : "Configure"}
          </button>

          {showJiraForm && (
            <div className="space-y-3 pt-3 border-t border-slate-200">
              <input value={jiraForm.base_url} onChange={(e) => setJiraForm({ ...jiraForm, base_url: e.target.value })} placeholder="https://yourcompany.atlassian.net" className="w-full border border-slate-300 text-slate-900 rounded-lg px-3 py-2 text-sm" />
              <input value={jiraForm.email} onChange={(e) => setJiraForm({ ...jiraForm, email: e.target.value })} placeholder="email@company.com" className="w-full border border-slate-300 text-slate-900 rounded-lg px-3 py-2 text-sm" />
              <input type="password" value={jiraForm.api_token} onChange={(e) => setJiraForm({ ...jiraForm, api_token: e.target.value })} placeholder="Jira API Token" className="w-full border border-slate-300 text-slate-900 rounded-lg px-3 py-2 text-sm" />
              <input value={jiraForm.default_project_key} onChange={(e) => setJiraForm({ ...jiraForm, default_project_key: e.target.value })} placeholder="Project Key (e.g. PROJ)" className="w-full border border-slate-300 text-slate-900 rounded-lg px-3 py-2 text-sm" />
              <button onClick={configureJira} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium">Save</button>
            </div>
          )}
        </div>

        {/* Slack Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-green-100 flex items-center justify-center">
                <span className="text-green-600 font-bold text-lg">S</span>
              </div>
              <div>
                <h3 className="text-slate-900 font-semibold">Slack</h3>
                <p className="text-xs text-slate-500">Team notifications & alerts</p>
              </div>
            </div>
            {slackStatus?.configured ? (
              <CheckCircle className="h-5 w-5 text-green-500" />
            ) : (
              <XCircle className="h-5 w-5 text-slate-300" />
            )}
          </div>

          {slackStatus?.configured ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-slate-500">Workspace:</span><span className="text-slate-700">{slackStatus.workspace_name || "\u2014"}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Channel:</span><span className="text-slate-700">{slackStatus.default_channel}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Review alerts:</span><span className={slackStatus.notify_on_review ? "text-green-600 font-medium" : "text-slate-400"}>{slackStatus.notify_on_review ? "On" : "Off"}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Deploy alerts:</span><span className={slackStatus.notify_on_deploy ? "text-green-600 font-medium" : "text-slate-400"}>{slackStatus.notify_on_deploy ? "On" : "Off"}</span></div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Not configured. Connect Slack to get notifications on reviews, deploys, and budget alerts.</p>
          )}

          <button onClick={() => setShowSlackForm(!showSlackForm)} className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-green-50 text-green-600 rounded-lg hover:bg-green-100 text-sm font-medium border border-green-200">
            <Settings className="h-4 w-4" /> {slackStatus?.configured ? "Update" : "Configure"}
          </button>

          {showSlackForm && (
            <div className="space-y-3 pt-3 border-t border-slate-200">
              <input value={slackForm.workspace_name} onChange={(e) => setSlackForm({ ...slackForm, workspace_name: e.target.value })} placeholder="Workspace name" className="w-full border border-slate-300 text-slate-900 rounded-lg px-3 py-2 text-sm" />
              <input type="password" value={slackForm.bot_token} onChange={(e) => setSlackForm({ ...slackForm, bot_token: e.target.value })} placeholder="Slack Bot Token (xoxb-...)" className="w-full border border-slate-300 text-slate-900 rounded-lg px-3 py-2 text-sm" />
              <input value={slackForm.default_channel} onChange={(e) => setSlackForm({ ...slackForm, default_channel: e.target.value })} placeholder="#zect-notifications" className="w-full border border-slate-300 text-slate-900 rounded-lg px-3 py-2 text-sm" />
              <button onClick={configureSlack} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium">Save</button>
            </div>
          )}

          {slackStatus?.configured && (
            <div className="flex gap-2 pt-3 border-t border-slate-200">
              <input value={testMsg} onChange={(e) => setTestMsg(e.target.value)} placeholder="Send a test message..." className="flex-1 border border-slate-300 text-slate-900 rounded-lg px-3 py-2 text-sm" />
              <button onClick={sendTestNotification} className="px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
                <Send className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
