import { useEffect, useState } from "react";
import { ShieldAlert, RefreshCw, CheckCircle, AlertTriangle } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { showToast } from "@/components/Toast";

type Finding = {
  id: number;
  fingerprint: string;
  source: string;
  kind: string;
  severity: string;
  status: string;
  title: string;
  description: string;
  host: string;
  correlation_id: string;
};

type Incident = {
  id: number;
  finding_id: number;
  status: string;
  summary: string;
  severity: string;
  jira_key: string;
  approval_status: string;
  correlation_id: string;
};

export default function SecurityIncidents() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [malwareStatus, setMalwareStatus] = useState<Record<string, unknown> | null>(null);
  const [scanPath, setScanPath] = useState("");

  const refresh = async () => {
    setLoading(true);
    try {
      const [fRes, iRes, mRes] = await Promise.all([
        apiFetch("/api/security/findings"),
        apiFetch("/api/security/incidents"),
        apiFetch("/api/security/malware/status"),
      ]);
      if (fRes.ok) setFindings(await fRes.json());
      if (iRes.ok) setIncidents(await iRes.json());
      if (mRes.ok) setMalwareStatus(await mRes.json());
    } catch {
      showToast("error", "Failed to load security data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const runScan = async () => {
    setBusy(true);
    try {
      const res = await apiFetch("/api/security/scan?lookback_hours=24", { method: "POST" });
      if (!res.ok) {
        showToast("error", `Scan failed (${res.status})`);
        return;
      }
      const body = await res.json();
      showToast("success", `Scan complete — ${body.findings?.length || 0} open finding(s)`);
      await refresh();
    } catch {
      showToast("error", "Scan failed");
    } finally {
      setBusy(false);
    }
  };

  const draftFromFinding = async (findingId: number) => {
    setBusy(true);
    try {
      const res = await apiFetch("/api/security/incidents/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ finding_id: findingId }),
      });
      if (!res.ok) {
        showToast("error", `Draft failed (${res.status})`);
        return;
      }
      showToast("success", "Incident draft created — approve to open Jira");
      await refresh();
    } catch {
      showToast("error", "Draft failed");
    } finally {
      setBusy(false);
    }
  };

  const approveIncident = async (incidentId: number) => {
    if (!window.confirm("Approve this incident? This may create a Jira issue and Slack notice.")) return;
    setBusy(true);
    try {
      const res = await apiFetch(`/api/security/incidents/${incidentId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved: true, create_jira: true, notify_slack: true }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        showToast("error", err.detail || `Approve failed (${res.status})`);
        return;
      }
      const body = await res.json();
      showToast("success", body.jira_key ? `Jira ${body.jira_key}` : "Incident approved");
      await refresh();
    } catch {
      showToast("error", "Approve failed");
    } finally {
      setBusy(false);
    }
  };

  const sevClass = (s: string) =>
    s === "critical" || s === "high"
      ? "bg-red-100 text-red-700"
      : s === "medium"
        ? "bg-amber-100 text-amber-700"
        : "bg-slate-100 text-slate-600";

  return (
    <div data-testid="security-incidents-page">
      <div className="flex items-center justify-between mb-6 gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <ShieldAlert className="h-6 w-6 text-red-600" /> ZECT Security Agent
          </h1>
          <p className="text-slate-500 text-sm">
            Audit findings, IR drafts, and malware scan — Mentrix coordinates; automatic process kill stays off.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={runScan}
            disabled={busy}
            className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-60"
          >
            Run audit scan
          </button>
          <button onClick={refresh} className="p-2 rounded hover:bg-slate-100" title="Refresh">
            <RefreshCw className="h-4 w-4 text-slate-500" />
          </button>
        </div>
      </div>

      <div
        className="mb-6 rounded-xl border border-slate-200 bg-white p-5"
        data-testid="security-malware-panel"
      >
        <h2 className="text-sm font-semibold text-slate-800 mb-2">Malware Scan</h2>
        <p className="text-xs text-slate-500 mb-3">
          Engine:{" "}
          <span data-testid="security-malware-status">
            {malwareStatus
              ? `${malwareStatus.label || "ZECT Security Agent"} — ${malwareStatus.status || "unknown"}`
              : "loading…"}
          </span>
        </p>
        <div className="flex flex-wrap gap-2 items-center">
          <input
            value={scanPath}
            onChange={(e) => setScanPath(e.target.value)}
            placeholder="Allowlisted file path to scan"
            className="flex-1 min-w-[12rem] rounded-lg border border-slate-200 px-3 py-1.5 text-sm"
          />
          <button
            type="button"
            disabled={busy || !scanPath.trim()}
            className="px-3 py-1.5 bg-slate-800 text-white rounded-lg text-sm disabled:opacity-60"
            onClick={async () => {
              setBusy(true);
              try {
                const res = await apiFetch("/api/security/malware/scan", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ path: scanPath.trim(), quarantine: true }),
                });
                const body = await res.json().catch(() => ({}));
                if (!res.ok) {
                  showToast("error", body.detail?.error || body.error || `Scan failed (${res.status})`);
                } else if (body.infected) {
                  showToast("success", `Threat found — quarantined if requested`);
                  await refresh();
                } else {
                  showToast("success", "Clean");
                }
              } catch {
                showToast("error", "Malware scan failed");
              } finally {
                setBusy(false);
              }
            }}
          >
            Scan file
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="text-sm font-semibold text-slate-800 mb-3 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-600" /> Findings ({findings.length})
            </h2>
            {findings.length === 0 ? (
              <p className="text-sm text-slate-400 py-8 text-center">No findings yet — run an audit scan.</p>
            ) : (
              <div className="space-y-2 max-h-[28rem] overflow-y-auto">
                {findings.map((f) => (
                  <div key={f.id} className="p-3 bg-slate-50 rounded-lg">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-xs px-2 py-0.5 rounded ${sevClass(f.severity)}`}>{f.severity}</span>
                      <span className="text-xs text-slate-500">{f.source}</span>
                      <span className="text-xs text-slate-400">{f.status}</span>
                    </div>
                    <p className="text-sm font-medium text-slate-800 mt-1">{f.title || f.kind}</p>
                    <p className="text-xs text-slate-500 line-clamp-2 mt-0.5">{f.description}</p>
                    {f.status === "open" && (
                      <button
                        onClick={() => draftFromFinding(f.id)}
                        disabled={busy}
                        className="mt-2 text-xs text-indigo-600 hover:text-indigo-700"
                      >
                        Draft incident
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="text-sm font-semibold text-slate-800 mb-3 flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-600" /> Incidents ({incidents.length})
            </h2>
            {incidents.length === 0 ? (
              <p className="text-sm text-slate-400 py-8 text-center">No incident drafts yet.</p>
            ) : (
              <div className="space-y-2 max-h-[28rem] overflow-y-auto">
                {incidents.map((i) => (
                  <div key={i.id} className="p-3 bg-slate-50 rounded-lg">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-xs px-2 py-0.5 rounded ${sevClass(i.severity)}`}>{i.severity}</span>
                      <span className="text-xs text-slate-500">{i.status}</span>
                      {i.jira_key && <span className="text-xs font-mono text-indigo-700">{i.jira_key}</span>}
                    </div>
                    <p className="text-sm font-medium text-slate-800 mt-1">{i.summary}</p>
                    <p className="text-xs text-slate-400 mt-0.5">correlation {i.correlation_id || "—"}</p>
                    {i.approval_status === "pending" && (
                      <button
                        onClick={() => approveIncident(i.id)}
                        disabled={busy}
                        className="mt-2 text-xs bg-green-600 text-white px-2 py-1 rounded hover:bg-green-700"
                      >
                        Approve → Jira / Slack
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
