import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Bot, Check, GitPullRequest, Play, Sparkles } from "lucide-react";
import {
  mentrixAgents,
  mentrixApproveRun,
  mentrixConfirmPlan,
  mentrixCreatePr,
  mentrixGetRun,
  mentrixListRuns,
  mentrixRealtimeTool,
  mentrixStartRun,
} from "@/lib/api";
import { useMentrixSession } from "@/mentrix/MentrixSessionContext";
const MODES = ["upgrade", "bugfix", "chat", "understand", "deliver", "review_only", "ops"];

const WORKFLOW_STEPS = [
  { id: "lattice", label: "Lattice" },
  { id: "plan", label: "Plan" },
  { id: "build_gates", label: "Build/Gates" },
  { id: "ultra_review", label: "Ultra Review" },
  { id: "approve", label: "Approve" },
  { id: "pr", label: "PR" },
] as const;

type ChatMsg = {
  role: "user" | "assistant" | "system";
  text: string;
  meta?: string;
};

function workflowStepIndex(run: any): number {
  if (!run) return -1;
  if (run.pr_url || run.status === "pr_created") return 5;
  if (run.approved_at || run.status === "approved") return 4;
  const gates = run.gates || run.result?.gates || {};
  const events = run.events || [];
  const phases = new Set(events.map((e: any) => e.phase).filter(Boolean));
  const agents = new Set(events.map((e: any) => e.agent).filter(Boolean));
  if (
    (gates.review_ok != null && run.status !== "awaiting_plan_confirm") ||
    phases.has("review") ||
    agents.has("reviewer") ||
    run.result?.ultra_review
  ) {
    return 3;
  }
  if (
    run.status !== "awaiting_plan_confirm" &&
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

function speakStatus(text: string, enabled: boolean) {
  if (!enabled || typeof window === "undefined" || !window.speechSynthesis) return;
  try {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.05;
    window.speechSynthesis.speak(u);
  } catch {
    /* ignore TTS failures */
  }
}

export default function Mentrix() {
  // Realtime voice (persistent dock, mounted globally in Layout.tsx) owns the speaker
  // whenever it's connected — this page's browser speechSynthesis must yield to it,
  // otherwise both speak at once ("multiple voices").
  const { voiceConnected } = useMentrixSession();
  const location = useLocation();
  const [goal, setGoal] = useState("");
  const [mode, setMode] = useState("upgrade");
  const [projectKey, setProjectKey] = useState("");
  const [workspace, setWorkspace] = useState("");
  const [issueKey, setIssueKey] = useState("");
  const [sourceLang, setSourceLang] = useState("");
  const [targetLang, setTargetLang] = useState("");
  const [agents, setAgents] = useState<any>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [active, setActive] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [ack, setAck] = useState(false);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [sttListening, setSttListening] = useState(false);
  const [wakeHint, setWakeHint] = useState("");
  const [jiraCommentNote, setJiraCommentNote] = useState("");
  const [planSummary, setPlanSummary] = useState("");
  const pollRef = useRef<number | null>(null);
  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const lastSpokenStatus = useRef<string>("");
  const goalInputRef = useRef<HTMLTextAreaElement | null>(null);

  const refresh = async () => {
    try {
      const [a, r] = await Promise.all([mentrixAgents(), mentrixListRuns(15)]);
      setAgents(a);
      setRuns(Array.isArray(r) ? r : []);
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    refresh();
    try {
      const raw = localStorage.getItem("zect_mentrix_workspace");
      if (raw) {
        const ws = JSON.parse(raw) as {
          project_key?: string;
          projectKey?: string;
          path?: string;
          workspace?: string;
        };
        const pk = ws.project_key || ws.projectKey;
        const wp = ws.path || ws.workspace;
        if (pk) setProjectKey(pk);
        if (wp) setWorkspace(wp);
      }
    } catch {
      /* ignore */
    }
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, []);

  // Incident / Ask / Plan handoff into Delivery
  useEffect(() => {
    const st = (location.state || {}) as {
      goal?: string;
      issue_key?: string;
      projectKey?: string;
      workspace?: string;
    };
    const params = new URLSearchParams(location.search);
    if (st.goal) setGoal(st.goal);
    else if (params.get("goal")) setGoal(params.get("goal") || "");
    if (st.issue_key) setIssueKey(st.issue_key);
    else if (params.get("issue_key")) setIssueKey(params.get("issue_key") || "");
    if (st.projectKey) setProjectKey(st.projectKey);
    if (st.workspace) setWorkspace(st.workspace);
  }, [location.state, location.search]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, active?.events?.length]);

  // Desktop wake: native Windows speech (main process) + hotkey; Web Speech only as browser bonus
  useEffect(() => {
    const desktop = window.zectDesktop?.mentrix;
    const unsubs: Array<() => void> = [];
    if (desktop?.onWake) {
      unsubs.push(
        desktop.onWake(() => {
          goalInputRef.current?.focus();
          speakStatus("Mentrix ready. State your goal.", ttsEnabled && !voiceConnected);
          setWakeHint("Wake heard — Mentrix ready");
        }),
      );
    }
    if (desktop?.onWakeStatus) {
      unsubs.push(
        desktop.onWakeStatus((s: any) => {
          if (s?.ok) {
            setSttListening(true);
            setWakeHint("Listening (Windows speech / headset mic) — say Hey Mentrix");
          } else {
            setSttListening(false);
            setWakeHint(`Voice wake offline (${s?.reason || "n/a"}) — use Ctrl+Shift+Space`);
          }
        }),
      );
    }
    desktop?.getWakeStatus?.().then((s: any) => {
      if (s?.ok) {
        setSttListening(true);
        setWakeHint("Listening (Windows speech / headset mic) — say Hey Mentrix");
      } else if (desktop) {
        setWakeHint("Use Ctrl+Shift+Space or Mentrix → Restart wake listening");
      }
    });
    if (desktop?.onSttGoal) {
      unsubs.push(
        desktop.onSttGoal((payload) => {
          if (payload?.goal) setGoal(payload.goal);
        }),
      );
    }
    // Browser-only Web Speech (Chrome). Electron Chromium cannot use Google STT.
    const SR =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    let recognition: any = null;
    if (!desktop && SR) {
      recognition = new SR();
      recognition.continuous = true;
      recognition.interimResults = false;
      recognition.lang = "en-US";
      recognition.onresult = async (event: any) => {
        const last = event.results?.[event.results.length - 1];
        const transcript = last?.[0]?.transcript || "";
        if (!transcript) return;
        const t = transcript.toLowerCase();
        if (/\b(mentrix|matrix|mentrics)\b/.test(t) || t.includes("hey mentrix")) {
          goalInputRef.current?.focus();
          setWakeHint("Wake heard — Mentrix ready");
          speakStatus("Mentrix ready. State your goal.", ttsEnabled && !voiceConnected);
        } else if (transcript.trim().length > 8) {
          setGoal((g) => (g ? g : transcript.trim()));
        }
      };
      recognition.onerror = () => setSttListening(false);
      recognition.onend = () => {
        try {
          recognition.start();
        } catch {
          /* ignore */
        }
      };
      try {
        recognition.start();
        setSttListening(true);
        setWakeHint("Browser listening — say Hey Mentrix");
      } catch {
        setSttListening(false);
      }
    }
    const onDomWake = () => {
      goalInputRef.current?.focus();
      speakStatus("Mentrix ready. State your goal.", ttsEnabled && !voiceConnected);
    };
    window.addEventListener("mentrix-wake", onDomWake);
    return () => {
      unsubs.forEach((u) => u());
      window.removeEventListener("mentrix-wake", onDomWake);
      try {
        if (recognition) {
          recognition.onend = null;
          recognition.stop();
        }
      } catch {
        /* ignore */
      }
      setSttListening(false);
    };
  }, [ttsEnabled, voiceConnected]);

  // TTS on status transitions
  useEffect(() => {
    if (!active?.status || !ttsEnabled || voiceConnected) return;
    const key = `${active.id}:${active.status}:${active.next_step || ""}`;
    if (key === lastSpokenStatus.current) return;
    lastSpokenStatus.current = key;
    const blockers = Object.entries(active.gates || active.result?.gates || {})
      .filter(([k, v]) => k.endsWith("_ok") && v === false)
      .map(([k]) => k);
    if (active.status === "running") {
      speakStatus(`Mentrix running. Phase ${active.current_agent || "scout"}.`, true);
    } else if (active.status === "awaiting_approval" || active.status === "needs_human") {
      speakStatus(
        blockers.length
          ? `Mentrix needs attention. Blockers: ${blockers.join(", ")}.`
          : "Mentrix awaiting your approval.",
        true,
      );
    } else if (active.status === "approved") {
      speakStatus("Approved. You can create the pull request.", true);
    } else if (active.pr_url) {
      speakStatus("Pull request ready.", true);
    }
  }, [active?.id, active?.status, active?.next_step, active?.pr_url, ttsEnabled, voiceConnected]);

  const eventsToMessages = (run: any): ChatMsg[] => {
    const msgs: ChatMsg[] = [
      { role: "user", text: run.goal, meta: `mode=${run.mode}` },
    ];
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
  };

  const startPolling = (runId: number) => {
    if (pollRef.current) window.clearInterval(pollRef.current);
    pollRef.current = window.setInterval(async () => {
      try {
        const run = await mentrixGetRun(runId);
        setActive(run);
        setMessages(eventsToMessages(run));
        if (run.status && run.status !== "running") {
          if (pollRef.current) window.clearInterval(pollRef.current);
          pollRef.current = null;
          await refresh();
        }
      } catch {
        /* ignore poll errors */
      }
    }, 2000);
  };

  const start = async () => {
    setError("");
    setLoading(true);
    setMessages([{ role: "user", text: goal, meta: `mode=${mode}` }]);
    try {
      const run = await mentrixStartRun(goal, mode, projectKey, workspace, {
        source_lang: sourceLang,
        target_lang: targetLang,
      });
      setActive(run);
      setMessages(eventsToMessages(run));
      if (run.status === "running") startPolling(run.id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Run failed");
    } finally {
      setLoading(false);
    }
  };

  const openRun = async (id: number) => {
    setLoading(true);
    try {
      const run = await mentrixGetRun(id);
      setActive(run);
      setMessages(eventsToMessages(run));
      if (run.status === "running") startPolling(id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Load failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const p = active?.result?.plan;
    if (p?.summary) setPlanSummary(String(p.summary));
    else if (active?.status !== "awaiting_plan_confirm") setPlanSummary("");
  }, [active?.id, active?.status, active?.result?.plan]);

  const confirmPlan = async () => {
    if (!active?.id) return;
    setError("");
    setLoading(true);
    try {
      const run = await mentrixConfirmPlan(active.id, {
        summary: planSummary || undefined,
        steps: active?.result?.plan?.steps,
      });
      setActive(run);
      setMessages(eventsToMessages(run));
      if (run.status === "running") startPolling(run.id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Confirm plan failed");
    } finally {
      setLoading(false);
    }
  };

  const approve = async () => {
    if (!active?.id) return;
    setError("");
    setLoading(true);
    try {
      const run = await mentrixApproveRun(active.id, ack);
      setActive(run);
      setMessages(eventsToMessages(run));
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approve failed");
    } finally {
      setLoading(false);
    }
  };

  const createPr = async () => {
    if (!active?.id) return;
    setError("");
    setJiraCommentNote("");
    setLoading(true);
    try {
      const run = await mentrixCreatePr(active.id, { dry_run: true });
      setActive(run);
      setMessages(eventsToMessages(run));
      await refresh();
      const pr =
        run?.pr_url ||
        run?.result?.pr_url ||
        (typeof run?.result?.pr === "object" ? run.result.pr?.html_url : "") ||
        "";
      const key = issueKey.trim().toUpperCase();
      if (key && pr) {
        try {
          await mentrixRealtimeTool(
            "jira_comment_pr",
            { issue_key: key, pr_url: String(pr) },
            true,
          );
          setJiraCommentNote(`Commented PR on ${key}`);
        } catch (ce) {
          setJiraCommentNote(
            ce instanceof Error ? `Jira comment skipped: ${ce.message}` : "Jira comment skipped",
          );
        }
      } else if (key && !pr) {
        setJiraCommentNote(
          `Dry-run PR — paste a real PR URL on Incident Runbook to comment ${key}`,
        );
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Create PR failed");
    } finally {
      setLoading(false);
    }
  };

  const gates = active?.gates || active?.result?.gates || {};
  const canApprove =
    active &&
    ["awaiting_approval", "needs_human", "completed"].includes(active.status) &&
    !active.approved_at;
  const canCreatePr = Boolean(active?.approved_at) && !active?.pr_url;
  const currentPhase =
    [...(active?.events || [])].reverse().find((e: any) => e.phase)?.phase ||
    active?.current_agent ||
    "—";
  const stepIdx = workflowStepIndex(active);

  return (
    <div className="max-w-6xl mx-auto space-y-4 p-1" data-testid="mentrix-page">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-slate-900 text-teal-300">
          <Bot className="h-6 w-6" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Mentrix</h1>
          <p className="text-sm text-slate-600">
            Primary delivery — Lattice → Confirm plan → Build → Gates → Ultra Review → Approve → PR
            (scorecard: grounded plan + gates green)
          </p>
          {agents?.wake_phrases && (
            <p className="text-xs text-slate-500 mt-1">
              Wake: {agents.wake_phrases.join(" · ")} · Desktop: Ctrl/Cmd+Shift+Space
            </p>
          )}
        </div>
      </div>

      <div
        className="rounded-xl border border-slate-200 bg-white px-3 py-3 overflow-x-auto"
        data-testid="mentrix-step-rail"
      >
        <ol className="flex items-center gap-1 min-w-max">
          {WORKFLOW_STEPS.map((step, i) => {
            const done = stepIdx > i;
            const current = stepIdx === i;
            return (
              <li key={step.id} className="flex items-center gap-1">
                {i > 0 && (
                  <span
                    className={`w-6 h-px ${done || current ? "bg-teal-500" : "bg-slate-200"}`}
                    aria-hidden
                  />
                )}
                <span
                  data-testid={`mentrix-step-${step.id}`}
                  className={`rounded-full px-2.5 py-1 text-xs font-medium whitespace-nowrap ${
                    done
                      ? "bg-teal-100 text-teal-800"
                      : current
                        ? "bg-teal-700 text-white"
                        : "bg-slate-100 text-slate-500"
                  }`}
                >
                  {step.label}
                </span>
              </li>
            );
          })}
        </ol>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <div className="rounded-xl border border-slate-200 bg-white flex flex-col min-h-[520px]">
          <div
            className="flex-1 overflow-auto p-4 space-y-3"
            data-testid="mentrix-chat"
          >
            {messages.length === 0 && (
              <div className="text-sm text-slate-500 space-y-2" data-testid="mentrix-empty-state">
                <p>
                  <strong>Clone or Lattice-ingest once → engage.</strong> Workspace + project key
                  auto-fill from Repo Workspace when available.
                </p>
                <p>
                  No graph yet?{" "}
                  <Link to="/repo-workspace" className="text-teal-700 underline font-medium">
                    Repo Workspace
                  </Link>{" "}
                  or{" "}
                  <Link to="/lattice" className="text-teal-700 underline font-medium">
                    Lattice Graph
                  </Link>
                  , then describe your goal and Mentrix engage.
                </p>
              </div>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                className={
                  m.role === "user"
                    ? "ml-8 rounded-lg bg-teal-50 border border-teal-100 px-3 py-2 text-sm"
                    : m.role === "system"
                      ? "rounded-lg bg-amber-50 border border-amber-100 px-3 py-2 text-xs text-amber-900"
                      : "mr-8 rounded-lg bg-slate-50 border border-slate-100 px-3 py-2 text-sm"
                }
              >
                {m.meta && (
                  <div className="font-mono text-[10px] uppercase tracking-wide text-teal-800 mb-1">
                    {m.meta}
                  </div>
                )}
                <div className="whitespace-pre-wrap">{m.text}</div>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          <div className="border-t border-slate-200 p-4 space-y-3">
            <textarea
              ref={goalInputRef}
              data-testid="mentrix-goal"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              rows={3}
              placeholder="e.g. Port this C service to Java with REST parity and API evals"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            <div className="flex flex-wrap gap-2 items-center">
              <label className="text-xs text-slate-600 flex items-center gap-2">
                Jira issue
                <input
                  data-testid="mentrix-issue-key"
                  value={issueKey}
                  onChange={(e) => setIssueKey(e.target.value)}
                  placeholder="INC-123"
                  className="rounded border border-slate-300 px-2 py-1 text-sm w-28"
                />
              </label>
              {jiraCommentNote && (
                <span data-testid="mentrix-jira-comment-note" className="text-xs text-teal-700">
                  {jiraCommentNote}
                </span>
              )}
            </div>
            <div className="flex flex-wrap gap-4 text-xs text-slate-600">
              <label className="inline-flex items-center gap-2" data-testid="mentrix-tts-toggle">
                <input
                  type="checkbox"
                  checked={ttsEnabled}
                  onChange={(e) => setTtsEnabled(e.target.checked)}
                />
                Speak status (TTS)
              </label>
              {(window.zectDesktop?.isDesktopApp || wakeHint) && (
                <span data-testid="mentrix-stt-status">
                  {wakeHint ||
                    (sttListening
                      ? "listening for Hey Mentrix"
                      : "unavailable — use Ctrl+Shift+Space · set headset as Windows default mic")}
                </span>
              )}
            </div>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              <label className="block text-xs">
                <span className="text-slate-600">Mode</span>
                <select
                  data-testid="mentrix-mode"
                  value={mode}
                  onChange={(e) => setMode(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
                >
                  {MODES.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-xs">
                <span className="text-slate-600">Lattice project key</span>
                <input
                  data-testid="mentrix-project-key"
                  value={projectKey}
                  onChange={(e) => setProjectKey(e.target.value)}
                  placeholder="from Lattice ingest"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
                />
              </label>
              <label className="block text-xs">
                <span className="text-slate-600">Workspace path</span>
                <input
                  data-testid="mentrix-workspace"
                  value={workspace}
                  onChange={(e) => setWorkspace(e.target.value)}
                  placeholder="local repo path"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
                />
              </label>
              <label className="block text-xs">
                <span className="text-slate-600">Source language</span>
                <input
                  value={sourceLang}
                  onChange={(e) => setSourceLang(e.target.value)}
                  placeholder="optional"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
                />
              </label>
              <label className="block text-xs">
                <span className="text-slate-600">Target language</span>
                <input
                  value={targetLang}
                  onChange={(e) => setTargetLang(e.target.value)}
                  placeholder="optional"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
                />
              </label>
            </div>
            <button
              data-testid="mentrix-engage"
              onClick={start}
              disabled={!goal.trim() || loading}
              className="inline-flex items-center gap-2 rounded-lg bg-teal-700 px-4 py-2 text-white disabled:opacity-50 text-sm"
            >
              <Play className="h-4 w-4" />
              Mentrix engage
            </button>
          </div>
        </div>

        <div className="space-y-4">
          <div
            className="rounded-xl border border-slate-200 bg-white p-4 space-y-3"
            data-testid="mentrix-live-status"
          >
            <h2 className="font-semibold text-sm flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-teal-600" />
              Live status
            </h2>
            {!active ? (
              <p className="text-sm text-slate-500">Start a run to see phases.</p>
            ) : (
              <>
                <div className="text-sm" data-testid="mentrix-run-status">
                  <div>
                    <span className="text-slate-500">Status:</span>{" "}
                    <span className="font-medium">{active.status}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Phase:</span>{" "}
                    <span className="text-teal-700" data-testid="mentrix-phase">
                      {currentPhase}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500">Next:</span> {active.next_step || "—"}
                  </div>
                </div>
                {active.status === "awaiting_plan_confirm" && (
                  <div
                    className="rounded-lg border border-teal-200 bg-teal-50/50 p-3 space-y-2"
                    data-testid="mentrix-plan-confirm"
                  >
                    <div className="font-semibold text-sm text-teal-900">Confirm plan before Build</div>
                    <p className="text-xs text-slate-600">
                      Edit the grounded plan if needed, then confirm. Build will not start until you confirm.
                    </p>
                    <textarea
                      data-testid="mentrix-plan-summary"
                      value={planSummary}
                      onChange={(e) => setPlanSummary(e.target.value)}
                      rows={5}
                      className="w-full rounded border border-slate-300 px-2 py-1.5 text-xs font-mono"
                    />
                    {(active.result?.plan?.steps || []).length > 0 && (
                      <ol className="text-xs text-slate-700 list-decimal pl-4 space-y-0.5 max-h-28 overflow-auto">
                        {(active.result.plan.steps as any[]).slice(0, 12).map((s, i) => (
                          <li key={i}>{s.title || s.action || s.step || JSON.stringify(s)}</li>
                        ))}
                      </ol>
                    )}
                    <button
                      type="button"
                      data-testid="mentrix-confirm-plan"
                      onClick={() => void confirmPlan()}
                      disabled={loading}
                      className="inline-flex items-center gap-2 rounded-lg bg-teal-700 px-3 py-2 text-white text-xs disabled:opacity-40"
                    >
                      <Check className="h-3.5 w-3.5" />
                      Confirm plan and continue
                    </button>
                  </div>
                )}
                <div
                  className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs space-y-1"
                  data-testid="mentrix-gates"
                >
                  <div className="font-semibold text-slate-700">
                    Gates (grounded plan + gates green to ship)
                  </div>
                  <div>plan_confirmed: {String(gates.plan_confirmed ?? "—")}</div>
                  <div>lint_ok: {String(gates.lint_ok ?? "—")}</div>
                  <div>sandbox_ready: {String(gates.sandbox_ready ?? "—")}</div>
                  <div>review_ok: {String(gates.review_ok ?? "—")}</div>
                  <div>incomplete_ok: {String(gates.incomplete_ok ?? "—")}</div>
                  <div>grounding_ok: {String(gates.grounding_ok ?? "—")}</div>
                  <div>contract_ok: {String(gates.contract_ok ?? "—")}</div>
                  <div>acceptance_ok: {String(gates.acceptance_ok ?? "—")}</div>
                  <div>api_eval_ok: {String(gates.api_eval_ok ?? "—")}</div>
                  <div>sast_ok: {String(gates.sast_ok ?? "—")}</div>
                  {active.pr_url && (
                    <div className="text-teal-800 break-all">PR: {active.pr_url}</div>
                  )}
                </div>
                <label className="flex items-center gap-2 text-xs">
                  <input
                    type="checkbox"
                    data-testid="mentrix-acknowledge"
                    checked={ack}
                    onChange={(e) => setAck(e.target.checked)}
                  />
                  Acknowledge issues (override sandbox / Ultra Review / API eval — not plan/SAST/security)
                </label>
                <div className="flex flex-wrap gap-2">
                  <button
                    data-testid="mentrix-approve"
                    onClick={approve}
                    disabled={!canApprove || loading || active.status === "awaiting_plan_confirm"}
                    className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-3 py-2 text-white text-xs disabled:opacity-40"
                  >
                    <Check className="h-3.5 w-3.5" />
                    Approve
                  </button>
                  <button
                    data-testid="mentrix-create-pr"
                    onClick={createPr}
                    disabled={!canCreatePr || loading}
                    className="inline-flex items-center gap-2 rounded-lg bg-teal-700 px-3 py-2 text-white text-xs disabled:opacity-40"
                  >
                    <GitPullRequest className="h-3.5 w-3.5" />
                    Create PR
                  </button>
                </div>
              </>
            )}
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="font-semibold text-sm mb-2">Recent runs</h2>
            <ul className="space-y-2 max-h-64 overflow-auto" data-testid="mentrix-run-list">
              {runs.map((r) => (
                <li key={r.id}>
                  <button
                    onClick={() => openRun(r.id)}
                    className="w-full text-left rounded-lg border border-slate-200 px-3 py-2 hover:bg-slate-50"
                  >
                    <div className="text-sm font-medium">
                      #{r.id} · {r.mode}
                    </div>
                    <div className="text-xs text-slate-500 truncate">{r.goal}</div>
                    <div className="text-xs text-teal-700">
                      {r.status} · {r.next_step || r.current_agent}
                    </div>
                  </button>
                </li>
              ))}
              {runs.length === 0 && <p className="text-sm text-slate-500">No runs yet.</p>}
            </ul>
          </div>
        </div>
      </div>

      {error && (
        <div
          data-testid="mentrix-error"
          className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {error}
        </div>
      )}

      {active?.events?.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-4" data-testid="mentrix-active-run">
          <h2 className="font-semibold text-sm mb-2">Phase events</h2>
          <ul className="space-y-2 max-h-48 overflow-auto" data-testid="mentrix-events">
            {(active.events || []).map((ev: any, i: number) => (
              <li key={i} className="rounded-lg bg-slate-50 px-3 py-2 text-sm">
                <span className="font-mono text-xs text-teal-800">
                  {ev.agent}
                  {ev.phase ? ` · ${ev.phase}` : ""}
                  {ev.event ? ` · ${ev.event}` : ""}
                  {ev.next_step ? ` → ${ev.next_step}` : ""}
                </span>
                <div>{ev.message}</div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
