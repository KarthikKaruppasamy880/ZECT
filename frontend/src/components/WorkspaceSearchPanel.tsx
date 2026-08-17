import { useState } from "react";
import { Search } from "lucide-react";
import { workspaceSearch, type WorkspaceSearchHit } from "@/lib/api";

type Props = {
  repoIds: number[];
  activeRepoId: number | null;
  currentFile: string;
  onOpen: (absPath: string, repoId?: number) => void;
};

export default function WorkspaceSearchPanel({ repoIds, activeRepoId, currentFile, onOpen }: Props) {
  const [query, setQuery] = useState("");
  const [scope, setScope] = useState<"file" | "root" | "workspace">("workspace");
  const [hits, setHits] = useState<WorkspaceSearchHit[]>([]);
  const [limitation, setLimitation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const run = async () => {
    const pattern = query.trim();
    if (!pattern || !repoIds.length) return;
    setBusy(true);
    setError("");
    try {
      const out = await workspaceSearch({
        pattern,
        scope,
        repo_ids: repoIds,
        active_repo_id: activeRepoId,
        current_file: currentFile || undefined,
        max_results: 80,
      });
      setHits(Array.isArray(out.hits) ? out.hits : []);
      setLimitation(String(out.limitation || ""));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
      setHits([]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col" data-testid="workspace-search-panel">
      <form
        className="flex flex-wrap items-center gap-1 border-b border-slate-100 pb-2"
        onSubmit={(e) => {
          e.preventDefault();
          void run();
        }}
      >
        <Search className="h-3.5 w-3.5 text-slate-400" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search files…"
          className="min-w-0 flex-1 rounded border border-slate-200 px-2 py-1 text-xs"
          data-testid="workspace-search-query"
        />
        <select
          value={scope}
          onChange={(e) => setScope(e.target.value as "file" | "root" | "workspace")}
          className="rounded border border-slate-200 px-1.5 py-1 text-[11px]"
          data-testid="workspace-search-scope"
        >
          <option value="file">Current file</option>
          <option value="root">Active root</option>
          <option value="workspace">Whole workspace</option>
        </select>
        <button
          type="submit"
          disabled={busy || !query.trim()}
          className="rounded bg-slate-900 px-2 py-1 text-[11px] text-white disabled:opacity-40"
          data-testid="workspace-search-run"
        >
          Search
        </button>
      </form>
      {error ? (
        <p className="mt-1 text-[11px] text-rose-700" role="alert">
          {error}
        </p>
      ) : null}
      {limitation ? <p className="mt-1 text-[10px] text-slate-400">{limitation}</p> : null}
      <ul className="mt-2 min-h-0 flex-1 overflow-auto space-y-1" data-testid="workspace-search-results">
        {hits.map((hit, i) => (
          <li key={`${hit.repo_id}-${hit.path}-${hit.line}-${i}`}>
            <button
              type="button"
              className="w-full rounded px-1.5 py-1 text-left text-[11px] hover:bg-slate-50"
              data-testid="workspace-search-hit"
              data-root={hit.root_label || ""}
              onClick={() => hit.abs_path && onOpen(hit.abs_path, hit.repo_id)}
            >
              <span className="font-medium text-slate-800">{hit.root_label}</span>
              <span className="ml-1 font-mono text-slate-500">
                {hit.path}:{hit.line}
              </span>
              <span className="mt-0.5 block truncate text-slate-600">{hit.content}</span>
            </button>
          </li>
        ))}
        {!hits.length && !busy ? <li className="text-[11px] text-slate-400">No hits</li> : null}
      </ul>
    </div>
  );
}
