import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { workspaceProblems, type WorkspaceProblem } from "@/lib/api";

type Props = {
  repoIds: number[];
  onOpen: (absPath: string, repoId?: number) => void;
};

export default function WorkspaceProblemsPanel({ repoIds, onOpen }: Props) {
  const [problems, setProblems] = useState<WorkspaceProblem[]>([]);
  const [checked, setChecked] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const run = async () => {
    if (!repoIds.length) {
      setProblems([]);
      setChecked([]);
      return;
    }
    setBusy(true);
    setError("");
    try {
      const out = await workspaceProblems(repoIds);
      setProblems(Array.isArray(out.problems) ? out.problems : []);
      setChecked(Array.isArray(out.checked) ? out.checked : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to check for problems");
      setProblems([]);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repoIds.join(",")]);

  return (
    <div className="flex h-full min-h-0 flex-col" data-testid="workspace-problems-panel">
      <div className="flex items-center justify-between border-b border-slate-100 pb-2">
        <p className="text-[10px] text-slate-400">
          {checked.length ? `Checked: ${checked.join(", ")}` : busy ? "Checking…" : "No lint/typecheck tooling detected"}
        </p>
        <button
          type="button"
          onClick={() => void run()}
          disabled={busy}
          className="flex items-center gap-1 rounded px-1.5 py-1 text-[11px] text-slate-500 hover:bg-slate-50 disabled:opacity-40"
          data-testid="workspace-problems-recheck"
        >
          <RefreshCw className={`h-3 w-3 ${busy ? "animate-spin" : ""}`} />
          Recheck
        </button>
      </div>
      {error ? (
        <p className="mt-1 text-[11px] text-rose-700" role="alert">
          {error}
        </p>
      ) : null}
      <ul className="mt-2 min-h-0 flex-1 overflow-auto space-y-1" data-testid="workspace-problems-list">
        {problems.map((p, i) => (
          <li key={`${p.repo_id}-${p.path}-${p.line}-${i}`}>
            <button
              type="button"
              className="w-full rounded px-1.5 py-1 text-left text-[11px] hover:bg-slate-50"
              data-testid="workspace-problem-item"
              onClick={() => p.abs_path && onOpen(p.abs_path, p.repo_id)}
            >
              <span
                className={`mr-1 rounded px-1 text-[9px] uppercase ${
                  p.severity === "warning" ? "bg-amber-100 text-amber-700" : "bg-rose-100 text-rose-700"
                }`}
              >
                {p.tool}
              </span>
              <span className="font-mono text-slate-500">
                {p.path}:{p.line}
              </span>
              <span className="mt-0.5 block truncate text-slate-600">{p.message}</span>
            </button>
          </li>
        ))}
        {!problems.length && !busy ? <li className="text-[11px] text-slate-400">No problems</li> : null}
      </ul>
    </div>
  );
}
