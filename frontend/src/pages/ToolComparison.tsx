/**
 * Side-by-side comparison of AI coding products vs ZECT Mentrix.
 * Product names appear only on this comparison surface (not in core APIs).
 */
import { useMemo, useState } from "react";
import { GitCompareArrows, Check, Minus, X } from "lucide-react";

type Cell = "yes" | "partial" | "no" | string;

type Row = {
  capability: string;
  category: string;
  cursor: Cell;
  devin: Cell;
  claudeCode: Cell;
  minion: Cell;
  zect: Cell;
};

const ROWS: Row[] = [
  { category: "Core IDE", capability: "Inline AI edit in editor", cursor: "yes", devin: "partial", claudeCode: "partial", minion: "partial", zect: "yes" },
  { category: "Core IDE", capability: "Multi-file agent workspace", cursor: "yes", devin: "yes", claudeCode: "yes", minion: "partial", zect: "yes" },
  { category: "Core IDE", capability: "PR review + approve-before-post", cursor: "partial", devin: "partial", claudeCode: "partial", minion: "no", zect: "yes" },
  { category: "Runtime", capability: "Isolated coding-engine worktrees", cursor: "partial", devin: "yes", claudeCode: "partial", minion: "no", zect: "yes" },
  { category: "Runtime", capability: "Browser automation with verify", cursor: "partial", devin: "yes", claudeCode: "partial", minion: "partial", zect: "yes" },
  { category: "Runtime", capability: "Desktop / Computer Mode last-resort", cursor: "no", devin: "partial", claudeCode: "no", minion: "yes", zect: "yes" },
  { category: "Voice", capability: "Realtime voice HUD + clone", cursor: "no", devin: "no", claudeCode: "no", minion: "partial", zect: "yes" },
  { category: "Ops", capability: "Jira / Slack draft-before-send", cursor: "no", devin: "partial", claudeCode: "no", minion: "partial", zect: "yes" },
  { category: "Ops", capability: "Security Detection Provider + IR draft", cursor: "no", devin: "no", claudeCode: "no", minion: "no", zect: "yes" },
  { category: "Memory", capability: "Typed memory + retention/export", cursor: "partial", devin: "partial", claudeCode: "partial", minion: "partial", zect: "yes" },
  { category: "Memory", capability: "Skills with approval / capability gates", cursor: "partial", devin: "partial", claudeCode: "yes", minion: "partial", zect: "yes" },
  { category: "Governance", capability: "Capability grants + emergency stop", cursor: "partial", devin: "partial", claudeCode: "partial", minion: "no", zect: "yes" },
  { category: "Governance", capability: "Secret refs + audit hash chain", cursor: "partial", devin: "no", claudeCode: "partial", minion: "no", zect: "yes" },
  { category: "Release", capability: "Self-host desktop + support bundle", cursor: "no", devin: "no", claudeCode: "partial", minion: "partial", zect: "yes" },
  { category: "Release", capability: "Org branding (adapters, no vendor UI)", cursor: "no", devin: "no", claudeCode: "no", minion: "no", zect: "yes" },
];

function CellView({ value }: { value: Cell }) {
  if (value === "yes") return <span className="inline-flex items-center gap-1 text-emerald-400"><Check className="h-4 w-4" /> Yes</span>;
  if (value === "partial") return <span className="inline-flex items-center gap-1 text-amber-400"><Minus className="h-4 w-4" /> Partial</span>;
  if (value === "no") return <span className="inline-flex items-center gap-1 text-slate-500"><X className="h-4 w-4" /> No</span>;
  return <span className="text-slate-300 text-sm">{value}</span>;
}

const TOOLS = [
  { key: "cursor" as const, label: "Cursor" },
  { key: "devin" as const, label: "Devin" },
  { key: "claudeCode" as const, label: "Claude Code" },
  { key: "minion" as const, label: "Minion Bot" },
  { key: "zect" as const, label: "ZECT" },
];

export default function ToolComparison() {
  const [category, setCategory] = useState<string>("all");
  const cats = useMemo(() => ["all", ...Array.from(new Set(ROWS.map((r) => r.category)))], []);
  const rows = useMemo(
    () => (category === "all" ? ROWS : ROWS.filter((r) => r.category === category)),
    [category],
  );
  const scores = useMemo(() => {
    const score = (k: keyof Row) =>
      ROWS.reduce((acc, r) => {
        const v = r[k];
        if (v === "yes") return acc + 2;
        if (v === "partial") return acc + 1;
        return acc;
      }, 0);
    return TOOLS.map((t) => ({ ...t, score: score(t.key) })).sort((a, b) => b.score - a.score);
  }, []);

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <header className="space-y-2">
        <div className="flex items-center gap-2 text-cyan-300">
          <GitCompareArrows className="h-6 w-6" />
          <h1 className="text-2xl font-semibold tracking-tight text-white">Development tool comparison</h1>
        </div>
        <p className="max-w-3xl text-sm text-slate-400">
          Capability matrix for ZECT Mentrix versus common AI coding products. Scores are directional
          (Yes=2, Partial=1) for product planning — not a marketing claim.
        </p>
      </header>

      <div className="grid gap-3 sm:grid-cols-5">
        {scores.map((t) => (
          <div key={t.key} className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-3">
            <div className="text-xs uppercase tracking-wide text-slate-500">{t.label}</div>
            <div className="mt-1 text-xl font-semibold text-white">{t.score}</div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        {cats.map((c) => (
          <button
            key={c}
            type="button"
            onClick={() => setCategory(c)}
            className={`rounded-md px-3 py-1.5 text-sm ${
              category === c ? "bg-cyan-600 text-white" : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
          >
            {c}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-800">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-900 text-slate-400">
            <tr>
              <th className="px-3 py-2 font-medium">Capability</th>
              {TOOLS.map((t) => (
                <th key={t.key} className="px-3 py-2 font-medium">{t.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.capability} className="border-t border-slate-800/80">
                <td className="px-3 py-2 text-slate-200">
                  <div className="font-medium">{r.capability}</div>
                  <div className="text-xs text-slate-500">{r.category}</div>
                </td>
                {TOOLS.map((t) => (
                  <td key={t.key} className="px-3 py-2">
                    <CellView value={r[t.key]} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
