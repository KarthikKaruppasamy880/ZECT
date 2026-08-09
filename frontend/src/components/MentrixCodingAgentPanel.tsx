/**
 * Mentrix Coding Agent panel — Cursor-class chat + tool/diff stream for Developer Workspace.
 */
import { useEffect, useRef, useState } from "react";
import { Bot, Loader2, Send, Square, Check, X } from "lucide-react";
import ModelSelector from "@/components/ModelSelector";
import {
  codingAgentApprove,
  codingAgentCancel,
  codingAgentCreateSession,
  codingAgentStream,
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
};

type Line = {
  id: string;
  kind: "user" | "event";
  text: string;
  event?: string;
  path?: string;
  actionId?: string;
};

export default function MentrixCodingAgentPanel({
  workspaceRoot,
  model = "gpt-4o-mini",
  onModelChange,
  onOpenPath,
  onFilesChanged,
  initialGoal = "",
  initialSessionId = null,
}: Props) {
  const [goal, setGoal] = useState(initialGoal);
  const [sessionId, setSessionId] = useState<string | null>(initialSessionId);
  const [status, setStatus] = useState("idle");
  const [lines, setLines] = useState<Line[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chatModel, setChatModel] = useState(model);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const writtenRef = useRef<string[]>([]);

  useEffect(() => {
    setChatModel(model);
  }, [model]);

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
    <div
      className="flex h-full min-h-[200px] flex-col rounded-lg border border-slate-200 bg-white"
      data-testid="mentrix-coding-agent-panel"
    >
      <div className="flex items-center justify-between gap-2 border-b border-slate-100 px-3 py-2">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-800">
          <Bot className="h-3.5 w-3.5 text-teal-700" />
          Mentrix Coding Agent
          <span className="font-normal text-slate-400" data-testid="mentrix-coding-agent-status">
            · {status}
          </span>
        </div>
        <div className="scale-90 origin-right">
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

      <div className="flex-1 space-y-2 overflow-auto px-3 py-2 text-xs" data-testid="mentrix-coding-agent-log">
        {lines.length === 0 ? (
          <p className="text-slate-500">
            Ask Mentrix to build or fix code in this workspace. It can read, search, edit, and run commands.
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
        <p className="px-3 text-[11px] text-rose-600" data-testid="mentrix-coding-agent-error">
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
    </div>
  );
}
