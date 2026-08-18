/**
 * Mentrix Coding Agent — production mission lifecycle plus interactive chat.
 * Companion does not edit code; this panel is the canonical edit/test/review/git loop.
 */
import { useEffect, useRef, useState } from "react";
import {
  Bot,
  Check,
  GitCompare,
  Loader2,
  RotateCcw,
  Send,
  Square,
  X,
} from "lucide-react";
import ModelSelector from "@/components/ModelSelector";
import {
  codingAgentApprove,
  codingAgentApproveGit,
  codingAgentApprovePlan,
  codingAgentCancel,
  codingAgentCancelMission,
  codingAgentCreateMission,
  codingAgentCreateSession,
  codingAgentResumeMission,
  codingAgentRetryMission,
  codingAgentStream,
  type CodingAgentMission,
  type CodingAgentMissionRoot,
  type MentrixCodingAgentEvent,
} from "@/lib/api";

type Props = {
  workspaceRoot: string;
  model?: string;
  onModelChange?: (id: string) => void;
  onOpenPath?: (relativeOrAbsolutePath: string) => void;
  onFilesChanged?: (paths: string[]) => void;
  initialGoal?: string;
  initialSessionId?: string | null;
  projectId?: number | null;
  workItemId?: number | null;
  roots?: CodingAgentMissionRoot[];
};

type Line = {
  id: string;
  kind: "user" | "event";
  text: string;
  event?: string;
  path?: string;
  actionId?: string;
};

type Tab = "mission" | "chat";

export default function MentrixCodingAgentPanel({
  workspaceRoot,
  model = "gpt-4o-mini",
  onModelChange,
  onOpenPath,
  onFilesChanged,
  initialGoal = "",
  initialSessionId = null,
  projectId = null,
  workItemId = null,
  roots = [],
}: Props) {
  const [tab, setTab] = useState<Tab>(initialSessionId ? "chat" : "mission");
  const [chatModel, setChatModel] = useState(model);

  useEffect(() => {
    setChatModel(model);
  }, [model]);

  return (
    <div
      className="flex h-full min-h-[200px] flex-col rounded-lg border border-slate-200 bg-white"
      data-testid="mentrix-coding-agent-panel"
    >
      <div className="flex items-center justify-between gap-2 border-b border-slate-100 px-3 py-2">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-800">
          <Bot className="h-3.5 w-3.5 text-teal-700" />
          Mentrix Coding Agent
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            className={`rounded px-2 py-0.5 text-[10px] ${tab === "mission" ? "bg-teal-700 text-white" : "text-slate-600"}`}
            data-testid="mentrix-coding-agent-mission-tab"
            onClick={() => setTab("mission")}
          >
            Mission
          </button>
          <button
            type="button"
            className={`rounded px-2 py-0.5 text-[10px] ${tab === "chat" ? "bg-teal-700 text-white" : "text-slate-600"}`}
            data-testid="mentrix-coding-agent-chat-tab"
            onClick={() => setTab("chat")}
          >
            Chat
          </button>
          <div className="origin-right scale-90">
            <ModelSelector
              value={chatModel}
              onChange={(id) => {
                setChatModel(id);
                onModelChange?.(id);
              }}
              compact
            />
          </div>
        </div>
      </div>
      {tab === "mission" ? (
        <MissionPane
          goalSeed={initialGoal}
          projectId={projectId}
          workItemId={workItemId}
          roots={roots}
          onOpenPath={onOpenPath}
          onFilesChanged={onFilesChanged}
        />
      ) : (
        <ChatPane
          workspaceRoot={workspaceRoot}
          chatModel={chatModel}
          onOpenPath={onOpenPath}
          onFilesChanged={onFilesChanged}
          initialGoal={initialGoal}
          initialSessionId={initialSessionId}
        />
      )}
    </div>
  );
}

function MissionPane({
  goalSeed,
  projectId,
  workItemId,
  roots,
  onOpenPath,
  onFilesChanged,
}: {
  goalSeed: string;
  projectId?: number | null;
  workItemId?: number | null;
  roots: CodingAgentMissionRoot[];
  onOpenPath?: (path: string) => void;
  onFilesChanged?: (paths: string[]) => void;
}) {
  const [goal, setGoal] = useState(goalSeed);
  const [patchesJson, setPatchesJson] = useState("");
  const [mission, setMission] = useState<CodingAgentMission | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDiff, setShowDiff] = useState(false);

  const run = async (fn: () => Promise<CodingAgentMission>) => {
    setBusy(true);
    setError(null);
    try {
      const next = await fn();
      setMission(next);
      const files = next.files || [];
      if (files.length) onFilesChanged?.(files);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Mission request failed");
    } finally {
      setBusy(false);
    }
  };

  const start = async () => {
    const g = goal.trim();
    if (!g) return;
    if (!roots.length && projectId == null) {
      setError("Authorized project roots required");
      return;
    }
    let patches: Record<string, Array<Record<string, string>>> | undefined;
    if (patchesJson.trim()) {
      try {
        patches = JSON.parse(patchesJson) as Record<string, Array<Record<string, string>>>;
      } catch {
        setError("Deterministic patches JSON is invalid");
        return;
      }
    }
    await run(() =>
      codingAgentCreateMission({
        goal: g,
        project_id: projectId,
        work_item_id: workItemId,
        roots,
        patches_by_repo: patches,
      }),
    );
  };

  const phase = mission?.phase || "idle";
  const blockers = mission?.blockers || [];
  const reviewFindings = mission?.review?.findings || [];
  const evidence = mission?.evidence || mission?.events || [];
  const ciStatus = String(mission?.ci?.status || "—");
  const prNote = String(mission?.pr?.url || mission?.pr?.note || ciStatus);

  return (
    <div className="flex min-h-0 flex-1 flex-col text-xs">
      <div className="flex items-center justify-between gap-2 border-b border-slate-50 px-3 py-1.5">
        <span className="text-slate-500" data-testid="mentrix-coding-agent-phase">
          phase · {phase}
        </span>
        <span className="text-[10px] text-slate-400" data-testid="mentrix-coding-agent-status">
          {mission?.status || "idle"} · no auto-merge
        </span>
      </div>

      <div className="min-h-0 flex-1 space-y-2 overflow-auto px-3 py-2">
        <label className="block text-[10px] uppercase text-slate-400">Goal</label>
        <textarea
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          disabled={busy}
          placeholder="Describe the change. PLAN must be approved before worktrees or edits."
          className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-xs"
          rows={2}
          data-testid="mentrix-coding-agent-mission-goal"
        />
        <details className="rounded border border-slate-100 px-2 py-1">
          <summary
            className="cursor-pointer text-[10px] text-slate-500"
            data-testid="mentrix-coding-agent-patches-toggle"
          >
            Deterministic patches (JSON)
          </summary>
          <textarea
            value={patchesJson}
            onChange={(e) => setPatchesJson(e.target.value)}
            className="mt-1 w-full rounded border border-slate-200 px-2 py-1 font-mono text-[10px]"
            rows={4}
            data-testid="mentrix-coding-agent-patches"
            placeholder='{"1":[{"path":"calc.py","old":"return a - b","new":"return a + b"}]}'
          />
        </details>

        <section data-testid="mentrix-coding-agent-approvals">
          <h4 className="text-[10px] font-semibold uppercase text-slate-500">Approvals</h4>
          <p className="text-slate-600">
            plan {mission?.approvals?.plan ? "approved" : "pending"} · git{" "}
            {mission?.approvals?.git ? "approved" : "pending"}
          </p>
        </section>

        <section data-testid="mentrix-coding-agent-plan">
          <h4 className="text-[10px] font-semibold uppercase text-slate-500">Plan</h4>
          <pre className="max-h-32 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-[11px] text-slate-700">
            {mission?.plan || "Start a mission to generate PLAN."}
          </pre>
        </section>

        <section data-testid="mentrix-coding-agent-repos">
          <h4 className="text-[10px] font-semibold uppercase text-slate-500">Repos</h4>
          {(mission?.repos || roots).length === 0 ? (
            <p className="text-slate-500">No authorized roots on this project.</p>
          ) : (
            <ul className="space-y-1">
              {(mission?.repos?.length
                ? mission.repos
                : roots.map((r) => ({
                    label: r.label,
                    repository_id: r.id,
                    branch: "",
                    test_status: undefined as string | undefined,
                  }))
              ).map((r, i) => (
                <li key={`${r.repository_id || r.label}-${i}`} className="font-mono text-[11px] text-slate-700">
                  {r.label || r.repository_id}
                  {r.branch ? ` · ${r.branch}` : ""}
                  {r.test_status ? ` · tests ${r.test_status}` : ""}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section data-testid="mentrix-coding-agent-files">
          <h4 className="text-[10px] font-semibold uppercase text-slate-500">Files</h4>
          <p className="font-mono text-[11px] text-slate-700">{(mission?.files || []).join(", ") || "—"}</p>
        </section>

        <section data-testid="mentrix-coding-agent-commands">
          <h4 className="text-[10px] font-semibold uppercase text-slate-500">Commands</h4>
          <p className="font-mono text-[11px] text-slate-700">{(mission?.commands || []).slice(-3).join(" · ") || "—"}</p>
        </section>

        <section data-testid="mentrix-coding-agent-tests">
          <h4 className="text-[10px] font-semibold uppercase text-slate-500">Tests</h4>
          <p className="text-slate-700">
            {mission?.tests && Object.keys(mission.tests).length
              ? Object.entries(mission.tests)
                  .map(([id, st]) => `${id}:${st || "unknown"}`)
                  .join(" · ")
              : "—"}
          </p>
        </section>

        <section data-testid="mentrix-coding-agent-blockers">
          <h4 className="text-[10px] font-semibold uppercase text-slate-500">Blockers</h4>
          <p className={blockers.length ? "text-rose-700" : "text-slate-500"}>
            {blockers.length ? blockers.join(" · ") : "none"}
          </p>
        </section>

        <section data-testid="mentrix-coding-agent-review">
          <h4 className="text-[10px] font-semibold uppercase text-slate-500">Ultra Review</h4>
          <p className="text-slate-700">
            {mission?.review?.passed === true
              ? "passed"
              : mission?.review?.passed === false
                ? `blocked · ${mission.review.critical_findings || 0} critical`
                : "—"}
          </p>
          {reviewFindings.slice(0, 3).map((f, i) => (
            <p key={i} className="text-[11px] text-slate-600">
              {f.severity}: {f.message}
            </p>
          ))}
        </section>

        <section data-testid="mentrix-coding-agent-pr">
          <h4 className="text-[10px] font-semibold uppercase text-slate-500">PR</h4>
          <p className="text-slate-700">{prNote}</p>
        </section>

        <section data-testid="mentrix-coding-agent-ci">
          <h4 className="text-[10px] font-semibold uppercase text-slate-500">CI</h4>
          <p className="text-slate-700">{ciStatus}</p>
        </section>

        {showDiff ? (
          <section data-testid="mentrix-coding-agent-diff">
            <h4 className="text-[10px] font-semibold uppercase text-slate-500">Diff</h4>
            <pre className="max-h-40 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 font-mono text-[10px]">
              {(mission?.repos || []).map((r) => r.diff).filter(Boolean).join("\n\n") || "No uncommitted diff."}
            </pre>
          </section>
        ) : null}

        <section data-testid="mentrix-coding-agent-evidence">
          <h4 className="text-[10px] font-semibold uppercase text-slate-500">Evidence</h4>
          <ul className="max-h-24 overflow-auto text-[11px] text-slate-600">
            {evidence.slice(-8).map((ev, i) => (
              <li key={`${ev.at}-${i}`}>
                {ev.event}: {ev.message}
              </li>
            ))}
          </ul>
        </section>
      </div>

      {error ? (
        <p className="px-3 text-[11px] text-rose-600" data-testid="mentrix-coding-agent-error">
          {error}
        </p>
      ) : null}

      <div className="flex flex-wrap items-center gap-1 border-t border-slate-100 p-2">
        <button
          type="button"
          onClick={() => void start()}
          disabled={busy || !goal.trim()}
          className="inline-flex items-center gap-1 rounded-md bg-teal-700 px-2 py-1.5 text-xs text-white disabled:opacity-40"
          data-testid="mentrix-coding-agent-start-mission"
        >
          {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <Send className="h-3 w-3" />}
          Start
        </button>
        <button
          type="button"
          disabled={busy || !mission || mission.phase !== "awaiting_plan_approval"}
          onClick={() => mission && void run(() => codingAgentApprovePlan(mission.id))}
          className="rounded border border-slate-300 px-2 py-1.5 text-xs disabled:opacity-40"
          data-testid="mentrix-coding-agent-approve-plan"
        >
          Approve PLAN
        </button>
        <button
          type="button"
          disabled={busy || !mission || mission.phase !== "awaiting_git_approval"}
          onClick={() => mission && void run(() => codingAgentApproveGit(mission.id))}
          className="rounded border border-slate-300 px-2 py-1.5 text-xs disabled:opacity-40"
          data-testid="mentrix-coding-agent-approve-git"
        >
          Approve git
        </button>
        <button
          type="button"
          disabled={busy || !mission || mission.phase === "cancelled"}
          onClick={() => mission && void run(() => codingAgentCancelMission(mission.id))}
          className="inline-flex items-center gap-1 rounded border border-slate-300 px-2 py-1.5 text-xs disabled:opacity-40"
          data-testid="mentrix-coding-agent-cancel-mission"
        >
          <Square className="h-3 w-3" /> Cancel
        </button>
        <button
          type="button"
          disabled={busy || !mission}
          onClick={() => mission && void run(() => codingAgentResumeMission(mission.id))}
          className="rounded border border-slate-300 px-2 py-1.5 text-xs disabled:opacity-40"
          data-testid="mentrix-coding-agent-resume"
        >
          Resume
        </button>
        <button
          type="button"
          disabled={busy || !mission}
          onClick={() => mission && void run(() => codingAgentRetryMission(mission.id))}
          className="inline-flex items-center gap-1 rounded border border-slate-300 px-2 py-1.5 text-xs disabled:opacity-40"
          data-testid="mentrix-coding-agent-retry"
        >
          <RotateCcw className="h-3 w-3" /> Retry
        </button>
        <button
          type="button"
          disabled={!mission}
          onClick={() => {
            setShowDiff((v) => !v);
            const first = mission?.files?.[0];
            if (first) onOpenPath?.(first);
          }}
          className="inline-flex items-center gap-1 rounded border border-slate-300 px-2 py-1.5 text-xs disabled:opacity-40"
          data-testid="mentrix-coding-agent-open-diff"
        >
          <GitCompare className="h-3 w-3" /> Open diff
        </button>
      </div>
    </div>
  );
}

function ChatPane({
  workspaceRoot,
  chatModel,
  onOpenPath,
  onFilesChanged,
  initialGoal,
  initialSessionId,
}: {
  workspaceRoot: string;
  chatModel: string;
  onOpenPath?: (path: string) => void;
  onFilesChanged?: (paths: string[]) => void;
  initialGoal: string;
  initialSessionId: string | null;
}) {
  const [goal, setGoal] = useState(initialGoal);
  const [sessionId, setSessionId] = useState<string | null>(initialSessionId);
  const [status, setStatus] = useState("idle");
  const [lines, setLines] = useState<Line[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const writtenRef = useRef<string[]>([]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  useEffect(() => {
    if (!initialSessionId) return;
    setSessionId(initialSessionId);
    void attachStream(initialSessionId, 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialSessionId]);

  const pushLine = (line: Omit<Line, "id">) => {
    setLines((prev) => [...prev, { ...line, id: `${Date.now()}-${Math.random()}` }]);
  };

  const handleEvent = (ev: MentrixCodingAgentEvent) => {
    if (!ev?.event || ev.event === "ping") return;
    setStatus(ev.event);
    const path = ev.data?.path as string | undefined;
    const actionId = ev.data?.action_id as string | undefined;
    pushLine({
      kind: "event",
      text: ev.message || ev.event,
      event: ev.event,
      path,
      actionId,
    });
    if (ev.event === "file_diff" && path) {
      if (!writtenRef.current.includes(path)) writtenRef.current.push(path);
      onFilesChanged?.(writtenRef.current.slice());
      onOpenPath?.(path);
    }
    if (ev.event === "completed" || ev.event === "failed" || ev.event === "cancelled") {
      setBusy(false);
      setStatus(ev.event);
    }
  };

  const attachStream = async (sid: string, after: number) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setBusy(true);
    try {
      await codingAgentStream(sid, {
        after,
        signal: controller.signal,
        onEvent: handleEvent,
      });
    } catch (e) {
      if ((e as Error)?.name === "AbortError") return;
      setError(e instanceof Error ? e.message : "Stream failed");
    } finally {
      setBusy(false);
    }
  };

  const start = async () => {
    const g = goal.trim();
    if (!g || !workspaceRoot) return;
    setError(null);
    writtenRef.current = [];
    pushLine({ kind: "user", text: g });
    setBusy(true);
    try {
      const res = await codingAgentCreateSession({
        goal: g,
        workspace: workspaceRoot,
        model: chatModel,
        auto_approve_edits: true,
      });
      setSessionId(res.id);
      setStatus(res.status || "running");
      setGoal("");
      const after = Math.max(0, ...(res.events || []).map((e) => e.sequence_id || 0));
      for (const ev of res.events || []) handleEvent(ev as MentrixCodingAgentEvent);
      void attachStream(res.id, after);
    } catch (e) {
      setBusy(false);
      setError(e instanceof Error ? e.message : "Failed to start Mentrix Coding Agent");
    }
  };

  const cancel = async () => {
    if (!sessionId) return;
    abortRef.current?.abort();
    try {
      await codingAgentCancel(sessionId);
      setStatus("cancelled");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cancel failed");
    } finally {
      setBusy(false);
    }
  };

  const respondApproval = async (actionId: string, approve: boolean) => {
    if (!sessionId) return;
    try {
      await codingAgentApprove(sessionId, actionId, approve);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approval failed");
    }
  };

  return (
    <>
      <div className="border-b border-slate-50 px-3 py-1 text-[10px] text-slate-400" data-testid="mentrix-coding-agent-chat-status">
        chat · {status}
      </div>
      <div className="flex-1 space-y-2 overflow-auto px-3 py-2 text-xs" data-testid="mentrix-coding-agent-log">
        {lines.length === 0 ? (
          <p className="text-slate-500">
            Chat uses the native tool loop in this workspace. Production missions (PLAN, worktrees, sibling
            blocking, git approval) live on the Mission tab.
          </p>
        ) : (
          lines.map((ln) => (
            <div
              key={ln.id}
              className={`rounded-md px-2 py-1.5 ${
                ln.kind === "user" ? "bg-teal-50 text-teal-900" : "bg-slate-50 text-slate-700"
              }`}
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <span>
                  {ln.event ? <span className="mr-1 text-[10px] uppercase text-slate-400">{ln.event}</span> : null}
                  {ln.text}
                </span>
                {ln.path ? (
                  <button
                    type="button"
                    className="font-mono text-[10px] text-teal-700 underline"
                    onClick={() => onOpenPath?.(ln.path!)}
                  >
                    {ln.path}
                  </button>
                ) : null}
              </div>
              {ln.event === "needs_approval" && ln.actionId ? (
                <div className="mt-1 flex gap-1">
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 rounded bg-emerald-600 px-2 py-0.5 text-[10px] text-white"
                    onClick={() => void respondApproval(ln.actionId!, true)}
                    data-testid="mentrix-coding-agent-approve"
                  >
                    <Check className="h-3 w-3" /> Allow
                  </button>
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 rounded bg-slate-600 px-2 py-0.5 text-[10px] text-white"
                    onClick={() => void respondApproval(ln.actionId!, false)}
                  >
                    <X className="h-3 w-3" /> Deny
                  </button>
                </div>
              ) : null}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
      {error ? (
        <p className="px-3 text-[11px] text-rose-600" data-testid="mentrix-coding-agent-chat-error">
          {error}
        </p>
      ) : null}
      <div className="flex items-center gap-2 border-t border-slate-100 p-2">
        <input
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void start();
            }
          }}
          disabled={busy || !workspaceRoot}
          placeholder={workspaceRoot ? "Describe the change…" : "Set workspace root first"}
          className="flex-1 rounded-md border border-slate-200 px-2 py-1.5 text-xs"
          data-testid="mentrix-coding-agent-input"
        />
        {busy ? (
          <button
            type="button"
            onClick={() => void cancel()}
            className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-2 py-1.5 text-xs"
            data-testid="mentrix-coding-agent-cancel"
          >
            <Square className="h-3 w-3" /> Stop
          </button>
        ) : (
          <button
            type="button"
            onClick={() => void start()}
            disabled={!goal.trim() || !workspaceRoot}
            className="inline-flex items-center gap-1 rounded-md bg-teal-700 px-2 py-1.5 text-xs text-white disabled:opacity-40"
            data-testid="mentrix-coding-agent-send"
          >
            {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <Send className="h-3 w-3" />}
            Run
          </button>
        )}
      </div>
    </>
  );
}
