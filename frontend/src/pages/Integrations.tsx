import { useState, useEffect } from "react";
import { Plug, CheckCircle, XCircle, Send, Settings } from "lucide-react";

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

export default function Integrations() {
  const [jiraStatus, setJiraStatus] = useState<JiraStatus | null>(null);
  const [slackStatus, setSlackStatus] = useState<SlackStatus | null>(null);
  const [showJiraForm, setShowJiraForm] = useState(false);
  const [showSlackForm, setShowSlackForm] = useState(false);
  const [jiraForm, setJiraForm] = useState({ base_url: "", email: "", api_token: "", default_project_key: "" });
  const [slackForm, setSlackForm] = useState({ bot_token: "", workspace_name: "", default_channel: "#zect-notifications" });
  const [testMsg, setTestMsg] = useState("");

  const fetchStatus = async () => {
    try {
      const [jRes, sRes] = await Promise.all([
        fetch(`${API}/api/jira/status`),
        fetch(`${API}/api/slack/status`),
      ]);
      if (jRes.ok) setJiraStatus(await jRes.json());
      if (sRes.ok) setSlackStatus(await sRes.json());
    } catch { /* API not available */ }
  };

  useEffect(() => { fetchStatus(); }, []);

  const configureJira = async () => {
    try {
      const res = await fetch(`${API}/api/jira/config`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(jiraForm),
      });
      if (res.ok) { setShowJiraForm(false); fetchStatus(); }
    } catch { /* error */ }
  };

  const configureSlack = async () => {
    try {
      const res = await fetch(`${API}/api/slack/config`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(slackForm),
      });
      if (res.ok) { setShowSlackForm(false); fetchStatus(); }
    } catch { /* error */ }
  };

  const sendTestNotification = async () => {
    if (!testMsg.trim()) return;
    try {
      await fetch(`${API}/api/slack/notify`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: testMsg }),
      });
      setTestMsg("");
    } catch { /* error */ }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Plug className="h-6 w-6 text-indigo-400" />
          Integrations
        </h1>
        <p className="text-sm text-slate-400 mt-1">Connect ZECT with Jira, Slack, and other services</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Jira Card */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-blue-600/20 flex items-center justify-center">
                <span className="text-blue-400 font-bold text-lg">J</span>
              </div>
              <div>
                <h3 className="text-white font-semibold">Jira</h3>
                <p className="text-xs text-slate-400">Issue tracking & project management</p>
              </div>
            </div>
            {jiraStatus?.configured ? (
              <CheckCircle className="h-5 w-5 text-green-400" />
            ) : (
              <XCircle className="h-5 w-5 text-slate-500" />
            )}
          </div>

          {jiraStatus?.configured ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-slate-400">URL:</span><span className="text-slate-300">{jiraStatus.base_url}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Email:</span><span className="text-slate-300">{jiraStatus.email}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Tickets:</span><span className="text-cyan-400">{jiraStatus.linked_tickets}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Status:</span><span className={jiraStatus.is_active ? "text-green-400" : "text-red-400"}>{jiraStatus.is_active ? "Active" : "Inactive"}</span></div>
            </div>
          ) : (
            <p className="text-sm text-slate-400">Not configured. Connect your Jira instance to create tickets from reviews.</p>
          )}

          <button onClick={() => setShowJiraForm(!showJiraForm)} className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600/20 text-blue-400 rounded-lg hover:bg-blue-600/30 text-sm font-medium border border-blue-600/30">
            <Settings className="h-4 w-4" /> {jiraStatus?.configured ? "Update" : "Configure"}
          </button>

          {showJiraForm && (
            <div className="space-y-3 pt-2 border-t border-slate-700">
              <input value={jiraForm.base_url} onChange={(e) => setJiraForm({ ...jiraForm, base_url: e.target.value })} placeholder="https://yourcompany.atlassian.net" className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg px-3 py-2 text-sm" />
              <input value={jiraForm.email} onChange={(e) => setJiraForm({ ...jiraForm, email: e.target.value })} placeholder="email@company.com" className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg px-3 py-2 text-sm" />
              <input type="password" value={jiraForm.api_token} onChange={(e) => setJiraForm({ ...jiraForm, api_token: e.target.value })} placeholder="Jira API Token" className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg px-3 py-2 text-sm" />
              <input value={jiraForm.default_project_key} onChange={(e) => setJiraForm({ ...jiraForm, default_project_key: e.target.value })} placeholder="Project Key (e.g. PROJ)" className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg px-3 py-2 text-sm" />
              <button onClick={configureJira} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 text-sm font-medium">Save</button>
            </div>
          )}
        </div>

        {/* Slack Card */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-green-600/20 flex items-center justify-center">
                <span className="text-green-400 font-bold text-lg">S</span>
              </div>
              <div>
                <h3 className="text-white font-semibold">Slack</h3>
                <p className="text-xs text-slate-400">Team notifications & alerts</p>
              </div>
            </div>
            {slackStatus?.configured ? (
              <CheckCircle className="h-5 w-5 text-green-400" />
            ) : (
              <XCircle className="h-5 w-5 text-slate-500" />
            )}
          </div>

          {slackStatus?.configured ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-slate-400">Workspace:</span><span className="text-slate-300">{slackStatus.workspace_name || "—"}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Channel:</span><span className="text-slate-300">{slackStatus.default_channel}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Review alerts:</span><span className={slackStatus.notify_on_review ? "text-green-400" : "text-slate-500"}>{slackStatus.notify_on_review ? "On" : "Off"}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Deploy alerts:</span><span className={slackStatus.notify_on_deploy ? "text-green-400" : "text-slate-500"}>{slackStatus.notify_on_deploy ? "On" : "Off"}</span></div>
            </div>
          ) : (
            <p className="text-sm text-slate-400">Not configured. Connect Slack to get notifications on reviews, deploys, and budget alerts.</p>
          )}

          <button onClick={() => setShowSlackForm(!showSlackForm)} className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-green-600/20 text-green-400 rounded-lg hover:bg-green-600/30 text-sm font-medium border border-green-600/30">
            <Settings className="h-4 w-4" /> {slackStatus?.configured ? "Update" : "Configure"}
          </button>

          {showSlackForm && (
            <div className="space-y-3 pt-2 border-t border-slate-700">
              <input value={slackForm.workspace_name} onChange={(e) => setSlackForm({ ...slackForm, workspace_name: e.target.value })} placeholder="Workspace name" className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg px-3 py-2 text-sm" />
              <input type="password" value={slackForm.bot_token} onChange={(e) => setSlackForm({ ...slackForm, bot_token: e.target.value })} placeholder="Slack Bot Token (xoxb-...)" className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg px-3 py-2 text-sm" />
              <input value={slackForm.default_channel} onChange={(e) => setSlackForm({ ...slackForm, default_channel: e.target.value })} placeholder="#zect-notifications" className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg px-3 py-2 text-sm" />
              <button onClick={configureSlack} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500 text-sm font-medium">Save</button>
            </div>
          )}

          {slackStatus?.configured && (
            <div className="flex gap-2 pt-2 border-t border-slate-700">
              <input value={testMsg} onChange={(e) => setTestMsg(e.target.value)} placeholder="Test message..." className="flex-1 bg-slate-900 border border-slate-700 text-white rounded-lg px-3 py-2 text-sm" />
              <button onClick={sendTestNotification} className="px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500">
                <Send className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
