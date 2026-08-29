import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import DeveloperMultiRepoStatus from "@/components/DeveloperMultiRepoStatus";
import {
  developerAsk,
  developerPlan,
  getWorkItem,
  getWorkItemEvents,
  type WorkItemRecord,
} from "@/lib/api";
import { showToast } from "@/components/Toast";

type EventRow = { id: number; event_type: string; payload?: Record<string, unknown> };

type Props = {
  workItemId: number;
};

function short(value?: string | null, n = 12) {
  const s = (value || "").trim();
  if (!s) return "—";
  return s.length > n ? `${s.slice(0, n)}…` : s;
}

export default function WorkItemDetailPanel({ workItemId }: Props) {
  const [item, setItem] = useState<WorkItemRecord | null>(null);
  const [events, setEvents] = useState<EventRow[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const [wi, ev] = await Promise.all([getWorkItem(workItemId), getWorkItemEvents(workItemId)]);
      setItem(wi);
      setEvents(ev.events || []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load WorkItem");
    }
  }, [workItemId]);

  useEffect(() => {
    void load();
  }, [load]);

  const runAsk = async () => {
    if (!item) return;
    setBusy("ask");
    try {
      await developerAsk({
        question: `Summarize WorkItem #${item.id} and affected repositories.`,
        work_item_id: item.id,
        project_id: item.project_id,
        repository_id: item.repository_id,
      });
      showToast("success", "ASK recorded");
      await load();
    } catch (e: unknown) {
      showToast("error", e instanceof Error ? e.message : "ASK failed");
    } finally {
      setBusy("");
    }
  };

  const runPlan = async () => {
    if (!item) return;
    setBusy("plan");
    try {
      const out = await developerPlan({
        goal: item.title || `Plan WorkItem #${item.id}`,
        work_item_id: item.id,
        project_id: item.project_id,
        repository_id: item.repository_id,
      });
      showToast("success", `PLAN ${short(out.plan_hash, 8)}`);
      await load();
    } catch (e: unknown) {
      showToast("error", e instanceof Error ? e.message : "PLAN failed");
    } finally {
      setBusy("");
    }
  };

  const agentEvents = events.filter((e) => /agent|ask|plan|evidence|status/i.test(e.event_type));

  return (
    <section className="mt-6 rounded-xl border border-slate-200 bg-white p-4" data-testid="work-item-detail">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">Selected WorkItem</h2>
          <p className="text-xs text-slate-500">Source → project → repos → ASK/PLAN/AGENT → evidence/CI aggregate.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            data-testid="work-item-ask"
            disabled={!item || Boolean(busy)}
            onClick={() => void runAsk()}
            className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 disabled:opacity-40"
          >
            {busy === "ask" ? "ASK…" : "ASK"}
          </button>
          <button
            type="button"
            data-testid="work-item-plan"
            disabled={!item || Boolean(busy)}
            onClick={() => void runPlan()}
            className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 disabled:opacity-40"
          >
            {busy === "plan" ? "PLAN…" : "PLAN"}
          </button>
          <Link
            className="rounded-lg bg-teal-700 px-3 py-1.5 text-xs text-white"
            data-testid="work-item-open-agent"
            to={`/workspace?work_item_id=${workItemId}`}
          >
            AGENT in Developer
          </Link>
        </div>
      </div>
      {error ? <p className="mt-2 text-xs text-rose-700">{error}</p> : null}
      {!item ? (
        <p className="mt-3 text-xs text-slate-400">Loading detail…</p>
      ) : (
        <dl className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 text-xs text-slate-700">
          <div>
            <dt className="text-slate-400">Source</dt>
            <dd data-testid="work-item-source">{item.source || "user"}</dd>
          </div>
          <div>
            <dt className="text-slate-400">External id</dt>
            <dd data-testid="work-item-external-id">{item.external_id || "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-400">Project</dt>
            <dd data-testid="work-item-project">{item.project_id ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-400">Status</dt>
            <dd data-testid="work-item-status">{item.status}</dd>
          </div>
          <div>
            <dt className="text-slate-400">Repos</dt>
            <dd data-testid="work-item-repos">
              {item.repository_id ? `#${item.repository_id}` : "—"}
              {item.repository_ref ? ` · ${item.repository_ref}` : ""}
            </dd>
          </div>
          <div>
            <dt className="text-slate-400">Plan</dt>
            <dd data-testid="work-item-plan-hash">
              v{item.plan_version || 0} · {short(item.plan_hash)}
            </dd>
          </div>
          <div>
            <dt className="text-slate-400">Agent / run</dt>
            <dd data-testid="work-item-agent">{item.mentrix_run_id ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-400">Worktree / SHA</dt>
            <dd data-testid="work-item-worktree">
              {item.worktree_path || "—"} · {short(item.current_commit_sha || item.base_commit_sha)}
            </dd>
          </div>
        </dl>
      )}
      <div className="mt-3" data-testid="work-item-aggregate">
        <DeveloperMultiRepoStatus workItemId={workItemId} />
      </div>
      <div className="mt-3" data-testid="work-item-evidence">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Events / evidence</p>
        {!agentEvents.length ? (
          <p className="mt-1 text-[11px] text-slate-400">No ASK/PLAN/AGENT events yet.</p>
        ) : (
          <ul className="mt-1 max-h-32 space-y-1 overflow-auto text-[11px] text-slate-600">
            {agentEvents.slice(-8).map((ev) => (
              <li key={ev.id}>
                {ev.event_type}
                {ev.payload?.status ? ` · ${String(ev.payload.status)}` : ""}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
