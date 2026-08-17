import { useEffect, useRef, useState } from "react";
import { Loader2, Play, Plus, Square, Terminal } from "lucide-react";
import { runnerExecute, runnerStart, runnerStop } from "@/lib/api";
import type { WorkspaceTerminalSession } from "@/lib/workspaceSession";

type RootChoice = { repoId: number; rootPath: string; label: string };

type WorkspaceTerminalProps = {
  /** @deprecated Prefer sessions; kept so a locked session cwd never silently retargets. */
  workspaceRoot: string;
  sessions?: WorkspaceTerminalSession[];
  activeSessionId?: string | null;
  roots?: RootChoice[];
  onSelectSession?: (id: string) => void;
  onCreateSession?: (root: RootChoice) => void;
};

/**
 * Per-root terminals: each session cwd is locked. Switching the Explorer root
 * does not retarget an existing terminal.
 */
export default function WorkspaceTerminal({
  workspaceRoot,
  sessions,
  activeSessionId,
  roots = [],
  onSelectSession,
  onCreateSession,
}: WorkspaceTerminalProps) {
  const active = sessions?.find((s) => s.id === activeSessionId) || sessions?.[0] || null;
  const root = (active?.rootPath || workspaceRoot || "").trim();
  const label = active?.label || "";
  const [command, setCommand] = useState("");
  const [linesById, setLinesById] = useState<Record<string, string[]>>({});
  const [busy, setBusy] = useState(false);
  const [bgId, setBgId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const key = active?.id || "default";
  const lines = linesById[key] || [];

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [lines]);

  const append = (chunk: string | string[]) => {
    const next = Array.isArray(chunk) ? chunk : [chunk];
    setLinesById((prev) => ({ ...prev, [key]: [...(prev[key] || []), ...next] }));
  };

  const runOnce = async () => {
    const cmd = command.trim();
    if (!cmd || busy) return;
    if (!root) {
      append("[error] No workspace root — pick an authorized root for this terminal");
      return;
    }
    setBusy(true);
    append(["", `$ ${cmd}`]);
    try {
      const result = await runnerExecute(cmd, root, 30, root);
      if (result.stdout) append(String(result.stdout).split("\n"));
      if (result.stderr) {
        append(String(result.stderr).split("\n").map((l: string) => `[stderr] ${l}`));
      }
      if (result.exit_code !== 0) append(`[exit code: ${result.exit_code}]`);
    } catch (e) {
      append(`[error] ${e instanceof Error ? e.message : "execute failed"}`);
    } finally {
      setCommand("");
      setBusy(false);
    }
  };

  const startBg = async () => {
    const cmd = command.trim();
    if (!cmd || busy || !root) return;
    setBusy(true);
    append(["", `[starting] ${cmd}`]);
    try {
      const result = await runnerStart(cmd, root, "workspace-terminal", undefined, root);
      setBgId(result.id);
      append(`[started] ${result.id}${result.pid != null ? ` pid=${result.pid}` : ""}`);
    } catch (e) {
      append(`[error] ${e instanceof Error ? e.message : "start failed"}`);
    } finally {
      setCommand("");
      setBusy(false);
    }
  };

  const stopBg = async () => {
    if (!bgId) return;
    try {
      await runnerStop(bgId);
      append(`[stopped] ${bgId}`);
      setBgId(null);
    } catch (e) {
      append(`[error] ${e instanceof Error ? e.message : "stop failed"}`);
    }
  };

  return (
    <div
      className="flex flex-col h-full min-h-[180px] rounded-lg border border-slate-200 bg-slate-950 text-slate-100"
      data-testid="workspace-terminal"
      data-locked-root={root || ""}
    >
      <div className="flex items-center justify-between gap-2 border-b border-slate-800 px-3 py-1.5 text-[11px] text-slate-400">
        <span className="inline-flex items-center gap-1.5 font-medium text-slate-300">
          <Terminal className="h-3.5 w-3.5" />
          Terminal
        </span>
        <span
          className="truncate font-mono"
          title={root || undefined}
          data-testid="workspace-terminal-cwd"
        >
          {label ? `${label} · ` : ""}cwd: {root || "(none)"}
        </span>
      </div>
      {sessions && sessions.length > 0 ? (
        <div className="flex flex-wrap items-center gap-1 border-b border-slate-800 px-2 py-1">
          {sessions.map((s) => (
            <button
              key={s.id}
              type="button"
              data-testid={`workspace-terminal-tab-${s.repoId}`}
              onClick={() => onSelectSession?.(s.id)}
              className={`rounded px-1.5 py-0.5 text-[10px] ${
                s.id === key ? "bg-teal-800 text-white" : "text-slate-400 hover:bg-slate-800"
              }`}
            >
              {s.label}
            </button>
          ))}
          {roots.length ? (
            <label className="ml-auto inline-flex items-center gap-1 text-[10px] text-slate-400">
              <Plus className="h-3 w-3" />
              <select
                data-testid="workspace-terminal-new-root"
                className="bg-slate-900 text-slate-200 text-[10px] rounded border border-slate-700"
                defaultValue=""
                onChange={(e) => {
                  const repoId = Number(e.target.value);
                  const hit = roots.find((r) => r.repoId === repoId);
                  if (hit) onCreateSession?.(hit);
                  e.target.value = "";
                }}
              >
                <option value="">New terminal…</option>
                {roots.map((r) => (
                  <option key={r.repoId} value={r.repoId}>
                    {r.label}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
        </div>
      ) : null}
      <div
        ref={scrollRef}
        className="flex-1 overflow-auto px-3 py-2 font-mono text-[11px] leading-relaxed whitespace-pre-wrap"
        data-testid="workspace-terminal-output"
      >
        {lines.length === 0 ? (
          <span className="text-slate-500">Commands run only under this terminal's locked root via App Runner.</span>
        ) : (
          lines.map((line, i) => <div key={`${i}-${line.slice(0, 24)}`}>{line}</div>)
        )}
      </div>
      <form
        className="flex items-center gap-1 border-t border-slate-800 p-2"
        onSubmit={(e) => {
          e.preventDefault();
          void runOnce();
        }}
      >
        <span className="text-teal-400 font-mono text-xs">$</span>
        <input
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          disabled={!root || busy}
          placeholder={root ? "command…" : "set workspace root first"}
          className="flex-1 min-w-0 bg-transparent text-xs font-mono text-slate-100 outline-none placeholder:text-slate-600"
          data-testid="workspace-terminal-input"
          autoComplete="off"
        />
        <button
          type="submit"
          disabled={!root || busy || !command.trim()}
          className="inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] bg-teal-700 text-white disabled:opacity-40"
          data-testid="workspace-terminal-run"
        >
          {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
          Run
        </button>
        <button
          type="button"
          disabled={!root || busy || !command.trim()}
          onClick={() => void startBg()}
          className="rounded px-2 py-1 text-[11px] border border-slate-600 text-slate-300 disabled:opacity-40"
          data-testid="workspace-terminal-start"
        >
          BG
        </button>
        {bgId && (
          <button
            type="button"
            onClick={() => void stopBg()}
            className="inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] border border-red-800 text-red-300"
            data-testid="workspace-terminal-stop"
          >
            <Square className="h-3 w-3" />
            Stop
          </button>
        )}
      </form>
    </div>
  );
}
