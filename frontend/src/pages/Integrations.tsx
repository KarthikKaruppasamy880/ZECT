import { useState, useEffect } from "react";
import { Plug, CheckCircle, XCircle, Send, Settings, Info } from "lucide-react";
import { mentrixCompanionIntegrations } from "@/lib/api";

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
  const [githubReady, setGithubReady] = useState(false);
  const [browserReady, setBrowserReady] = useState(false);
  const [browserHint, setBrowserHint] = useState("");
  const [presentonReady, setPresentonReady] = useState(false);
  const [presentonUrl, setPresentonUrl] = useState("");
  const [zoomJoinReady, setZoomJoinReady] = useState(false);
  const [zoomPathReady, setZoomPathReady] = useState(false);
  const [processReady, setProcessReady] = useState(false);
  const [processDetail, setProcessDetail] = useState("");
  const [connectorMatrix, setConnectorMatrix] = useState<any[]>([]);

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
      try {
        const integ = await mentrixCompanionIntegrations();
        setGithubReady(!!integ.github);
        setBrowserReady(!!integ.browser);
        setBrowserHint(integ.browser_hint || "");
        setPresentonReady(!!integ.presenton);
        setPresentonUrl(integ.presenton_base_url || "");
        setZoomJoinReady(!!integ.zoom_join_url_configured);
        setZoomPathReady(!!integ.zoom_desktop_path_configured);
      } catch {
        /* companion integrations optional */
      }
      try {
        const cm = await fetch(`${API}/api/personal-actions/connectors/health`, { headers });
        if (cm.ok) {
          const data = await cm.json();
          setConnectorMatrix(data.connectors || []);
        }
      } catch {
        setConnectorMatrix([]);
      }
      try {
        const pRes = await fetch(`${API}/api/process/status`, { headers });
        if (pRes.ok) {
          const p = await pRes.json();
          setProcessReady(!!p.ready);
          setProcessDetail(p.detail || p.status || "");
        }
      } catch {
        setProcessReady(false);
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
            <li><strong>Browser automation</strong> — Mentrix uses Playwright via BrowserRuntime. Install: <code>pip install playwright && playwright install chromium</code>. See docs/BROWSER_RUNTIME.md.</li>
            <li><strong>GitHub</strong> — Set <code>GITHUB_TOKEN</code> in <code>backend/.env</code> (repo read + PR create). Status card below shows readiness (never shows the token).</li>
            <li><strong>Jira</strong> — UI form below <em>or</em> env: <code>JIRA_BASE_URL</code> / <code>MCP_JIRA_URL</code>, <code>JIRA_EMAIL</code>, <code>JIRA_API_TOKEN</code>. Same credentials power Mentrix Incident + MCP.</li>
            <li><strong>Slack</strong> — Get notifications when reviews complete, deployments happen, or budget alerts trigger. Create a Slack bot at api.slack.com/apps.</li>
            <li><strong>Presenton</strong> — Self-host Docker; set <code>PRESENTON_BASE_URL</code>. Mentrix Companion → Present Deck → Generate deck → PPTX path.</li>
            <li><strong>Zoom (Present Deck)</strong> — Optional <code>ZOOM_DESKTOP_PATH</code> / <code>ZOOM_DEFAULT_JOIN_URL</code>. Mentrix opens Zoom only; you join and share PowerPoint (no Meeting SDK).</li>
            <li><strong>MCP hub</strong> — Mentrix Integrator/Ops <em>execute</em> outbound tools via <code>/api/mcp</code> (Rules Engine gates every call).</li>
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6" data-testid="integrations-readiness">
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-3 shadow-sm" data-testid="integrations-github-card">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-slate-900 font-semibold">GitHub</h3>
              <p className="text-xs text-slate-500">Repo analysis, Mentrix Create PR, Actions</p>
            </div>
            {githubReady ? (
              <CheckCircle className="h-5 w-5 text-green-500" data-testid="github-ready" />
            ) : (
              <XCircle className="h-5 w-5 text-slate-300" data-testid="github-missing" />
            )}
          </div>
          <p className="text-sm text-slate-600">
            {githubReady
              ? "GITHUB_TOKEN is set in backend env (value never shown)."
              : "Not ready — add GITHUB_TOKEN to backend/.env and restart uvicorn."}
          </p>
          <p className="text-xs text-slate-500">
            Token needs repo + pull_request write for real Mentrix PRs. Keep MENTRIX_PR_DRY_RUN=true until you intend a live PR.
          </p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-3 shadow-sm" data-testid="integrations-process-card">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-slate-900 font-semibold">Mentrix Process</h3>
              <p className="text-xs text-slate-500">BPM deploy / start / incidents</p>
            </div>
            {processReady ? (
              <CheckCircle className="h-5 w-5 text-green-500" data-testid="process-ready" />
            ) : (
              <XCircle className="h-5 w-5 text-slate-300" data-testid="process-missing" />
            )}
          </div>
          <p className="text-sm text-slate-600">
            {processReady
              ? `Engine ready (${processDetail || "ok"}).`
              : "Set ZECT_CAMUNDA_BASE_URL (+ user/password) and optional ZECT_CAMUNDA_COCKPIT_URL."}
          </p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-3 shadow-sm" data-testid="integrations-browser-card">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-slate-900 font-semibold">Browser automation</h3>
              <p className="text-xs text-slate-500">Mentrix → BrowserRuntime → Playwright</p>
            </div>
            {browserReady ? (
              <CheckCircle className="h-5 w-5 text-green-500" data-testid="browser-ready" />
            ) : (
              <XCircle className="h-5 w-5 text-slate-300" data-testid="browser-missing" />
            )}
          </div>
          <p className="text-sm text-slate-600">
            {browserReady
              ? "Playwright Chromium is ready for Mentrix browser tools."
              : browserHint ||
                "Offline — run: pip install playwright && playwright install chromium"}
          </p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-3 shadow-sm" data-testid="integrations-zoom-card">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-slate-900 font-semibold">Zoom + Presenton</h3>
              <p className="text-xs text-slate-500">Present Deck assist (no auto-share)</p>
            </div>
            {presentonReady || zoomJoinReady || zoomPathReady ? (
              <CheckCircle className="h-5 w-5 text-green-500" />
            ) : (
              <XCircle className="h-5 w-5 text-slate-300" />
            )}
          </div>
          <ul className="text-sm text-slate-600 space-y-1">
            <li>Presenton: {presentonReady ? `ready (${presentonUrl || "configured"})` : "set PRESENTON_BASE_URL"}</li>
            <li>Zoom path: {zoomPathReady ? "ZOOM_DESKTOP_PATH set" : "auto-detect Zoom.exe / set path"}</li>
            <li>Join URL: {zoomJoinReady ? "ZOOM_DEFAULT_JOIN_URL set" : "optional — paste in Present Deck"}</li>
          </ul>
        </div>
      </div>

      {connectorMatrix.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-5" data-testid="connector-health-matrix">
          <h3 className="font-semibold text-slate-900 mb-1">Mentrix connector gateway</h3>
          <p className="text-xs text-slate-500 mb-3">
            Connected / Degraded / Missing credentials · read/write tools · permission policy (ALLOW / CONFIRM / DENY)
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="text-xs text-slate-500 border-b border-slate-100">
                  <th className="py-2 pr-3 font-medium">Connector</th>
                  <th className="py-2 pr-3 font-medium">Health</th>
                  <th className="py-2 pr-3 font-medium">Auth</th>
                  <th className="py-2 pr-3 font-medium">Policy</th>
                  <th className="py-2 pr-3 font-medium">Read</th>
                  <th className="py-2 font-medium">Write</th>
                </tr>
              </thead>
              <tbody>
                {connectorMatrix.map((c) => {
                  const health = String(c.health || c.status || "unknown");
                  const auth = String(c.auth_status || "unknown");
                  const policy = String(c.permission_policy || c.policy || "CONFIRM");
                  const healthColor =
                    health === "connected" || health === "ok"
                      ? "text-green-600"
                      : health === "degraded"
                        ? "text-amber-600"
                        : health === "missing_creds" || health === "missing"
                          ? "text-slate-400"
                          : "text-slate-600";
                  return (
                    <tr key={c.id || c.connector_id || c.name} className="border-b border-slate-50">
                      <td className="py-2 pr-3 font-medium text-slate-800">{c.name || c.id || c.connector_id}</td>
                      <td className={`py-2 pr-3 ${healthColor}`}>{health}</td>
                      <td className="py-2 pr-3 text-slate-600">{auth}</td>
                      <td className="py-2 pr-3 text-slate-600">{policy}</td>
                      <td className="py-2 pr-3 text-xs text-slate-500">
                        {(c.read_tools || c.tools_read || []).join(", ") || "—"}
                      </td>
                      <td className="py-2 text-xs text-slate-500">
                        {(c.write_tools || c.tools_write || []).join(", ") || "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
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
