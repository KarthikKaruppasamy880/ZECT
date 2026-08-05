import { useEffect, useRef, useState } from "react";
import { Loader2, Play, Square, Terminal } from "lucide-react";
import { runnerExecute, runnerStart, runnerStop } from "@/lib/api";

type WorkspaceTerminalProps = {
  /** Active Mentrix / Active Project root — commands run with this cwd only. */
  workspaceRoot: string;
};

/**
 * Phase 3 Stage B — workspace-scoped terminal via App Runner APIs.
 * Always passes workspaceRoot as cwd; refuses to run without a root.
 */
export default function WorkspaceTerminal({ workspaceRoot }: WorkspaceTerminalProps) {
  const root = (workspaceRoot || "").trim();
  const [command, setCommand] = useState("");
  const [lines, setLines] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [bgId, setBgId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [lines]);

  const append = (chunk: string | string[]) => {
    const next = Array.isArray(chunk) ? chunk : [chunk];
    setLines((prev) => [...prev, ...next]);
  };

  const runOnce = async () => {
    const cmd = command.trim();
    if (!cmd || busy) return;
    if (!root) {
      append("[error] No workspace root — set Active Project or Mentrix workspace");
      return;
    }
    setBusy(true);
    append(["", `$ ${cmd}`]);
    try {
      const result = await runnerExecute(cmd, root, 30);
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
      const result = await runnerStart(cmd, root, "workspace-terminal");
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
    >
      <div className="flex items-center justify-between gap-2 border-b border-slate-800 px-3 py-1.5 text-[11px] text-slate-400">
        <span className="inline-flex items-center gap-1.5 font-medium text-slate-300">
          <Terminal className="h-3.5 w-3.5" />
          Terminal
        </span>
        <span className="truncate font-mono" title={root || undefined}>
          cwd: {root || "(none)"}
        </span>
      </div>
      <div
        ref={scrollRef}
        className="flex-1 overflow-auto px-3 py-2 font-mono text-[11px] leading-relaxed whitespace-pre-wrap"
        data-testid="workspace-terminal-output"
      >
        {lines.length === 0 ? (
          <span className="text-slate-500">Commands run only under the workspace root via App Runner.</span>
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
