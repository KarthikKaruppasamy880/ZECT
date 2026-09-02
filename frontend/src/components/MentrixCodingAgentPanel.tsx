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
import { MentionAutocomplete, MentionContextStrip } from "@/components/MentionComposerAddons";
import { ComposerAttachmentBar } from "@/components/ComposerAttachmentBar";
import { hasMentions } from "@/lib/mentions";
import { canonicalLatticeState, latticeHeaderLabel } from "@/lib/contextUsed";
import { useComposerAttachments, imageFilesFromClipboard } from "@/hooks/useComposerAttachments";
import {
  codingAgentApprove,
  codingAgentApproveGit,
  codingAgentApprovePlan,
  codingAgentCancel,
  codingAgentCancelMission,
  codingAgentCreateMission,
  codingAgentCreateSession,
  codingAgentGetMission,
  codingAgentGetSession,
  codingAgentResolveMentions,
  codingAgentResumeMission,
  codingAgentRetryMission,
  codingAgentStream,
  codingAgentGetPlan,
  codingAgentListPlans,
  codingAgentSavePlan,
  developerAsk,
  developerAskHistory,
  developerPlan,
  getDocumentMarkdown,
  listWorkItemAttachments,
  mentrixStartRun,
  type CodingAgentMission,
  type CodingAgentMissionRoot,
  type ContextPack,
  type DeveloperAskTurn,
  type MentrixCodingAgentEvent,
} from "@/lib/api";
import { WorkItemAttachmentsStrip } from "@/components/WorkItemAttachmentsStrip";

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
  onWorkItemResolved?: (id: number) => void;
  /** A Mission id from the URL, the persisted session or the WorkItem, so the
   *  pane re-attaches to a Mission that is already running instead of
   *  offering to start a new one (finding F4). */
  missionId?: string | null;
  onMissionChanged?: (id: string) => void;
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
  onWorkItemResolved,
  missionId = null,
  onMissionChanged,
}: Props) {
  const [tab, setTab] = useState<Tab>("agent");
  const [chatModel, setChatModel] = useState(model);
  const [handoffMission, setHandoffMission] = useState<CodingAgentMission | null>(null);
  const [askSeed, setAskSeed] = useState<AskToPlanSeed | null>(null);

  useEffect(() => {
    setChatModel(model);
  }, [model]);

  // The seed is delivered once, at the exact mount PlanPane makes when this
  // switch happens (both state updates are batched into the same render).
  // Clearing it right after means a later, unrelated visit to PLAN never
  // silently overwrites the user's own edits with stale ASK content.
  useEffect(() => {
    if (tab === "plan") setAskSeed(null);
  }, [tab]);

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
          roots={roots}
          onCreatePlan={(seed) => {
            setAskSeed(seed);
            setTab("plan");
          }}
          onWorkItemResolved={onWorkItemResolved}
        />
      ) : tab === "plan" ? (
        <PlanPane
          goalSeed={initialGoal}
          askSeed={askSeed}
          workItemId={workItemId}
          projectId={projectId}
          roots={roots}
          workspaceRoot={workspaceRoot}
          model={chatModel}
          onApproved={(mission) => {
            setHandoffMission(mission);
            setTab("agent");
          }}
          onFilesChanged={onFilesChanged}
          onOpenPath={onOpenPath}
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
          seedMission={handoffMission}
          missionId={missionId}
          onMissionChanged={onMissionChanged}
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
  seedMission,
  missionId,
  onMissionChanged,
  onOpenPath,
  onFilesChanged,
  onTestOutput,
}: {
  goalSeed: string;
  projectId?: number | null;
  workItemId?: number | null;
  roots: CodingAgentMissionRoot[];
  workspaceRoot: string;
  seedMission?: CodingAgentMission | null;
  missionId?: string | null;
  onMissionChanged?: (id: string) => void;
  onOpenPath?: (path: string) => void;
  onFilesChanged?: (paths: string[]) => void;
  onTestOutput?: (text: string) => void;
}) {
  const [goal, setGoal] = useState(goalSeed);
  const [patchesJson, setPatchesJson] = useState("");
  const [mission, setMission] = useState<CodingAgentMission | null>(seedMission ?? null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDiff, setShowDiff] = useState(false);
  const [shipNote, setShipNote] = useState<string | null>(null);
  const [reattaching, setReattaching] = useState(false);
  const attach = useComposerAttachments(projectId, workItemId);

  useEffect(() => {
    if (seedMission) setMission(seedMission);
  }, [seedMission]);

  // A Mission lives on the server, but the pane only ever held it in React
  // state, so navigating away and back showed an empty "start a mission"
  // form while the real Mission was still running (finding F4). Re-attach
  // from the durable id the page hands down.
  const knownMissionId = mission?.id || "";
  useEffect(() => {
    const wanted = (missionId || "").trim();
    if (!wanted || wanted === knownMissionId) return;
    let cancelled = false;
    setReattaching(true);
    void codingAgentGetMission(wanted)
      .then((m) => {
        if (cancelled || !m?.id) return;
        setMission(m);
        const files = m.files || [];
        if (files.length) onFilesChanged?.(files);
      })
      .catch(() => {
        // A stale id (mission expired, or a different machine) must not
        // block starting a new mission -- leave the form usable.
      })
      .finally(() => {
        if (!cancelled) setReattaching(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [missionId, knownMissionId]);

  useEffect(() => {
    if (knownMissionId) onMissionChanged?.(knownMissionId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [knownMissionId]);

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
    const docBlob = attach.documentContextBlob();
    const localIds = new Set([
      ...attach.attachments.map((a) => a.id),
      ...attach.images.map((i) => i.artifactId).filter((id): id is number => id != null),
    ]);
    const durableBlob = await fetchDurableAttachmentBlob(workItemId, localIds);
    const combinedBlob = [docBlob, durableBlob].filter(Boolean).join("\n\n");
    const goalWithAttachments = combinedBlob ? `${g}\n\n${combinedBlob}` : g;
    await run(() =>
      codingAgentCreateMission({
        goal: goalWithAttachments,
        project_id: projectId,
        work_item_id: workItemId,
        roots,
        patches_by_repo: patches,
      }),
    );
    attach.reset();
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
      <ContextUsedStrip used={mission?.context_used} />
      {reattaching ? (
        <p
          className="px-3 pt-1 text-[10px] text-slate-500"
          data-testid="mentrix-coding-agent-mission-reattaching"
        >
          Re-attaching to mission {missionId}…
        </p>
      ) : null}

      <div className="min-h-0 flex-1 space-y-2 overflow-auto px-3 py-2">
        <label className="block text-[10px] uppercase text-slate-400">Goal</label>
        <textarea
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          onPaste={(e) => {
            const imgs = imageFilesFromClipboard(e);
            if (imgs.length) void attach.attachFiles(imgs);
          }}
          disabled={busy}
          placeholder="Describe the change. Approve &amp; Build implements it in a worktree, then this tab ships the PR. Pull-latest on clones does not start a mission."
          className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-xs"
          rows={2}
          data-testid="mentrix-coding-agent-mission-goal"
        />
        <ComposerAttachmentBar
          attachments={attach.attachments}
          images={attach.images}
          attaching={attach.attaching}
          onAttachFiles={(files) => void attach.attachFiles(files)}
          onRemoveAttachment={attach.removeAttachment}
          onRemoveImage={attach.removeImage}
          testIdPrefix="mentrix-coding-agent-mission"
        />
        <WorkItemAttachmentsStrip workItemId={workItemId} />
        {attach.error ? <p className="text-rose-600">{attach.error}</p> : null}
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

function repoIdsFromRoots(roots: CodingAgentMissionRoot[]): number[] {
  return roots.map((r) => r.id).filter((id) => Number.isFinite(id) && id > 0);
}

/** No model-capability registry exists in ZECT today (see ModelSelector) --
 * this is a soft, best-effort hint, not an enforced gate. A false negative
 * just means a missed warning; the real failure mode (a genuinely
 * non-vision model) still surfaces the provider's own error either way. */
const _VISION_CAPABLE_HINTS = ["gpt-4o", "gpt-4.1", "gpt-5", "o1", "o3", "claude-3", "claude-opus", "claude-sonnet", "claude-haiku", "gemini", "grok"];

function isLikelyVisionCapable(modelId: string): boolean {
  const m = (modelId || "").toLowerCase();
  return _VISION_CAPABLE_HINTS.some((hint) => m.includes(hint));
}

/** Folds in whatever is durably attached to this WorkItem from ANY pane
 * (not just this one's own local attach state), so an ASK attachment is
 * actually usable in PLAN/AGENT, not merely visible. `excludeIds` skips
 * attachments this pane's own local `useComposerAttachments` instance
 * already uploaded THIS turn, so their content isn't folded in twice.
 * Images have no text form -- Mission/PLAN goal text has no vision
 * channel -- so they're only noted by filename here; they remain usable as
 * real vision content wherever ASK's own `images` param already reaches
 * the model. */
async function fetchDurableAttachmentBlob(workItemId: number | null | undefined, excludeIds: Set<number>): Promise<string> {
  if (workItemId == null) return "";
  try {
    const { attachments } = await listWorkItemAttachments(workItemId);
    const pending = attachments.filter((a) => !excludeIds.has(a.id));
    if (!pending.length) return "";
    const parts: string[] = [];
    for (const a of pending) {
      if (a.kind === "image") {
        parts.push(`[attachment:${a.filename}] (image attached earlier in this Mission)`);
        continue;
      }
      try {
        const doc = await getDocumentMarkdown(a.id);
        if (doc.markdown) parts.push(`[attachment:${a.filename}]\n${doc.markdown}`);
      } catch {
        /* one unreadable attachment must not block the rest */
      }
    }
    return parts.join("\n\n");
  } catch {
    return "";
  }
}

type ContextUsedLite = {
  knowledge?: boolean;
  lattice_hits?: number;
  lattice_indexed?: boolean;
  lattice_state?: string;
  blueprint?: boolean;
};

function contextFromDeveloperPi(pi?: {
  lattice?: { status?: string; state?: string; hits?: unknown[] };
  knowledge?: unknown[];
  blueprint?: { snippet?: string };
} | null): ContextUsedLite {
  const hits = Array.isArray(pi?.lattice?.hits) ? pi.lattice.hits.length : 0;
  const state = canonicalLatticeState(pi?.lattice?.status || pi?.lattice?.state);
  return {
    knowledge: Array.isArray(pi?.knowledge) && pi.knowledge.length > 0,
    lattice_hits: hits,
    lattice_indexed: state === "READY",
    lattice_state: state,
    blueprint: Boolean(pi?.blueprint?.snippet),
  };
}

function contextUsedSummaryText(used?: ContextUsedLite | null): string {
  if (!used) return "";
  // The same canonical state the Developer header shows, so a Mission and
  // the header can never disagree about the Lattice (finding F6). Falling
  // back to the boolean keeps older persisted context packs readable.
  const state = canonicalLatticeState(
    used.lattice_state || (used.lattice_indexed ? "READY" : "NOT_INDEXED"),
  );
  const lattice =
    state === "READY" && used.lattice_hits
      ? `${latticeHeaderLabel(state)} · ${used.lattice_hits} hits`
      : latticeHeaderLabel(state);
  const parts = [lattice];
  if (used.knowledge) parts.push("Knowledge");
  if (used.blueprint) parts.push("Blueprint");
  return parts.join(" · ");
}

function ContextUsedStrip({ used }: { used?: ContextUsedLite | null }) {
  if (!used) return null;
  return (
    <p className="mt-1 text-[10px] text-slate-500" data-testid="mentrix-coding-agent-context-used">
      Context used · {contextUsedSummaryText(used)}
    </p>
  );
}

/** Everything ASK gathered for one "Create Plan" click -- so PLAN starts
 * from the requirement, not a blank textarea the user has to re-paste into.
 * `version` makes each click distinct even if the underlying question is
 * unchanged, so the parent can tell "a new handoff happened" from "PlanPane
 * remounted for an unrelated reason". */
type AskToPlanSeed = {
  version: number;
  question: string;
  turns: DeveloperAskTurn[];
  evidence: string;
  attachmentBlob: string;
  findings: string;
};

function buildAskSeedMarkdown(seed: AskToPlanSeed): string {
  const sections: string[] = ["## Requirements from ASK", ""];
  if (seed.turns.length) {
    sections.push("### Conversation");
    for (const t of seed.turns) {
      sections.push(`**Q:** ${t.question}`, `**A:** ${t.answer}`, "");
    }
  }
  if (seed.evidence) {
    sections.push("### Evidence", seed.evidence, "");
  }
  if (seed.attachmentBlob) {
    sections.push("### Attached documents", seed.attachmentBlob, "");
  }
  if (seed.findings) {
    sections.push("### Findings", seed.findings, "");
  }
  sections.push("## Plan", "");
  return sections.join("\n");
}

function AskPane({
  workspaceRoot,
  model,
  workItemId,
  projectId,
  roots,
  onCreatePlan,
  onWorkItemResolved,
}: {
  workspaceRoot: string;
  model: string;
  workItemId?: number | null;
  projectId?: number | null;
  roots: CodingAgentMissionRoot[];
  onCreatePlan: (seed: AskToPlanSeed) => void;
  onWorkItemResolved?: (id: number) => void;
}) {
  const [q, setQ] = useState("");
  const [turns, setTurns] = useState<DeveloperAskTurn[]>([]);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [contextUsed, setContextUsed] = useState<Parameters<typeof ContextUsedStrip>[0]["used"]>(null);
  const [mentionPack, setMentionPack] = useState<ContextPack | null>(null);
  const qRef = useRef<HTMLTextAreaElement | null>(null);
  const attach = useComposerAttachments(projectId, workItemId);

  /** Resolve every @mention against real data so ASK sees the same truthful
   * context PLAN already does -- @mentions in the question are decorative
   * otherwise. */
  const resolveMentionBlob = async (): Promise<string> => {
    if (!hasMentions(q) || !workspaceRoot) return "";
    try {
      const { pack } = await codingAgentResolveMentions({
        text: q,
        workspace: workspaceRoot,
        work_item_id: workItemId ?? undefined,
      });
      setMentionPack(pack);
      const resolved = pack.items.filter((i) => i.verification_state !== "unresolved");
      if (!resolved.length) return "";
      const parts = resolved.map((item) => `[${item.source_type}:${item.source_id}]\n${item.content}`);
      return `## Resolved Context\n\n${parts.join("\n\n")}\n\n## Question\n\n`;
    } catch {
      /* Mention resolution failing must never block Ask. */
      return "";
    }
  };

  // Restore the conversation whenever this pane mounts with a known
  // work item -- covers tab-switch (unmount/remount), navigate-away-and-back,
  // browser refresh, and backend/Electron restart, all via the same durable
  // source (WorkItemEvent rows), not client-only state.
  useEffect(() => {
    let cancelled = false;
    setHistoryLoaded(false);
    if (!workItemId) {
      setTurns([]);
      setHistoryLoaded(true);
      return;
    }
    void developerAskHistory(workItemId)
      .then((res) => {
        if (cancelled) return;
        const turns = res.turns || [];
        setTurns(turns);
        // Restore the Context Used strip from the most recent turn's
        // persisted summary too -- without this it stays blank after a
        // reload/tab switch until the user asks a brand-new question, even
        // though the prior turn's context was already computed and is now
        // durable. Older turns persisted before context_used existed have
        // no such key -- leave the strip blank rather than guessing.
        const lastContextUsed = turns[turns.length - 1]?.context_used;
        if (lastContextUsed) setContextUsed(lastContextUsed);
      })
      .catch(() => {
        /* history is best-effort; a fresh Ask still works without it */
      })
      .finally(() => {
        if (!cancelled) setHistoryLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, [workItemId]);

  const ask = async () => {
    const question = q.trim();
    if (!question) return;
    setBusy(true);
    setError(null);
    try {
      const ids = repoIdsFromRoots(roots);
      const mentionBlob = await resolveMentionBlob();
      const docBlob = attach.documentContextBlob();
      const localIds = new Set([
        ...attach.attachments.map((a) => a.id),
        ...attach.images.map((i) => i.artifactId).filter((id): id is number => id != null),
      ]);
      const durableBlob = await fetchDurableAttachmentBlob(workItemId, localIds);
      const combinedBlob = [docBlob, durableBlob].filter(Boolean).join("\n\n");
      const askedText = `${mentionBlob}${question}${combinedBlob ? `\n\n${combinedBlob}` : ""}`;
      const images = attach.images.map((i) => i.dataUrl);
      const res = await developerAsk({
        question: askedText,
        project_id: projectId ?? undefined,
        work_item_id: workItemId ?? undefined,
        repository_id: ids[0],
        repository_ids: ids,
        images: images.length ? images : undefined,
      });
      // Reusing the same work_item_id on every subsequent call (instead of
      // letting the backend spawn a fresh WorkItem each time) is what makes
      // the conversation persist at all -- lift it to the parent once resolved.
      if (res.work_item_id && res.work_item_id !== workItemId) {
        onWorkItemResolved?.(res.work_item_id);
        // Link any attachment made before this WorkItem existed right now,
        // using the id from this response directly -- waiting for it to
        // come back down as a prop would race attach.reset() below.
        await attach.linkPendingTo(res.work_item_id);
      }
      setTurns((prev) => [
        ...prev,
        { question, answer: res.answer || "", model: "", offline: false, image_count: images.length, created_at: null },
      ]);
      setQ("");
      attach.reset();
      setContextUsed(contextFromDeveloperPi(res.project_intelligence));
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
        ref={qRef}
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onPaste={(e) => {
          const imgs = imageFilesFromClipboard(e);
          if (imgs.length) void attach.attachFiles(imgs);
        }}
        className="mt-1 min-h-[4rem] rounded border border-slate-200 px-2 py-1"
        placeholder="Search or explain this workspace… (paste a screenshot to ask about it) — @file @workspace @problem @workitem …"
        data-testid="mentrix-coding-agent-ask-input"
      />
      <MentionAutocomplete
        value={q}
        onChange={(next, cursor) => {
          setQ(next);
          requestAnimationFrame(() => qRef.current?.setSelectionRange(cursor, cursor));
        }}
        textareaRef={qRef}
      />
      <MentionContextStrip pack={mentionPack} />
      <ComposerAttachmentBar
        attachments={attach.attachments}
        images={attach.images}
        attaching={attach.attaching}
        onAttachFiles={(files) => void attach.attachFiles(files)}
        onRemoveAttachment={attach.removeAttachment}
        onRemoveImage={attach.removeImage}
        testIdPrefix="mentrix-coding-agent-ask"
      />
      <WorkItemAttachmentsStrip workItemId={workItemId} />
      {attach.images.length > 0 && !isLikelyVisionCapable(model) ? (
        <p className="mt-1 text-[10px] text-amber-600" data-testid="mentrix-coding-agent-ask-vision-hint">
          {model} may not support image attachments — switch to a vision-capable model for reliable results.
        </p>
      ) : null}
      {attach.error ? <p className="mt-1 text-rose-600">{attach.error}</p> : null}
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
          onClick={() => {
            const evidence = (mentionPack?.items || [])
              .filter((i) => i.verification_state !== "unresolved")
              .map((item) => `[${item.source_type}:${item.source_id}]\n${item.content}`)
              .join("\n\n");
            onCreatePlan({
              version: Date.now(),
              question: q.trim() || turns[turns.length - 1]?.question || "",
              turns,
              evidence,
              attachmentBlob: attach.documentContextBlob(),
              findings: contextUsedSummaryText(contextUsed),
            });
          }}
          className="rounded border border-slate-300 px-2 py-1"
          data-testid="mentrix-coding-agent-ask-create-plan"
        >
          Create Plan
        </button>
      </div>
      {error ? (
        <p className="mt-1 text-rose-600" data-testid="mentrix-coding-agent-ask-error">
          {error}
        </p>
      ) : null}
      <ContextUsedStrip used={contextUsed} />
      {historyLoaded && turns.length > 0 ? (
        <div
          className="mt-2 flex-1 overflow-auto rounded bg-slate-50 p-2"
          data-testid="mentrix-coding-agent-ask-history"
        >
          {turns.map((t, i) => (
            <div key={i} className="mb-2 border-b border-slate-200 pb-2 last:mb-0 last:border-0">
              <p className="font-semibold text-slate-600">{t.question}</p>
              <pre className="mt-1 whitespace-pre-wrap text-[11px]" data-testid={i === turns.length - 1 ? "mentrix-coding-agent-ask-answer" : undefined}>
                {t.answer}
              </pre>
            </div>
          ))}
        </div>
      ) : null}
      <p className="mt-1 text-[10px] text-slate-400">WorkItem {workItemId ?? "—"} · zero edits</p>
    </div>
  );
}

function PlanPane({
  goalSeed,
  askSeed,
  workItemId,
  projectId,
  roots,
  workspaceRoot,
  model,
  onApproved,
  onFilesChanged,
  onOpenPath,
}: {
  goalSeed: string;
  askSeed?: AskToPlanSeed | null;
  workItemId?: number | null;
  projectId?: number | null;
  roots: CodingAgentMissionRoot[];
  workspaceRoot: string;
  model: string;
  onApproved: (mission: CodingAgentMission) => void;
  onFilesChanged?: (paths: string[]) => void;
  onOpenPath?: (path: string) => void;
}) {
  // Read once at mount -- askSeed is a one-shot handoff (the parent clears
  // it right after this pane mounts), so a plain prop read here, not an
  // effect, is what keeps a later unrelated remount from reapplying it.
  const [goal, setGoal] = useState(() => (askSeed?.question ? askSeed.question : goalSeed));
  const [markdown, setMarkdown] = useState(() => (askSeed ? buildAskSeedMarkdown(askSeed) : ""));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const key = String(workItemId || "local");
  void model; // PLAN never sends images to a model itself -- see AskPane for the vision path.

  const [contextUsed, setContextUsed] = useState<Parameters<typeof ContextUsedStrip>[0]["used"]>(null);
  const mdRef = useRef<HTMLTextAreaElement | null>(null);
  const [mentionPack, setMentionPack] = useState<ContextPack | null>(null);
  const [planPath, setPlanPath] = useState("");
  const attach = useComposerAttachments(projectId, workItemId);

  // Reload the saved plan whenever this pane mounts (tab switch, navigate
  // away and back, reload). Without this the on-disk .plan.md survives but
  // the editor comes back empty, which reads as "my plan was lost".
  useEffect(() => {
    let cancelled = false;
    void codingAgentGetPlan(`${key}-coding`, workspaceRoot || undefined)
      .then((saved) => {
        if (cancelled || !saved?.markdown) return;
        setMarkdown((current) => (current.trim() ? current : saved.markdown));
        setPlanPath(saved.path || "");
      })
      .catch(() => {
        /* no saved plan for this work item yet -- start from an empty editor */
      });
    return () => {
      cancelled = true;
    };
  }, [key, workspaceRoot]);

  /** Resolve every @mention against real data and fold both that and any
   * uploaded attachments into one context blob to prepend to what actually
   * reaches the model -- @mentions in the PLAN.md text are decorative
   * otherwise. */
  const resolveContextAndBuildBlob = async (): Promise<string> => {
    const parts: string[] = [];
    if (hasMentions(markdown) && workspaceRoot) {
      try {
        const { pack } = await codingAgentResolveMentions({
          text: markdown,
          workspace: workspaceRoot,
          work_item_id: workItemId ?? undefined,
        });
        setMentionPack(pack);
        const resolved = pack.items.filter((i) => i.verification_state !== "unresolved");
        for (const item of resolved) parts.push(`[${item.source_type}:${item.source_id}]\n${item.content}`);
      } catch {
        /* Context resolution failing must never block Save/Approve & Build. */
      }
    }
    const docBlob = attach.documentContextBlob();
    if (docBlob) parts.push(docBlob);
    const localIds = new Set([
      ...attach.attachments.map((a) => a.id),
      ...attach.images.map((i) => i.artifactId).filter((id): id is number => id != null),
    ]);
    const durableBlob = await fetchDurableAttachmentBlob(workItemId, localIds);
    if (durableBlob) parts.push(durableBlob);
    return parts.length ? `## Resolved Context\n\n${parts.join("\n\n")}\n\n## Plan\n\n` : "";
  };

  const save = async () => {
    if (!markdown.trim()) return;
    setBusy(true);
    setError(null);
    try {
      // Resolve for display (truthful Context Used while still drafting) --
      // the persisted PLAN.md stays exactly what the user wrote; the
      // resolved blob is only prepended when the mission is actually built.
      await resolveContextAndBuildBlob();
      const saved = await codingAgentSavePlan({
        work_item_or_run: key,
        title: "coding",
        markdown,
        meta: { workspace: workspaceRoot },
        workspace: workspaceRoot,
      });
      setPlanPath(saved.path || "");
      onFilesChanged?.([]);
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
      const ids = repoIdsFromRoots(roots);
      const res = await developerPlan({
        goal: g,
        project_id: projectId ?? undefined,
        work_item_id: workItemId ?? undefined,
        repository_id: ids[0],
        repository_ids: ids,
      });
      setMarkdown(res.plan || "");
      setContextUsed(contextFromDeveloperPi(res.project_intelligence));
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
    if (!roots.length) {
      setError("Authorize a local workspace root before Approve & Build");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const contextBlob = await resolveContextAndBuildBlob();
      const augmentedPlan = contextBlob ? `${contextBlob}${markdown}` : markdown;
      await codingAgentSavePlan({
        work_item_or_run: key,
        title: "coding",
        markdown: augmentedPlan,
        workspace: workspaceRoot,
      });
      const created = await codingAgentCreateMission({
        goal: goal.trim() || "Approved PLAN",
        project_id: projectId,
        work_item_id: workItemId,
        roots,
        plan: augmentedPlan,
        workspace_parent: workspaceRoot,
        propose_if_empty: true,
      });
      onApproved(created);
      if (created.files?.length) onFilesChanged?.(created.files);
      if (created.phase === "awaiting_plan_approval") {
        void codingAgentApprovePlan(created.id)
          .then((approved) => {
            onApproved(approved);
            // approve_plan runs edit -> test -> diagnose/repair -> app
            // start/browser-verify synchronously -- its response already
            // carries every file that loop touched, so the real Explorer/
            // Diff must refresh now, not wait for a later manual click.
            if (approved.files?.length) onFilesChanged?.(approved.files);
          })
          .catch(() => {
            /* Agent tab polls / shows blockers; PLAN already handed off. */
          });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approve & Build failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col p-2 text-xs" data-testid="mentrix-coding-agent-plan-mode">
      <p className="text-[10px] text-slate-500">PLAN.md is scratch in .zect/plans (gitignored). Approve &amp; Build starts the Mentrix implementer in an isolated worktree (same tool loop as Implement chat). Zero edits until then.</p>
      {planPath ? (
        <button
          type="button"
          onClick={() => onOpenPath?.(planPath)}
          className="mt-1 truncate text-left font-mono text-[10px] text-teal-700 underline"
          title={planPath}
          data-testid="mentrix-coding-agent-plan-path"
        >
          {planPath}
        </button>
      ) : null}
      <input
        value={goal}
        onChange={(e) => setGoal(e.target.value)}
        className="mt-1 rounded border border-slate-200 px-2 py-1"
        placeholder="Goal"
        data-testid="mentrix-coding-agent-plan-goal"
      />
      <textarea
        ref={mdRef}
        value={markdown}
        onChange={(e) => setMarkdown(e.target.value)}
        onPaste={(e) => {
          const imgs = imageFilesFromClipboard(e);
          if (imgs.length) void attach.attachFiles(imgs);
        }}
        className="mt-1 min-h-[8rem] flex-1 rounded border border-slate-200 px-2 py-1 font-mono text-[11px]"
        placeholder="## Plan  --  @file @folder @symbol @references @repo @plan @diff @terminal @error @test @lattice @skill @rule"
        data-testid="mentrix-coding-agent-plan-md"
      />
      <MentionAutocomplete
        value={markdown}
        onChange={(next, cursor) => {
          setMarkdown(next);
          requestAnimationFrame(() => mdRef.current?.setSelectionRange(cursor, cursor));
        }}
        textareaRef={mdRef}
      />
      <MentionContextStrip pack={mentionPack} />
      <ComposerAttachmentBar
        attachments={attach.attachments}
        images={attach.images}
        attaching={attach.attaching}
        onAttachFiles={(files) => void attach.attachFiles(files)}
        onRemoveAttachment={attach.removeAttachment}
        onRemoveImage={attach.removeImage}
        testIdPrefix="mentrix-coding-agent-plan"
      />
      <WorkItemAttachmentsStrip workItemId={workItemId} />
      {attach.error ? <p className="text-rose-600">{attach.error}</p> : null}
      {error ? (
        <p className="text-rose-600" data-testid="mentrix-coding-agent-plan-error">
          {error}
        </p>
      ) : null}
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
    void codingAgentListPlans(workspaceRoot || undefined)
      .then((r) => setRows(r.plans || []))
      .catch(() => setRows([]));
  }, [workspaceRoot]);
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
  const [contextUsed, setContextUsed] = useState<Parameters<typeof ContextUsedStrip>[0]["used"]>(null);
  const [mentionPack, setMentionPack] = useState<ContextPack | null>(null);
  const goalRef = useRef<HTMLInputElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const writtenRef = useRef<string[]>([]);
  const sessionIdRef = useRef<string | null>(initialSessionId);
  sessionIdRef.current = sessionId;

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
      const sid = sessionIdRef.current;
      if (sid) {
        void codingAgentGetSession(sid)
          .then((s) => setContextUsed(s?.context_used ?? null))
          .catch(() => {
            /* Context Used is a display nicety -- never blocks on it. */
          });
      }
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

  const resolveMentionBlob = async (text: string): Promise<string> => {
    if (!hasMentions(text) || !workspaceRoot) return "";
    try {
      const { pack } = await codingAgentResolveMentions({ text, workspace: workspaceRoot });
      setMentionPack(pack);
      const resolved = pack.items.filter((i) => i.verification_state !== "unresolved");
      if (!resolved.length) return "";
      const parts = resolved.map((item) => `[${item.source_type}:${item.source_id}]\n${item.content}`);
      return `## Resolved Context\n\n${parts.join("\n\n")}\n\n## Goal\n\n`;
    } catch {
      /* Mention resolution failing must never block Run. */
      return "";
    }
  };

  const start = async () => {
    const g = goal.trim();
    if (!g || !workspaceRoot) return;
    setError(null);
    setContextUsed(null);
    writtenRef.current = [];
    pushLine({ kind: "user", text: g });
    setBusy(true);
    try {
      const mentionBlob = await resolveMentionBlob(g);
      const res = await codingAgentCreateSession({
        goal: `${mentionBlob}${g}`,
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
        <ContextUsedStrip used={contextUsed} />
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
        <div className="flex-1">
          <input
            ref={goalRef}
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void start();
              }
            }}
            disabled={busy || !workspaceRoot}
            placeholder={workspaceRoot ? "Describe the change… — @file @workspace @problem @branch …" : "Set workspace root first"}
            className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-xs"
            data-testid="mentrix-coding-agent-input"
          />
          <MentionAutocomplete
            value={goal}
            onChange={(next, cursor) => {
              setGoal(next);
              requestAnimationFrame(() => goalRef.current?.setSelectionRange(cursor, cursor));
            }}
            textareaRef={goalRef}
          />
          <MentionContextStrip pack={mentionPack} />
        </div>
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
