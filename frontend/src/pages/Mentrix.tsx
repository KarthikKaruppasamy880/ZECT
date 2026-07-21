import { useEffect, useRef, useState } from "react";
import { Bot, Check, GitPullRequest, Play, Sparkles } from "lucide-react";
import {
  mentrixAgents,
  mentrixApproveRun,
  mentrixCreatePr,
  mentrixGetRun,
  mentrixListRuns,
  mentrixStartRun,
} from "@/lib/api";

const MODES = ["upgrade", "chat", "understand", "deliver", "review_only", "ops"];

type ChatMsg = {
  role: "user" | "assistant" | "system";
  text: string;
  meta?: string;
};

export default function Mentrix() {
  const [goal, setGoal] = useState("");
  const [mode, setMode] = useState("upgrade");
  const [projectKey, setProjectKey] = useState("");
  const [workspace, setWorkspace] = useState("");
  const [sourceLang, setSourceLang] = useState("");
  const [targetLang, setTargetLang] = useState("");
  const [agents, setAgents] = useState<any>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [active, setActive] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [ack, setAck] = useState(false);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const pollRef = useRef<number | null>(null);
  const chatEndRef = useRef<HTMLDivElement | null>(null);

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
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, active?.events?.length]);

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
    setLoading(true);
    try {
      const run = await mentrixCreatePr(active.id, { dry_run: true });
      setActive(run);
      setMessages(eventsToMessages(run));
      await refresh();
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

  return (
    <div className="max-w-6xl mx-auto space-y-4 p-1" data-testid="mentrix-page">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-slate-900 text-teal-300">
          <Bot className="h-6 w-6" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Mentrix</h1>
          <p className="text-sm text-slate-600">
            Unified agent chat — Lattice → Blueprint → Ask/Plan → Mentrix Ultra Review → Build →
            gates → Approve → PR
          </p>
          {agents?.wake_phrases && (
            <p className="text-xs text-slate-500 mt-1">
              Wake: {agents.wake_phrases.join(" · ")}
            </p>
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <div className="rounded-xl border border-slate-200 bg-white flex flex-col min-h-[520px]">
          <div
            className="flex-1 overflow-auto p-4 space-y-3"
            data-testid="mentrix-chat"
          >
            {messages.length === 0 && (
              <p className="text-sm text-slate-500">
                Describe an upgrade goal (any language → any language). Mentrix will stream phase
                status here.
              </p>
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
              data-testid="mentrix-goal"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              rows={3}
              placeholder="e.g. Port this C service to Java with REST parity and API evals"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
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
                <div
                  className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs space-y-1"
                  data-testid="mentrix-gates"
                >
                  <div className="font-semibold text-slate-700">Gates (100% green to ship)</div>
                  <div>lint_ok: {String(gates.lint_ok ?? "—")}</div>
                  <div>sandbox_ready: {String(gates.sandbox_ready ?? "—")}</div>
                  <div>review_ok: {String(gates.review_ok ?? "—")}</div>
                  <div>incomplete_ok: {String(gates.incomplete_ok ?? "—")}</div>
                  <div>grounding_ok: {String(gates.grounding_ok ?? "—")}</div>
                  <div>contract_ok: {String(gates.contract_ok ?? "—")}</div>
                  <div>acceptance_ok: {String(gates.acceptance_ok ?? "—")}</div>
                  <div>api_eval_ok: {String(gates.api_eval_ok ?? "—")}</div>
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
                  Acknowledge issues (override sandbox / Ultra Review / API eval)
                </label>
                <div className="flex flex-wrap gap-2">
                  <button
                    data-testid="mentrix-approve"
                    onClick={approve}
                    disabled={!canApprove || loading}
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
