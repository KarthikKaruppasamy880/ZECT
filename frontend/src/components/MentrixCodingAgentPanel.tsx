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
  codingAgentListPlans,
  codingAgentSavePlan,
  askQuestion,
  generatePlan,
  mentrixStartRun,
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
  onTestOutput?: (text: string) => void;
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

type Tab = "ask" | "plan" | "agent" | "history";

export default function MentrixCodingAgentPanel({
  workspaceRoot,
  model = "gpt-4o-mini",
  onModelChange,
  onOpenPath,
  onFilesChanged,
  onTestOutput,
  initialGoal = "",
  initialSessionId = null,
  projectId = null,
  workItemId = null,
  roots = [],
}: Props) {
  const [tab, setTab] = useState<Tab>("agent");
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
            className={`rounded px-2 py-0.5 text-[10px] ${tab === "ask" ? "bg-teal-700 text-white" : "text-slate-600"}`}
            data-testid="mentrix-coding-agent-ask-tab"
            onClick={() => setTab("ask")}
          >
            ASK
          </button>
          <button
            type="button"
            className={`rounded px-2 py-0.5 text-[10px] ${tab === "plan" ? "bg-teal-700 text-white" : "text-slate-600"}`}
            data-testid="mentrix-coding-agent-plan-tab"
            onClick={() => setTab("plan")}
          >
            PLAN
          </button>
          <button
            type="button"
            className={`rounded px-2 py-0.5 text-[10px] ${tab === "agent" ? "bg-teal-700 text-white" : "text-slate-600"}`}
            data-testid="mentrix-coding-agent-mission-tab"
            onClick={() => setTab("agent")}
          >
            AGENT
            <span className="ml-0.5 font-normal opacity-80">Ship/PR</span>
          </button>
          <button
            type="button"
            className={`rounded px-2 py-0.5 text-[10px] ${tab === "history" ? "bg-teal-700 text-white" : "text-slate-600"}`}
            data-testid="mentrix-coding-agent-history-tab"
            onClick={() => setTab("history")}
          >
            HISTORY
            <span className="ml-0.5 font-normal opacity-80">Implement</span>
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
      {tab === "ask" ? (
        <AskPane
          workspaceRoot={workspaceRoot}
          model={chatModel}
          workItemId={workItemId}
          projectId={projectId}
          repoId={roots[0]?.id ?? null}
          onCreatePlan={() => setTab("plan")}
        />
      ) : tab === "plan" ? (
        <PlanPane
          goalSeed={initialGoal}
          workItemId={workItemId}
          projectId={projectId}
          roots={roots}
          workspaceRoot={workspaceRoot}
          model={chatModel}
          onApproved={() => setTab("agent")}
        />
      ) : tab === "history" ? (
        <HistoryPane
          workspaceRoot={workspaceRoot}
          chatModel={chatModel}
          onOpenPath={onOpenPath}
          onFilesChanged={onFilesChanged}
          initialGoal={initialGoal}
          initialSessionId={initialSessionId}
        />
      ) : (
        <MissionPane
          goalSeed={initialGoal}
          projectId={projectId}
          workItemId={workItemId}
          roots={roots}
          workspaceRoot={workspaceRoot}
          onOpenPath={onOpenPath}
          onFilesChanged={onFilesChanged}
          onTestOutput={onTestOutput}
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
  workspaceRoot,
  onOpenPath,
  onFilesChanged,
  onTestOutput,
}: {
  goalSeed: string;
  projectId?: number | null;
  workItemId?: number | null;
  roots: CodingAgentMissionRoot[];
  workspaceRoot: string;
  onOpenPath?: (path: string) => void;
  onFilesChanged?: (paths: string[]) => void;
  onTestOutput?: (text: string) => void;
}) {
  const [goal, setGoal] = useState(goalSeed);
  const [patchesJson, setPatchesJson] = useState("");
  const [mission, setMission] = useState<CodingAgentMission | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDiff, setShowDiff] = useState(false);
  const [shipNote, setShipNote] = useState<string | null>(null);

  useEffect(() => {
    if (!mission?.tests) return;
    const blob = JSON.stringify(mission.tests, null, 2);
    try {
      localStorage.setItem("zect_ws_last_test_log", blob);
    } catch {
      /* ignore */
    }
    onTestOutput?.(blob);
  }, [mission, onTestOutput]);

  const run = async (fn: () => Promise<CodingAgentMission>) => {
    setBusy(true);
    setError(null);
    try {
      const next = await fn();
      if (next.mission_created === false || next.phase === "synced") {
        setMission(null);
        setError(next.message || "Pulled authorized roots. Lattice is STALE. No coding mission started.");
        return;
      }
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
          placeholder="Describe the change. Approve &amp; Build implements it in a worktree, then this tab ships the PR. Pull-latest on clones does not start a mission."
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
          Approve & Build
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
        <a
          href="/review"
          className="rounded border border-slate-300 px-2 py-1.5 text-xs text-slate-700"
          data-testid="mentrix-coding-agent-review"
        >
          Review
        </a>
        <button
          type="button"
          disabled={busy || !mission || !mission.review || mission.review.passed !== false}
          onClick={() => mission && void run(() => codingAgentRetryMission(mission.id))}
          className="rounded border border-slate-300 px-2 py-1.5 text-xs disabled:opacity-40"
          data-testid="mentrix-coding-agent-fix-findings"
        >
          Fix findings
        </button>
        <button
          type="button"
          disabled={busy || !mission}
          onClick={async () => {
            if (!mission) return;
            setBusy(true);
            setShipNote(null);
            try {
              const run = await mentrixStartRun(
                mission.goal || goal,
                "upgrade",
                "",
                workspaceRoot,
                {
                  work_item_id: workItemId,
                  coding_mission_id: mission.id,
                },
              );
              const id = run?.id;
              setShipNote(`Delivery run ${id} — no auto-merge. Open Mentrix Runs.`);
              window.location.assign(`/mentrix?run=${encodeURIComponent(String(id || ""))}`);
            } catch (e) {
              const msg = e instanceof Error ? e.message : "Prepare PR failed";
              if (/duplicate_delivery_run/i.test(msg)) {
                setError("A Delivery run already exists for this WorkItem and mission. Open Mentrix Runs — do not start a second pipeline.");
              } else {
                setError(msg);
              }
            } finally {
              setBusy(false);
            }
          }}
          className="rounded bg-indigo-700 px-2 py-1.5 text-xs text-white disabled:opacity-40"
          data-testid="mentrix-coding-agent-prepare-pr"
        >
          Prepare PR
        </button>
      </div>
      {shipNote ? <p className="px-3 pb-2 text-[10px] text-indigo-700">{shipNote}</p> : null}
    </div>
  );
}

function ContextUsedStrip({ used }: { used?: { knowledge?: boolean; lattice_hits?: number; lattice_indexed?: boolean; blueprint?: boolean } | null }) {
  if (!used) return null;
  const lattice = used.lattice_indexed
    ? used.lattice_hits
      ? `Lattice ${used.lattice_hits} hits`
      : "Lattice indexed"
    : "Lattice NOT INDEXED";
  return (
    <p className="mt-1 text-[10px] text-slate-500" data-testid="mentrix-coding-agent-context-used">
      Context used · {lattice}
      {used.knowledge ? " · Knowledge" : ""}
      {used.blueprint ? " · Blueprint" : ""}
    </p>
  );
}

function AskPane({
  workspaceRoot,
  model,
  workItemId,
  projectId,
  repoId,
  onCreatePlan,
}: {
  workspaceRoot: string;
  model: string;
  workItemId?: number | null;
  projectId?: number | null;
  repoId?: number | null;
  onCreatePlan: () => void;
}) {
  const [q, setQ] = useState("");
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [contextUsed, setContextUsed] = useState<Parameters<typeof ContextUsedStrip>[0]["used"]>(null);
  void workspaceRoot;

  const ask = async () => {
    const question = q.trim();
    if (!question) return;
    setBusy(true);
    setError(null);
    try {
      const res = await askQuestion(
        question,
        undefined,
        repoId ?? undefined,
        model,
        projectId ?? undefined,
      );
      setAnswer(res.answer || "");
      setContextUsed(res.context_used || null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ask failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col p-2 text-xs" data-testid="mentrix-coding-agent-ask">
      <p className="text-[10px] text-slate-500">ASK is Q&amp;A only — this path never edits files. Use PLAN → Approve &amp; Build or Implement chat to change code.</p>
      <textarea
        value={q}
        onChange={(e) => setQ(e.target.value)}
        className="mt-1 min-h-[4rem] rounded border border-slate-200 px-2 py-1"
        placeholder="Search or explain this workspace…"
        data-testid="mentrix-coding-agent-ask-input"
      />
      <div className="mt-2 flex gap-1">
        <button
          type="button"
          disabled={busy || !q.trim()}
          onClick={() => void ask()}
          className="rounded bg-teal-700 px-2 py-1 text-white disabled:opacity-40"
          data-testid="mentrix-coding-agent-ask-send"
        >
          {busy ? "Asking…" : "Ask"}
        </button>
        <button
          type="button"
          onClick={onCreatePlan}
          className="rounded border border-slate-300 px-2 py-1"
          data-testid="mentrix-coding-agent-ask-create-plan"
        >
          Create Plan
        </button>
      </div>
      {error ? <p className="mt-1 text-rose-600">{error}</p> : null}
      <ContextUsedStrip used={contextUsed} />
      {answer ? (
        <pre className="mt-2 flex-1 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-[11px]" data-testid="mentrix-coding-agent-ask-answer">
          {answer}
        </pre>
      ) : null}
      <p className="mt-1 text-[10px] text-slate-400">WorkItem {workItemId ?? "—"} · zero edits</p>
    </div>
  );
}

function PlanPane({
  goalSeed,
  workItemId,
  projectId,
  roots,
  workspaceRoot,
  model,
  onApproved,
}: {
  goalSeed: string;
  workItemId?: number | null;
  projectId?: number | null;
  roots: CodingAgentMissionRoot[];
  workspaceRoot: string;
  model: string;
  onApproved: () => void;
}) {
  const [goal, setGoal] = useState(goalSeed);
  const [markdown, setMarkdown] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const key = String(workItemId || "local");

  const [contextUsed, setContextUsed] = useState<Parameters<typeof ContextUsedStrip>[0]["used"]>(null);

  const save = async () => {
    if (!markdown.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await codingAgentSavePlan({
        work_item_or_run: key,
        title: "coding",
        markdown,
        meta: { workspace: workspaceRoot },
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const revise = async () => {
    const g = goal.trim();
    if (!g) return;
    setBusy(true);
    setError(null);
    try {
      const res = await generatePlan(
        g,
        undefined,
        undefined,
        roots[0]?.id,
        model,
        projectId ?? undefined,
      );
      setMarkdown(res.plan || "");
      setContextUsed(res.context_used || null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Revise failed");
    } finally {
      setBusy(false);
    }
  };

  const approveAndBuild = async () => {
    if (!markdown.trim()) {
      setError("Save a PLAN.md before Approve & Build");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await codingAgentSavePlan({ work_item_or_run: key, title: "coding", markdown });
      const mission = await codingAgentCreateMission({
        goal: goal.trim() || "Approved PLAN",
        project_id: projectId,
        work_item_id: workItemId,
        roots,
        plan: markdown,
        workspace_parent: workspaceRoot,
        propose_if_empty: true,
      });
      if (mission.phase === "awaiting_plan_approval") {
        await codingAgentApprovePlan(mission.id);
      }
      onApproved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approve & Build failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col p-2 text-xs" data-testid="mentrix-coding-agent-plan-mode">
      <p className="text-[10px] text-slate-500">PLAN.md is scratch in .zect/plans (gitignored). Approve &amp; Build starts the Mentrix implementer in an isolated worktree (same tool loop as Implement chat). Zero edits until then.</p>
      <input
        value={goal}
        onChange={(e) => setGoal(e.target.value)}
        className="mt-1 rounded border border-slate-200 px-2 py-1"
        placeholder="Goal"
        data-testid="mentrix-coding-agent-plan-goal"
      />
      <textarea
        value={markdown}
        onChange={(e) => setMarkdown(e.target.value)}
        className="mt-1 min-h-[8rem] flex-1 rounded border border-slate-200 px-2 py-1 font-mono text-[11px]"
        placeholder="## Plan"
        data-testid="mentrix-coding-agent-plan-md"
      />
      {error ? <p className="text-rose-600">{error}</p> : null}
      <ContextUsedStrip used={contextUsed} />
      <div className="mt-2 flex flex-wrap gap-1">
        <button type="button" disabled={busy} onClick={() => void save()} className="rounded border border-slate-300 px-2 py-1" data-testid="mentrix-coding-agent-save-plan">
          Save Plan
        </button>
        <button type="button" disabled={busy} onClick={() => void revise()} className="rounded border border-slate-300 px-2 py-1" data-testid="mentrix-coding-agent-revise-plan">
          Revise
        </button>
        <button type="button" disabled={busy} onClick={() => void approveAndBuild()} className="rounded bg-teal-700 px-2 py-1 text-white" data-testid="mentrix-coding-agent-approve-build">
          Approve &amp; Build
        </button>
      </div>
    </div>
  );
}

function HistoryPane({
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
  const [rows, setRows] = useState<Array<{ id: string; markdown?: string; title?: string }>>([]);
  useEffect(() => {
    void codingAgentListPlans()
      .then((r) => setRows(r.plans || []))
      .catch(() => setRows([]));
  }, []);
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden" data-testid="mentrix-coding-agent-history">
      <div className="max-h-[40%] overflow-auto p-2 text-xs">
        <p className="text-[10px] text-slate-500">Saved PLAN.md versions. Chat below is Implement (live tool loop). Companion never edits code. Ship/PR is the AGENT tab.</p>
        {rows.length === 0 ? <p className="mt-2 text-slate-400">No saved plans yet.</p> : null}
        <ul className="mt-2 space-y-2">
          {rows.map((p) => (
            <li key={p.id} className="rounded border border-slate-100 p-2">
              <p className="font-semibold">{p.title || p.id}</p>
              <pre className="max-h-24 overflow-auto whitespace-pre-wrap text-[10px] text-slate-600">{p.markdown}</pre>
            </li>
          ))}
        </ul>
      </div>
      <div className="min-h-0 flex-1 overflow-hidden border-t border-slate-100">
        <ChatPane
          workspaceRoot={workspaceRoot}
          chatModel={chatModel}
          onOpenPath={onOpenPath}
          onFilesChanged={onFilesChanged}
          initialGoal={initialGoal}
          initialSessionId={initialSessionId}
        />
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
            Chat is Implement: native tool loop in this workspace. AGENT is Ship/PR (worktrees, sibling gates, git approval). Companion does not write code.
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
