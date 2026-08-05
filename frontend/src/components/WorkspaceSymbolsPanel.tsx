import { useCallback, useEffect, useState } from "react";
import { Code2, Loader2, Search } from "lucide-react";
import { getFileSymbols, searchCodeSymbols } from "@/lib/api";
import { normalizePath, relativeToRoot } from "@/lib/workspacePaths";

export type SymbolJumpTarget = {
  filePath: string;
  line: number;
  name: string;
};

type WorkspaceSymbolsPanelProps = {
  workspaceRoot: string;
  openFilePath: string;
  repoId?: number | null;
  onJump: (target: SymbolJumpTarget) => void;
};

type Sym = {
  symbol_name?: string;
  symbol_type?: string;
  file_path?: string;
  line_start?: number;
  signature?: string;
};

/**
 * Phase 3 Stage E — symbol search + open-file outline with jump-to-line.
 */
export default function WorkspaceSymbolsPanel({
  workspaceRoot,
  openFilePath,
  repoId,
  onJump,
}: WorkspaceSymbolsPanelProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Sym[]>([]);
  const [outline, setOutline] = useState<Sym[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const resolvePath = (filePath: string): string => {
    const n = normalizePath(filePath);
    if (!n) return "";
    if (n.startsWith("/") || /^[a-z]:\//i.test(n)) return n;
    const root = normalizePath(workspaceRoot);
    return `${root}/${n}`.replace(/\/+/g, "/");
  };

  const loadOutline = useCallback(async () => {
    if (!openFilePath) {
      setOutline([]);
      return;
    }
    const rel = relativeToRoot(openFilePath, workspaceRoot) || openFilePath;
    try {
      const items = await getFileSymbols(rel, repoId ?? undefined);
      // Also try absolute path if relative missed
      if (Array.isArray(items) && items.length) {
        setOutline(items);
        return;
      }
      const abs = await getFileSymbols(openFilePath, repoId ?? undefined);
      setOutline(Array.isArray(abs) ? abs : []);
    } catch {
      setOutline([]);
    }
  }, [openFilePath, workspaceRoot, repoId]);

  useEffect(() => {
    void loadOutline();
  }, [loadOutline]);

  const search = async () => {
    const q = query.trim();
    if (!q) return;
    setBusy(true);
    setError("");
    try {
      const items = await searchCodeSymbols(q, undefined, undefined, repoId ?? undefined, 40);
      setResults(Array.isArray(items) ? items : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
      setResults([]);
    } finally {
      setBusy(false);
    }
  };

  const jump = (s: Sym) => {
    const line = Number(s.line_start) || 1;
    const name = s.symbol_name || "?";
    const filePath = resolvePath(s.file_path || openFilePath);
    if (!filePath) return;
    onJump({ filePath, line, name });
  };

  const renderList = (items: Sym[], testId: string) =>
    items.length === 0 ? (
      <p className="text-[11px] text-slate-500 px-1 py-2">None</p>
    ) : (
      <ul className="space-y-0.5" data-testid={testId}>
        {items.map((s, i) => (
          <li key={`${s.file_path}-${s.symbol_name}-${s.line_start}-${i}`}>
            <button
              type="button"
              onClick={() => jump(s)}
              className="w-full text-left rounded px-1.5 py-1 text-[11px] hover:bg-slate-50"
              data-testid="workspace-symbol-item"
            >
              <div className="font-medium text-slate-800 truncate">
                {s.symbol_name}
                <span className="ml-1 font-normal text-slate-400">{s.symbol_type}</span>
              </div>
              <div className="font-mono text-[10px] text-slate-500 truncate">
                {s.file_path}:{s.line_start}
              </div>
            </button>
          </li>
        ))}
      </ul>
    );

  return (
    <div
      className="flex flex-col h-full min-h-[180px] rounded-lg border border-slate-200 bg-white overflow-hidden"
      data-testid="workspace-symbols-panel"
    >
      <div className="flex items-center gap-1.5 border-b border-slate-100 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        <Code2 className="h-3.5 w-3.5 text-teal-700" />
        Symbols
      </div>
      <form
        className="flex gap-1 p-2 border-b border-slate-100"
        onSubmit={(e) => {
          e.preventDefault();
          void search();
        }}
      >
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search symbols…"
          className="flex-1 min-w-0 rounded border border-slate-200 px-2 py-1 text-xs"
          data-testid="workspace-symbol-query"
        />
        <button
          type="submit"
          disabled={busy || !query.trim()}
          className="inline-flex items-center gap-1 rounded bg-slate-900 px-2 py-1 text-[11px] text-white disabled:opacity-40"
          data-testid="workspace-symbol-search"
        >
          {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <Search className="h-3 w-3" />}
        </button>
      </form>
      {error ? (
        <p className="px-2 py-1 text-[11px] text-red-600" role="alert">
          {error}
        </p>
      ) : null}
      <div className="flex-1 overflow-auto p-2 space-y-3">
        {results.length > 0 ? (
          <div>
            <h3 className="text-[10px] font-semibold uppercase text-slate-400 mb-1">Search</h3>
            {renderList(results, "workspace-symbol-results")}
          </div>
        ) : null}
        <div>
          <h3 className="text-[10px] font-semibold uppercase text-slate-400 mb-1">File outline</h3>
          {renderList(outline, "workspace-symbol-outline")}
        </div>
      </div>
    </div>
  );
}
