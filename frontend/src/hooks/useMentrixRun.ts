import { useCallback, useEffect, useRef, useState } from "react";
import {
  mentrixAgents,
  mentrixCancelRun,
  mentrixGetRun,
  mentrixListRuns,
  mentrixRetryRun,
  mentrixStartRun,
} from "@/lib/api";

export const MENTRIX_WORKFLOW_STEPS = [
  { id: "lattice", label: "Lattice" },
  { id: "plan", label: "Plan" },
  { id: "build_gates", label: "Build/Gates" },
  { id: "ultra_review", label: "Ultra Review" },
  { id: "approve", label: "Approve" },
  { id: "pr", label: "PR" },
] as const;

export type MentrixChatMsg = {
  role: "user" | "assistant" | "system";
  text: string;
  meta?: string;
};

export function mentrixWorkflowStepIndex(run: any): number {
  if (!run) return -1;
  if (run.pr_url || run.status === "pr_created") return 5;
  if (run.approved_at || run.status === "approved") return 4;
  const gates = run.gates || run.result?.gates || {};
  const events = run.events || [];
  const phases = new Set(events.map((e: any) => e.phase).filter(Boolean));
  const agents = new Set(events.map((e: any) => e.agent).filter(Boolean));
  if (
    (gates.review_ok != null && run.status !== "awaiting_plan_confirm" && run.status !== "awaiting_batch_confirm") ||
    phases.has("review") ||
    agents.has("reviewer") ||
    run.result?.ultra_review
  ) {
    return 3;
  }
  if (
    run.status !== "awaiting_plan_confirm" &&
    run.status !== "awaiting_batch_confirm" &&
    (gates.lint_ok != null ||
      gates.sandbox_ready != null ||
      phases.has("lint") ||
      phases.has("sandbox") ||
      phases.has("build") ||
      agents.has("builder"))
  ) {
    return 2;
  }
  if (
    run.status === "awaiting_plan_confirm" ||
    run.status === "awaiting_batch_confirm" ||
    phases.has("plan") ||
    phases.has("root_cause") ||
    phases.has("ask") ||
    agents.has("planner")
  ) {
    return 1;
  }
  if (phases.has("lattice") || agents.has("scout") || agents.has("lattice") || phases.has("blueprint")) {
    return 0;
  }
  if (run.status === "running") return 0;
  return -1;
}

export function mentrixEventsToMessages(run: any): MentrixChatMsg[] {
  const msgs: MentrixChatMsg[] = [{ role: "user", text: run.goal, meta: `mode=${run.mode}` }];
  for (const ev of run.events || []) {
    const phase = ev.phase ? ` · ${ev.phase}` : "";
    const progress =
      typeof ev.progress === "number" ? ` · ${Math.round(ev.progress * 100)}%` : "";
    msgs.push({
      role: "assistant",
      text: ev.message || "",
      meta: `${ev.agent || "mentrix"}${phase}${progress}${ev.next_step ? ` → ${ev.next_step}` : ""}`,
    });
  }
  if (run.result?.ask?.answer) {
    msgs.push({
      role: "assistant",
      text: String(run.result.ask.answer).slice(0, 1200),
      meta: "ask",
    });
  }
  if (run.result?.ultra_review?.summary) {
    msgs.push({
      role: "assistant",
      text: `Mentrix Ultra Review: ${run.result.ultra_review.summary}`,
      meta: `score=${run.result.ultra_review.score}`,
    });
  }
  if (run.status) {
    msgs.push({
      role: "system",
      text: `Status: ${run.status}${run.next_step ? ` · next: ${run.next_step}` : ""}`,
    });
  }
  return msgs;
}

/**
 * Mentrix Delivery run state: list refresh, active run, chat messages from events,
 * and 2s polling while status === "running".
 */
export function useMentrixRun() {
  const [agents, setAgents] = useState<any>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [active, setActive] = useState<any>(null);
  const [messages, setMessages] = useState<MentrixChatMsg[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const pollRef = useRef<number | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const refresh = useCallback(async () => {
    try {
      const [a, r] = await Promise.all([mentrixAgents(), mentrixListRuns(15)]);
      setAgents(a);
      setRuns(Array.isArray(r) ? r : []);
    } catch {
      /* ignore */
    }
  }, []);

  const applyRun = useCallback(
    (run: any, opts?: { pollIfRunning?: boolean }) => {
      setActive(run);
      setMessages(mentrixEventsToMessages(run));
      if (opts?.pollIfRunning !== false && run?.status === "running" && run?.id != null) {
        stopPolling();
        pollRef.current = window.setInterval(async () => {
          try {
            const next = await mentrixGetRun(run.id);
            setActive(next);
            setMessages(mentrixEventsToMessages(next));
            if (next.status && next.status !== "running") {
              stopPolling();
              await refresh();
            }
          } catch {
            /* ignore poll errors */
          }
        }, 2000);
      }
    },
    [refresh, stopPolling],
  );

  const startPolling = useCallback(
    (runId: number) => {
      stopPolling();
      pollRef.current = window.setInterval(async () => {
        try {
          const run = await mentrixGetRun(runId);
          setActive(run);
          setMessages(mentrixEventsToMessages(run));
          if (run.status && run.status !== "running") {
            stopPolling();
            await refresh();
          }
        } catch {
          /* ignore poll errors */
        }
      }, 2000);
    },
    [refresh, stopPolling],
  );

  const startRun = useCallback(
    async (
      goal: string,
      mode: string,
      projectKey: string,
      workspace: string,
      opts?: { source_lang?: string; target_lang?: string; repo_id?: number },
    ) => {
      setError("");
      setLoading(true);
      setMessages([{ role: "user", text: goal, meta: `mode=${mode}` }]);
      try {
        const run = await mentrixStartRun(goal, mode, projectKey, workspace, opts);
        applyRun(run);
        await refresh();
        return run;
      } catch (e) {
        setError(e instanceof Error ? e.message : "Run failed");
        throw e;
      } finally {
        setLoading(false);
      }
    },
    [applyRun, refresh],
  );

  const openRun = useCallback(
    async (id: number) => {
      setLoading(true);
      setError("");
      try {
        const run = await mentrixGetRun(id);
        applyRun(run);
        return run;
      } catch (e) {
        setError(e instanceof Error ? e.message : "Load failed");
        throw e;
      } finally {
        setLoading(false);
      }
    },
    [applyRun],
  );

  const cancelRun = useCallback(
    async (id: number) => {
      setLoading(true);
      setError("");
      try {
        stopPolling();
        const run = await mentrixCancelRun(id);
        applyRun(run, { pollIfRunning: false });
        await refresh();
        return run;
      } catch (e) {
        setError(e instanceof Error ? e.message : "Cancel failed");
        throw e;
      } finally {
        setLoading(false);
      }
    },
    [applyRun, refresh, stopPolling],
  );

  const retryRun = useCallback(
    async (id: number) => {
      setLoading(true);
      setError("");
      try {
        stopPolling();
        const run = await mentrixRetryRun(id);
        applyRun(run);
        await refresh();
        return run;
      } catch (e) {
        setError(e instanceof Error ? e.message : "Retry failed");
        throw e;
      } finally {
        setLoading(false);
      }
    },
    [applyRun, refresh, stopPolling],
  );

  useEffect(() => {
    void refresh();
    return () => stopPolling();
  }, [refresh, stopPolling]);

  const gates = active?.gates || active?.result?.gates || {};
  const canApprove =
    Boolean(active) &&
    ["awaiting_approval", "needs_human", "completed"].includes(active.status) &&
    !active.approved_at;
  const canCreatePr = Boolean(active?.approved_at) && !active?.pr_url;
  const canRetry =
    Boolean(active) && ["failed", "cancelled", "needs_human"].includes(active.status);
  const currentPhase =
    [...(active?.events || [])].reverse().find((e: any) => e.phase)?.phase ||
    active?.current_agent ||
    "—";
  const stepIdx = mentrixWorkflowStepIndex(active);

  return {
    agents,
    runs,
    active,
    setActive,
    messages,
    setMessages,
    loading,
    setLoading,
    error,
    setError,
    refresh,
    applyRun,
    startPolling,
    stopPolling,
    startRun,
    openRun,
    cancelRun,
    retryRun,
    gates,
    canApprove,
    canCreatePr,
    canRetry,
    currentPhase,
    stepIdx,
    workflowSteps: MENTRIX_WORKFLOW_STEPS,
  };
}
