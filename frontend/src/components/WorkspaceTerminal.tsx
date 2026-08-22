import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, Play, Plus, Square, Terminal, X } from "lucide-react";
import { runnerExecute, runnerOutput, runnerStart, runnerStop, codingAgentRuntimeRecipes, type RuntimeRecipe } from "@/lib/api";
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
  onCloseSession?: (id: string) => void;
  onClosePanel?: () => void;
  runAppTick?: number;
  runAppRecipeId?: string | null;
};

const FALLBACK_APP_CMD = "npm run dev";

function joinCwd(root: string, cwdRel: string): string {
  const rel = (cwdRel || ".").replace(/\\/g, "/");
  if (!rel || rel === ".") return root;
  if (rel.split("/").includes("..")) return root;
  return `${root.replace(/[\\/]+$/, "")}/${rel}`;
}

/**
 * Per-root command forms: each session cwd is locked. This is App Runner, not a Cursor PTY.
 * Switching the Explorer root does not retarget an existing terminal.
 */
export default function WorkspaceTerminal({
  workspaceRoot,
  sessions,
  activeSessionId,
  roots = [],
  onSelectSession,
  onCreateSession,
  onCloseSession,
  onClosePanel,
  runAppTick = 0,
  runAppRecipeId = null,
}: WorkspaceTerminalProps) {
  const active = sessions?.find((s) => s.id === activeSessionId) || sessions?.[0] || null;
  const root = (active?.rootPath || workspaceRoot || roots[0]?.rootPath || "").trim();
  const label = active?.label || roots[0]?.label || "";
  const [command, setCommand] = useState("");
  const [linesById, setLinesById] = useState<Record<string, string[]>>({});
  const [busy, setBusy] = useState(false);
  const [bgId, setBgId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const key = active?.id || "default";
  const lines = linesById[key] || [];
  const [recipes, setRecipes] = useState<RuntimeRecipe[]>([]);
  const [defaultRecipeId, setDefaultRecipeId] = useState("");
  const [selectedRecipeId, setSelectedRecipeId] = useState("");
  const [recipesReady, setRecipesReady] = useState(false);

  const focusInput = () => {
    if (!root || busy) return;
    inputRef.current?.focus();
  };

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [lines]);

  useEffect(() => {
    if (!bgId) return;
    let cancelled = false;
    let offset = 0;
    const poll = async () => {
      try {
        const data = await runnerOutput(bgId, offset, 200);
        if (cancelled) return;
        const chunk = Array.isArray(data.lines) ? data.lines.map((l: unknown) => String(l)) : [];
        if (chunk.length) {
          offset += chunk.length;
          setLinesById((prev) => ({ ...prev, [key]: [...(prev[key] || []), ...chunk] }));
        }
        if (data.running === false) {
          setLinesById((prev) => ({
            ...prev,
            [key]: [...(prev[key] || []), `[exited] code ${data.exit_code ?? "—"}`],
          }));
          setBgId(null);
        }
      } catch {
        /* process gone or runner unavailable */
      }
    };
    void poll();
    const timer = window.setInterval(() => void poll(), 2000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [bgId, key]);

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

  const startBg = async (cmdOverride?: string, cwdOverride?: string) => {
    const cmd = (cmdOverride ?? command).trim();
    if (!cmd || busy || !root) return;
    const cwd = cwdOverride && !cwdOverride.split(/[\\/]/).includes("..") ? cwdOverride : root;
    setBusy(true);
    append(["", `[starting] ${cmd} (cwd ${cwd})`]);
    try {
      const result = await runnerStart(cmd, cwd, "workspace-terminal", undefined, root);
      setBgId(result.id);
      append(`[started] ${result.id}${result.pid != null ? ` pid=${result.pid}` : ""} — output streams here. Stop to kill.`);
    } catch (e) {
      append(`[error] ${e instanceof Error ? e.message : "start failed"}`);
    } finally {
      setCommand("");
      setBusy(false);
    }
  };

  const startRecipe = async (recipe: RuntimeRecipe) => {
    if (recipe.confirmRequired) {
      const ok = window.confirm(
        `Run ${recipe.label || recipe.command}?\n\nCommand: ${recipe.command}\nCwd: ${recipe.cwdRel}\n${recipe.evidence || ""}\n\nZECT does not start PostgreSQL. Use the project's local DATABASE_URL.`,
      );
      if (!ok) return;
    }
    await startBg(recipe.command, joinCwd(root, recipe.cwdRel));
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

  const startRecipeRef = useRef(startRecipe);
  startRecipeRef.current = startRecipe;
  const recipesRef = useRef(recipes);
  recipesRef.current = recipes;
  const appliedRunTick = useRef(0);

  useEffect(() => {
    if (!root) {
      setRecipes([]);
      setRecipesReady(true);
      return;
    }
    let cancelled = false;
    setRecipesReady(false);
    void codingAgentRuntimeRecipes(root)
      .then((out) => {
        if (cancelled) return;
        if (out.ok) {
          setRecipes(out.recipes || []);
          setDefaultRecipeId(out.default_id || out.recipes?.[0]?.id || "");
          setSelectedRecipeId((prev) => prev || out.default_id || out.recipes?.[0]?.id || "");
        } else {
          setRecipes([]);
        }
        setRecipesReady(true);
      })
      .catch(() => {
        if (!cancelled) {
          setRecipes([]);
          setRecipesReady(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [root]);

  useEffect(() => {
    if (!runAppTick || appliedRunTick.current === runAppTick) return;
    if (!recipesReady) return;
    appliedRunTick.current = runAppTick;
    const id = runAppRecipeId || selectedRecipeId || defaultRecipeId;
    const recipe = recipesRef.current.find((r) => r.id === id) || recipesRef.current[0];
    if (recipe) void startRecipeRef.current(recipe);
    else void startBg(FALLBACK_APP_CMD, root);
  }, [runAppTick, runAppRecipeId, selectedRecipeId, defaultRecipeId, root, recipesReady]);

  const showSessionBar = Boolean((sessions && sessions.length > 0) || roots.length);

  return (
    <div
      className="flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-lg border border-slate-200 bg-slate-950 text-slate-100"
      data-testid="workspace-terminal"
      data-locked-root={root || ""}
      onMouseDown={(e) => {
        const el = e.target as HTMLElement;
        if (el.closest("button, a, select, input, textarea, label")) return;
        focusInput();
      }}
    >
      <div className="flex shrink-0 items-center justify-between gap-2 border-b border-slate-800 px-3 py-1.5 text-[11px] text-slate-400">
        <span className="inline-flex min-w-0 items-center gap-1.5 font-medium text-slate-300">
          <Terminal className="h-3.5 w-3.5" />
          Terminal
        </span>
        <span
          className="min-w-0 truncate font-mono"
          title={root || undefined}
          data-testid="workspace-terminal-cwd"
        >
          {label ? `${label} · ` : ""}cwd: {root || "(none)"}
          {root ? " — locked root, not a PTY" : ""}
        </span>
        {onClosePanel ? (
          <button
            type="button"
            className="shrink-0 rounded p-0.5 text-slate-400 hover:bg-slate-800 hover:text-white"
            data-testid="workspace-terminal-close-panel"
            title="Close terminal panel"
            aria-label="Close terminal panel"
            onClick={onClosePanel}
          >
            <X className="h-3.5 w-3.5" />
          </button>
        ) : null}
      </div>
      {showSessionBar ? (
        <div className="flex shrink-0 flex-wrap items-center gap-1 border-b border-slate-800 px-2 py-1">
          {(sessions || []).map((s) => (
            <span
              key={s.id}
              className={`inline-flex items-center rounded ${
                s.id === key ? "bg-teal-800 text-white" : "text-slate-400 hover:bg-slate-800"
              }`}
            >
              <button
                type="button"
                data-testid={`workspace-terminal-tab-${s.repoId}`}
                onClick={() => onSelectSession?.(s.id)}
                className="rounded px-1.5 py-0.5 text-[10px]"
              >
                {s.label}
              </button>
              {onCloseSession ? (
                <button
                  type="button"
                  className="px-1 py-0.5 text-slate-400 hover:text-rose-300"
                  data-testid={`workspace-terminal-tab-close-${s.repoId}`}
                  title="Close this terminal session"
                  aria-label={`Close ${s.label}`}
                  onClick={() => onCloseSession(s.id)}
                >
                  <X className="h-3 w-3" />
                </button>
              ) : null}
            </span>
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
        className="flex-1 min-h-0 overflow-auto px-3 py-2 font-mono text-[11px] leading-relaxed whitespace-pre-wrap"
        data-testid="workspace-terminal-output"
      >
        {!root ? (
          <div className="text-amber-200/90 space-y-2" data-testid="workspace-terminal-no-root">
            <p>This is a command form (not a Cursor-style PTY). Input stays disabled until a workspace root is attached.</p>
            <p>
              Cursor-style “Add folder to workspace” is <strong>Project → Open local git</strong>{" "}
              (register-local), not an untitled multi-root IDE window.
            </p>
            <Link
              to="/projects"
              className="inline-flex items-center rounded border border-teal-700 px-2 py-1 text-[11px] text-teal-200 hover:bg-teal-950"
              data-testid="workspace-terminal-attach-root"
            >
              Attach a git root
            </Link>
          </div>
        ) : lines.length === 0 ? (
          <div className="space-y-2 text-slate-400" data-testid="workspace-terminal-help">
            <p>This folder is the locked root — not a PTY. Commands run here via App Runner.</p>
            <p>Not a live Cursor shell. Commands run under this locked root via App Runner.</p>
            <p>
              <strong className="text-slate-300">Run</strong> = one-shot, 30 seconds (<code>git status</code>).{" "}
              <strong className="text-slate-300">Start app / BG</strong> = long-running discovered recipe (not hardcoded <code>npm run dev</code> at clone root).
              Mentrix chat cannot spawn a PTY. Postgres is never started by ZECT.
            </p>
            <p>
              Preview and process list:{" "}
              <Link to="/app-runner" className="text-teal-300 underline" data-testid="workspace-terminal-app-runner">
                App Runner
              </Link>
            </p>
          </div>
        ) : (
          lines.map((line, i) => <div key={`${i}-${line.slice(0, 24)}`}>{line}</div>)
        )}
      </div>
      <form
        className="relative z-20 flex shrink-0 flex-wrap items-center gap-1 border-t border-slate-800 bg-slate-950 p-2 pointer-events-auto"
        onSubmit={(e) => {
          e.preventDefault();
          void runOnce();
        }}
      >
        <span className="text-teal-400 font-mono text-xs">$</span>
        <input
          ref={inputRef}
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          disabled={!root || busy}
          placeholder={root ? "Type a command, then Run or Start app" : "No workspace root — attach a git folder on the Project"}
          title={!root ? "Attach a git root: Project → Open local git (register-local)" : "Command form: Run = 30s; Start app / BG = long-running"}
          className="min-h-9 min-w-0 flex-1 bg-transparent px-1 py-2 font-mono text-xs text-slate-100 outline-none placeholder:text-slate-500 pointer-events-auto"
          data-testid="workspace-terminal-input"
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
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
        {recipes.length ? (
          <select
            value={selectedRecipeId || defaultRecipeId}
            onChange={(e) => setSelectedRecipeId(e.target.value)}
            className="max-w-[10rem] rounded border border-slate-700 bg-slate-900 px-1 py-1 text-[10px] text-slate-200"
            data-testid="workspace-terminal-recipe"
            title="Discovered Run App recipes — confirm before execute"
          >
            {recipes.map((r) => (
              <option key={r.id} value={r.id}>
                {r.label || r.command} · {r.cwdRel || "."}
              </option>
            ))}
          </select>
        ) : null}
        <button
          type="button"
          disabled={!root || busy}
          onClick={() => {
            const recipe = recipes.find((r) => r.id === (selectedRecipeId || defaultRecipeId)) || recipes[0];
            if (recipe) void startRecipe(recipe);
            else void startBg(FALLBACK_APP_CMD, root);
          }}
          className="rounded px-2 py-1 text-[11px] border border-teal-700 text-teal-200 disabled:opacity-40"
          data-testid="workspace-terminal-start-app"
          title="Start the confirmed Run App recipe (App Runner). Not a Cursor PTY."
        >
          Start app
        </button>
        <button
          type="button"
          disabled={!root || busy || !command.trim()}
          onClick={() => void startBg()}
          className="rounded px-2 py-1 text-[11px] border border-slate-600 text-slate-300 disabled:opacity-40"
          data-testid="workspace-terminal-start"
          title="Background process — use for servers that do not exit"
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
