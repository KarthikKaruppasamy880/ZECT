import { useEffect, useState } from "react";
import {
  mentrixLongRunningCancel,
  mentrixLongRunningGet,
  mentrixLongRunningPause,
  mentrixLongRunningResume,
  mentrixLongRunningStart,
  mentrixLongRunningTick,
} from "@/lib/api";

type Props = {
  workItemId: number;
  title?: string;
};

/** Developer Workspace / Work Items run view — no chain-of-thought. */
export default function LongRunningRunPanel({ workItemId, title }: Props) {
  const [runId, setRunId] = useState("");
  const [run, setRun] = useState<any>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!runId) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const data = await mentrixLongRunningGet(runId);
        if (!cancelled) setRun(data);
      } catch (e: any) {
        if (!cancelled) setError(e?.message || "Failed to load run");
      }
    };
    poll();
    const t = setInterval(poll, 2500);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [runId]);

  const start = async () => {
    setBusy(true);
    setError("");
    try {
      const out = await mentrixLongRunningStart({
        work_item_id: workItemId,
        operation_count: 12,
        autonomy: "L1",
        model_profile: "QUALITY",
      });
      setRunId(out.run_id);
      setRun(out);
    } catch (e: any) {
      setError(e?.message || "Start failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-4 rounded-lg border border-slate-200 p-4" data-testid="long-running-run-panel">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">Long-running Mentrix run</h2>
          <p className="text-xs text-slate-500">{title || `WorkItem #${workItemId}`}</p>
        </div>
        {!runId && (
          <button
            type="button"
            disabled={busy}
            onClick={start}
            className="rounded bg-teal-700 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
          >
            Start synthetic run
          </button>
        )}
      </div>
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
      {run && (
        <div className="mt-3 space-y-2 text-xs text-slate-700">
          <p>
            <span className="font-medium uppercase tracking-wide">{run.status}</span>
            {" · "}
            Ops {run.operations_completed}/{run.operations_total}
            {" · "}
            Current {run.current_operation_id || "—"}
          </p>
          <p>
            Model {run.state?.actual_model || run.state?.model_profile || "—"} · Provider{" "}
            {run.state?.provider || "—"}
          </p>
          <p>
            Resume {run.resume_operation || "—"} · Lease {run.worker_id || "idle"}
          </p>
          <div className="flex flex-wrap gap-2 pt-1">
            <button type="button" className="rounded border px-2 py-1" onClick={() => mentrixLongRunningPause(runId).then(setRun)}>
              Pause
            </button>
            <button type="button" className="rounded border px-2 py-1" onClick={() => mentrixLongRunningResume(runId).then(setRun)}>
              Resume
            </button>
            <button
              type="button"
              className="rounded border px-2 py-1"
              onClick={() => mentrixLongRunningTick(runId, { worker_id: "ui", max_ops: 5 }).then(setRun)}
            >
              Tick 5
            </button>
            <button type="button" className="rounded border px-2 py-1 text-red-700" onClick={() => mentrixLongRunningCancel(runId).then(setRun)}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
