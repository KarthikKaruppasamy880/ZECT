/**
 * Mentrix Companion — Incident runbook: load Jira ticket, Datadog context,
 * hand off to Mentrix Delivery, comment PR on ticket.
 */
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertTriangle, Loader2, Search, Send } from "lucide-react";
import { mcpExecute, mentrixRealtimeTool } from "@/lib/api";

type IssueCard = {
  key: string;
  summary: string;
  status: string;
  issuetype: string;
  description: string;
  deliveryGoal: string;
};

function flattenAdf(node: unknown): string {
  if (typeof node === "string") return node;
  if (!node || typeof node !== "object") return "";
  const n = node as { type?: string; text?: string; content?: unknown[] };
  if (n.type === "text") return n.text || "";
  if (Array.isArray(n.content)) return n.content.map(flattenAdf).join("");
  return "";
}

function parseIssue(result: any): IssueCard | null {
  const raw = result?.result ?? result;
  if (!raw || raw.status === "not_configured" || raw.status === "disabled") return null;
  const key = raw.key || "";
  const fields = raw.fields || {};
  if (!key && !fields.summary) return null;
  const desc = fields.description;
  const description =
    typeof desc === "string" ? desc : flattenAdf(desc);
  const summary = fields.summary || "";
  return {
    key: key || String(raw.id || ""),
    summary,
    status: fields.status?.name || "",
    issuetype: fields.issuetype?.name || "",
    description: description.slice(0, 4000),
    deliveryGoal: `Fix incident ${key}: ${summary}\n\n${description.slice(0, 1500)}`.trim(),
  };
}

type Props = { defaultExpanded?: boolean };

export default function IncidentRunbookPanel({ defaultExpanded = false }: Props) {
  const navigate = useNavigate();
  const [issueKey, setIssueKey] = useState("");
  const [ddQuery, setDdQuery] = useState("status:error");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [issue, setIssue] = useState<IssueCard | null>(null);
  const [ddNote, setDdNote] = useState("");
  const [prUrl, setPrUrl] = useState("");
  const [commentStatus, setCommentStatus] = useState("");

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("zect_incident_draft");
      if (raw) {
        const d = JSON.parse(raw) as IssueCard;
        if (d?.key) setIssue(d);
      }
    } catch {
      /* ignore */
    }
  }, []);

  const loadIssue = async () => {
    const key = issueKey.trim().toUpperCase();
    if (!key) return;
    setLoading(true);
    setError("");
    setCommentStatus("");
    try {
      const out = await mcpExecute("jira", "get_issue", { issue_key: key });
      const parsed = parseIssue(out);
      if (!parsed) {
        const msg =
          out?.result?.message ||
          (out?.status === "error" ? JSON.stringify(out.result) : "Could not load issue — check Jira MCP config");
        setError(typeof msg === "string" ? msg : "Could not load issue");
        setIssue(null);
        return;
      }
      setIssue(parsed);
      sessionStorage.setItem("zect_incident_draft", JSON.stringify(parsed));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Load failed");
      setIssue(null);
    } finally {
      setLoading(false);
    }
  };

  const queryDatadog = async () => {
    setLoading(true);
    setError("");
    try {
      const out = await mcpExecute("datadog", "query_logs", { query: ddQuery || "status:error" });
      const result = out?.result || {};
      if (result.status === "not_configured" || result.status === "disabled") {
        setDdNote(result.message || "Datadog not configured");
        return;
      }
      const n = Array.isArray(result.data) ? result.data.length : 0;
      setDdNote(`Datadog: ${n} log event(s) for "${ddQuery}"`);
    } catch (e) {
      setDdNote(e instanceof Error ? e.message : "Datadog query failed");
    } finally {
      setLoading(false);
    }
  };

  const useInDelivery = () => {
    if (!issue) return;
    let workspace = "";
    let projectKey = "";
    try {
      const raw = localStorage.getItem("zect_mentrix_workspace");
      if (raw) {
        const ws = JSON.parse(raw) as {
          path?: string;
          workspace?: string;
          project_key?: string;
          projectKey?: string;
        };
        workspace = ws.path || ws.workspace || "";
        projectKey = ws.project_key || ws.projectKey || "";
      }
      projectKey = projectKey || localStorage.getItem("zect_lattice_key") || "";
    } catch {
      /* ignore */
    }
    navigate("/mentrix", {
      state: {
        goal: issue.deliveryGoal,
        issue_key: issue.key,
        projectKey,
        workspace,
      },
    });
  };

  const commentPr = async () => {
    if (!issue?.key || !prUrl.trim()) return;
    setLoading(true);
    setCommentStatus("");
    setError("");
    try {
      // Prefer companion tool (permission-gated); confirm=true for UI action.
      const out = await mentrixRealtimeTool(
        "jira_comment_pr",
        { issue_key: issue.key, pr_url: prUrl.trim() },
        true,
      );
      if (out?.needs_confirm && !out?.ok) {
        setError("Comment needs Allow — try again or check Permissions");
        return;
      }
      if (out?.ok === false || out?.result?.ok === false) {
        setError(out?.error || out?.result?.error || "Comment failed");
        return;
      }
      setCommentStatus(`PR commented on ${issue.key}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Comment failed");
    } finally {
      setLoading(false);
    }
  };

  if (!defaultExpanded && !issue) {
    return (
      <div data-testid="incident-runbook-collapsed" className="text-xs text-slate-400">
        <Link to="/mentrix-home?incident=1" className="text-teal-400 hover:underline inline-flex items-center gap-1">
          <AlertTriangle className="h-3.5 w-3.5" /> Open Incident Runbook
        </Link>
      </div>
    );
  }

  return (
    <div
      data-testid="incident-runbook-panel"
      className="rounded-xl border border-amber-900/50 bg-slate-950/80 p-4 space-y-3"
    >
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 text-amber-400" />
        <h3 className="text-sm font-semibold text-amber-100">Incident runbook</h3>
      </div>
      <p className="text-xs text-slate-400">
        Load a Jira incident, pull Datadog signals, send to Mentrix Delivery (Lattice → upgrade → gates → PR),
        then comment the PR on the ticket.
      </p>

      <div className="flex flex-wrap gap-2">
        <input
          data-testid="incident-issue-key"
          value={issueKey}
          onChange={(e) => setIssueKey(e.target.value)}
          placeholder="Issue key (e.g. INC-123)"
          className="flex-1 min-w-[10rem] rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
        />
        <button
          type="button"
          data-testid="incident-load"
          disabled={loading || !issueKey.trim()}
          onClick={() => void loadIssue()}
          className="inline-flex items-center gap-2 rounded-lg bg-amber-700 hover:bg-amber-600 disabled:opacity-40 px-3 py-2 text-sm text-white"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
          Load
        </button>
      </div>

      {issue && (
        <div data-testid="incident-issue-card" className="rounded-lg border border-slate-700 bg-slate-900/80 p-3 space-y-2">
          <p className="text-sm text-teal-100 font-medium">
            {issue.key} — {issue.summary}
          </p>
          <p className="text-[11px] text-slate-400">
            {issue.issuetype} · {issue.status}
          </p>
          {issue.description && (
            <p className="text-xs text-slate-300 whitespace-pre-wrap max-h-32 overflow-y-auto">
              {issue.description.slice(0, 800)}
            </p>
          )}
          <button
            type="button"
            data-testid="incident-use-delivery"
            onClick={useInDelivery}
            className="inline-flex items-center gap-2 rounded-lg bg-teal-600 hover:bg-teal-500 px-3 py-2 text-sm text-white"
          >
            <Send className="h-4 w-4" />
            Use in Mentrix Delivery
          </button>
        </div>
      )}

      <div className="flex flex-wrap gap-2 items-center">
        <input
          data-testid="incident-datadog-query"
          value={ddQuery}
          onChange={(e) => setDdQuery(e.target.value)}
          placeholder="Datadog log query"
          className="flex-1 min-w-[10rem] rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
        />
        <button
          type="button"
          data-testid="incident-datadog-run"
          disabled={loading}
          onClick={() => void queryDatadog()}
          className="rounded-lg border border-slate-600 px-3 py-2 text-xs text-slate-200 hover:border-teal-600"
        >
          Query Datadog
        </button>
      </div>
      {ddNote && (
        <p data-testid="incident-datadog-note" className="text-xs text-slate-400">
          {ddNote}
        </p>
      )}

      <div className="flex flex-wrap gap-2 items-center border-t border-slate-800 pt-3">
        <input
          data-testid="incident-pr-url"
          value={prUrl}
          onChange={(e) => setPrUrl(e.target.value)}
          placeholder="PR URL to comment on ticket"
          className="flex-1 min-w-[10rem] rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
        />
        <button
          type="button"
          data-testid="incident-comment-pr"
          disabled={loading || !issue?.key || !prUrl.trim()}
          onClick={() => void commentPr()}
          className="rounded-lg border border-teal-700 px-3 py-2 text-xs text-teal-200 disabled:opacity-40"
        >
          Comment PR on ticket
        </button>
      </div>
      {commentStatus && (
        <p data-testid="incident-comment-status" className="text-xs text-emerald-400">
          {commentStatus}
        </p>
      )}
      {error && (
        <p data-testid="incident-error" className="text-xs text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}
