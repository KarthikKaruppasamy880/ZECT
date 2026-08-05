import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, Loader2, RefreshCw } from "lucide-react";
import { mentrixGetRun, mentrixListRuns } from "@/lib/api";

type MentrixEvent = {
  sequence_id?: number;
  agent?: string;
  phase?: string;
  event?: string;
  next_step?: string;
  message?: string;
};

type MentrixRunSummary = {
  id: number;
  goal?: string;
  status?: string;
  mode?: string;
  events?: MentrixEvent[];
};

type WorkspaceMentrixTimelineProps = {
  /** Optional filter hint — runs are global; workspace shown for context. */
  workspaceRoot?: string;
};

/**
 * Phase 3 Stage B — compact Mentrix agent activity timeline for the developer workspace.
 * Polls the selected run while status === "running".
 */
export default function WorkspaceMentrixTimeline({ workspaceRoot }: WorkspaceMentrixTimelineProps) {
  const [runs, setRuns] = useState<MentrixRunSummary[]>([]);
  const [active, setActive] = useState<MentrixRunSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const selectedIdRef = useRef<number | null>(null);

  const loadRun = useCallback(async (id: number) => {
    setError("");
    try {
      const run = await mentrixGetRun(id);
      selectedIdRef.current = id;
      setActive(run);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load run");
    }
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const list = await mentrixListRuns(12);
      const arr = Array.isArray(list) ? list : [];
      setRuns(arr);
      const preferred = selectedIdRef.current ?? arr[0]?.id ?? null;
      if (preferred != null) {
        await loadRun(preferred);
      } else {
        setActive(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load runs");
    } finally {
      setLoading(false);
    }
  }, [loadRun]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Poll active run while running
  useEffect(() => {
    if (!active?.id || active.status !== "running") return;
    const id = active.id;
    const t = window.setInterval(async () => {
      try {
        const next = await mentrixGetRun(id);
        setActive(next);
        setRuns((prev) => prev.map((r) => (r.id === id ? { ...r, ...next } : r)));
      } catch {
        /* ignore */
      }
    }, 2000);
    return () => window.clearInterval(t);
  }, [active?.id, active?.status]);

  const events = active?.events || [];

  return (
    <div
      className="flex flex-col h-full min-h-[180px] rounded-lg border border-slate-200 bg-white"
      data-testid="workspace-mentrix-timeline"
    >
      <div className="flex items-center justify-between gap-2 border-b border-slate-100 px-3 py-1.5">
        <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          <Activity className="h-3.5 w-3.5 text-teal-700" />
          Agent timeline
        </span>
        <div className="flex items-center gap-2">
          <Link to="/mentrix" className="text-[11px] text-teal-700 hover:underline">
            Open Mentrix
          </Link>
          <button
            type="button"
            onClick={() => void refresh()}
            className="inline-flex items-center gap-1 rounded border border-slate-200 px-1.5 py-0.5 text-[11px] text-slate-600"
            data-testid="workspace-timeline-refresh"
          >
            <RefreshCw className={`h-3 w-3 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {workspaceRoot ? (
        <p className="px-3 pt-1.5 text-[10px] font-mono text-slate-400 truncate" title={workspaceRoot}>
          workspace: {workspaceRoot}
        </p>
      ) : null}

      {error ? (
        <p className="px-3 py-2 text-xs text-red-600" role="alert">
          {error}
        </p>
      ) : null}

      <div className="flex flex-1 min-h-0">
        <ul
          className="w-36 shrink-0 overflow-auto border-r border-slate-100 py-1"
          data-testid="workspace-timeline-runs"
        >
          {loading && runs.length === 0 ? (
            <li className="px-2 py-3 text-[11px] text-slate-500 flex items-center gap-1">
              <Loader2 className="h-3 w-3 animate-spin" /> Loading…
            </li>
          ) : runs.length === 0 ? (
            <li className="px-2 py-3 text-[11px] text-slate-500">No Mentrix runs yet.</li>
          ) : (
            runs.map((r) => (
              <li key={r.id}>
                <button
                  type="button"
                  onClick={() => void loadRun(r.id)}
                  className={`w-full text-left px-2 py-1.5 text-[11px] hover:bg-slate-50 ${
                    active?.id === r.id ? "bg-teal-50 text-teal-900" : "text-slate-700"
                  }`}
                  data-testid={`workspace-timeline-run-${r.id}`}
                >
                  <div className="font-medium truncate">
                    #{r.id} · {r.status || "?"}
                  </div>
                  <div className="truncate text-slate-500">{r.goal || r.mode || "run"}</div>
                </button>
              </li>
            ))
          )}
        </ul>

        <ul className="flex-1 overflow-auto p-2 space-y-1.5" data-testid="workspace-timeline-events">
          {!active ? (
            <li className="text-xs text-slate-500 p-2">Select a run to view events.</li>
          ) : events.length === 0 ? (
            <li className="text-xs text-slate-500 p-2">
              Run #{active.id} · {active.status || "—"} — no events yet.
            </li>
          ) : (
            events.map((ev, i) => (
              <li
                key={ev.sequence_id ?? i}
                className="rounded bg-slate-50 px-2 py-1.5 text-xs"
                data-testid="workspace-timeline-event"
              >
                <div className="font-mono text-[10px] text-teal-800">
                  {ev.sequence_id != null ? `#${ev.sequence_id} · ` : ""}
                  {ev.agent || "mentrix"}
                  {ev.phase ? ` · ${ev.phase}` : ""}
                  {ev.event ? ` · ${ev.event}` : ""}
                  {ev.next_step ? ` → ${ev.next_step}` : ""}
                </div>
                {ev.message ? <div className="text-slate-700 mt-0.5">{ev.message}</div> : null}
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}
