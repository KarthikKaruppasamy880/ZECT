/** PA-6 File Organize UI — durable plans with SHA-256 preview / approve / undo. */

import { useState } from "react";
import { FolderInput, Play, RotateCcw, Shield } from "lucide-react";
import { apiFetch } from "@/lib/api";

type Plan = {
  plan_id: string;
  source_dir: string;
  dest_dir: string;
  status: string;
  moves: { from: string; to: string; sha256: string; bytes: number; collision?: string }[];
  errors?: { file: string; error: string }[];
  rollback?: { from: string; to: string }[];
  durable?: boolean;
};

export default function FileOrganize() {
  const [sourceDir, setSourceDir] = useState("");
  const [destDir, setDestDir] = useState("");
  const [patterns, setPatterns] = useState("*");
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const createPlan = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await apiFetch("/api/file-organize/plan", {
        method: "POST",
        body: JSON.stringify({
          source_dir: sourceDir,
          dest_dir: destDir,
          patterns: patterns.split(",").map((p) => p.trim()).filter(Boolean),
          dry_run: true,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(typeof err.detail === "string" ? err.detail : "Plan failed");
      }
      setPlan(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Plan failed");
    } finally {
      setBusy(false);
    }
  };

  const approve = async () => {
    if (!plan) return;
    setBusy(true);
    setError("");
    try {
      const res = await apiFetch("/api/file-organize/approve", {
        method: "POST",
        body: JSON.stringify({ plan_id: plan.plan_id, execute: true }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(typeof err.detail === "string" ? err.detail : "Approve failed");
      }
      setPlan(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approve failed");
    } finally {
      setBusy(false);
    }
  };

  const rollback = async () => {
    if (!plan) return;
    setBusy(true);
    setError("");
    try {
      const res = await apiFetch(`/api/file-organize/rollback?plan_id=${encodeURIComponent(plan.plan_id)}`, {
        method: "POST",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(typeof err.detail === "string" ? err.detail : "Rollback failed");
      }
      setPlan(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Rollback failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto p-6" data-testid="file-organize-page">
      <div className="flex items-center gap-3 mb-6">
        <FolderInput className="h-6 w-6 text-teal-700" />
        <div>
          <h1 className="text-xl font-semibold text-slate-900">File organize</h1>
          <p className="text-sm text-slate-500">
            Dry-run proposals with SHA-256. Approve moves only — Mentrix never deletes.
          </p>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3 mb-4">
        <label className="block text-xs font-medium text-slate-600">
          Source directory (allowlisted)
          <input
            className="mt-1 w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
            value={sourceDir}
            onChange={(e) => setSourceDir(e.target.value)}
            placeholder="C:\\Users\\…\\Documents\\Inbox"
            data-testid="file-organize-source"
          />
        </label>
        <label className="block text-xs font-medium text-slate-600">
          Destination directory
          <input
            className="mt-1 w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
            value={destDir}
            onChange={(e) => setDestDir(e.target.value)}
            placeholder="C:\\Users\\…\\Documents\\Sorted"
            data-testid="file-organize-dest"
          />
        </label>
        <label className="block text-xs font-medium text-slate-600">
          Patterns (comma-separated)
          <input
            className="mt-1 w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
            value={patterns}
            onChange={(e) => setPatterns(e.target.value)}
            placeholder="*.pdf,*.docx"
          />
        </label>
        <button
          type="button"
          disabled={busy || !sourceDir || !destDir}
          onClick={() => void createPlan()}
          className="inline-flex items-center gap-2 px-4 py-2 bg-slate-900 text-white rounded-lg text-sm disabled:opacity-50"
          data-testid="file-organize-plan"
        >
          <Shield className="h-4 w-4" />
          Create dry-run plan
        </button>
      </div>

      {error && (
        <p className="text-sm text-red-600 mb-3" data-testid="file-organize-error">
          {error}
        </p>
      )}

      {plan && (
        <div className="bg-white border border-slate-200 rounded-xl p-5" data-testid="file-organize-plan-result">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
            <div>
              <p className="text-sm font-medium text-slate-900">
                Plan {plan.plan_id} · <span className="text-teal-700">{plan.status}</span>
              </p>
              <p className="text-xs text-slate-500">
                {plan.moves?.length || 0} file(s)
                {plan.durable ? " · durable" : ""}
              </p>
            </div>
            <div className="flex gap-2">
              {plan.status === "planned" && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void approve()}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-teal-700 text-white rounded-lg text-xs"
                  data-testid="file-organize-approve"
                >
                  <Play className="h-3.5 w-3.5" />
                  Approve &amp; move
                </button>
              )}
              {(plan.status === "executed" || plan.status === "executed_with_errors") && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void rollback()}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-slate-300 rounded-lg text-xs"
                  data-testid="file-organize-rollback"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  Undo
                </button>
              )}
            </div>
          </div>
          <ul className="max-h-80 overflow-y-auto text-xs space-y-2">
            {(plan.moves || []).map((m) => (
              <li key={m.from} className="border-b border-slate-100 pb-2">
                <p className="font-mono text-slate-700 truncate">{m.from}</p>
                <p className="font-mono text-slate-500 truncate">→ {m.to}</p>
                <p className="text-slate-400">
                  sha256:{m.sha256.slice(0, 12)}… · {m.bytes} B
                  {m.collision === "skip" ? " · collision skip" : ""}
                </p>
              </li>
            ))}
          </ul>
          {!!plan.errors?.length && (
            <p className="mt-2 text-xs text-amber-700">{plan.errors.length} error(s) during execute</p>
          )}
        </div>
      )}
    </div>
  );
}
