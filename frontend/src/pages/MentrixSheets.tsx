import { useMemo, useState } from "react";
import { mentrixSheetsExport, mentrixSheetsGenerate, mentrixSheetsImport } from "@/lib/api";

type Cell = { v?: string; f?: string };
type Sheet = { name: string; cells: Record<string, Cell> };

const COLS = ["A", "B", "C", "D", "E", "F"];
const ROWS = [1, 2, 3, 4, 5, 6, 7, 8];

export default function MentrixSheets() {
  const [prompt, setPrompt] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [sheet, setSheet] = useState<Sheet>({ name: "Sheet1", cells: {} });

  const grid = useMemo(() => sheet.cells, [sheet]);

  const setCell = (addr: string, value: string) => {
    setSheet((prev) => ({
      ...prev,
      cells: {
        ...prev.cells,
        [addr]: value.startsWith("=") ? { v: "", f: value } : { v: value, f: "" },
      },
    }));
  };

  const generate = async () => {
    if (!prompt.trim()) return;
    setBusy(true);
    setStatus("");
    try {
      const pid = (() => {
        try {
          const raw = localStorage.getItem("zect_active_project");
          const parsed = raw ? (JSON.parse(raw) as { projectId?: number | null }) : null;
          return parsed?.projectId && parsed.projectId > 0 ? parsed.projectId : undefined;
        } catch {
          return undefined;
        }
      })();
      const out = await mentrixSheetsGenerate(prompt.trim(), pid);
      const next = out.workbook?.sheets?.[0];
      if (next) setSheet({ name: next.name || "Sheet1", cells: next.cells || {} });
      setStatus("Generated from chat. Formulas are stored as text, not executed.");
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Generate failed");
    } finally {
      setBusy(false);
    }
  };

  const onImport = async (file: File | null) => {
    if (!file) return;
    setBusy(true);
    try {
      const out = await mentrixSheetsImport(file);
      const next = out.workbook?.sheets?.[0];
      if (next) setSheet({ name: next.name || "Sheet1", cells: next.cells || {} });
      setStatus("Imported XLSX");
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Import failed");
    } finally {
      setBusy(false);
    }
  };

  const onExport = async () => {
    setBusy(true);
    try {
      await mentrixSheetsExport({ sheets: [sheet] });
      setStatus("Exported XLSX");
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Export failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="zect-page space-y-4" data-testid="mentrix-sheets-page">
      <div>
        <p className="text-[11px] uppercase tracking-wide text-teal-800">Mentrix</p>
        <h1 className="text-2xl font-semibold text-slate-900">Sheets</h1>
        <p className="text-xs text-slate-500">Chat-driven workbook. Formulas are stored, never executed in Python.</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <textarea
          data-testid="mentrix-sheets-prompt"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={2}
          className="min-w-[16rem] flex-1 rounded border border-slate-300 px-2 py-1.5 text-sm"
          placeholder="Make a 2×3 status grid for this week’s delivery…"
        />
        <button
          type="button"
          data-testid="mentrix-sheets-generate"
          disabled={busy || !prompt.trim()}
          onClick={() => void generate()}
          className="zect-btn zect-btn-primary text-xs disabled:opacity-40"
        >
          Generate
        </button>
        <label className="zect-btn zect-btn-secondary text-xs">
          Import XLSX
          <input
            type="file"
            accept=".xlsx"
            data-testid="mentrix-sheets-import"
            className="hidden"
            onChange={(e) => {
              void onImport(e.target.files?.[0] || null);
              e.target.value = "";
            }}
          />
        </label>
        <button type="button" data-testid="mentrix-sheets-export" className="zect-btn zect-btn-secondary text-xs" onClick={() => void onExport()}>
          Export XLSX
        </button>
      </div>
      {status ? (
        <p className="text-xs text-slate-600" data-testid="mentrix-sheets-status">
          {status}
        </p>
      ) : null}
      <div className="overflow-auto rounded-xl border border-slate-200 bg-white" data-testid="mentrix-sheets-grid">
        <table className="min-w-full border-collapse text-xs">
          <thead>
            <tr>
              <th className="border border-slate-200 bg-slate-50 px-2 py-1" />
              {COLS.map((c) => (
                <th key={c} className="border border-slate-200 bg-slate-50 px-2 py-1 font-medium">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ROWS.map((r) => (
              <tr key={r}>
                <th className="border border-slate-200 bg-slate-50 px-2 py-1">{r}</th>
                {COLS.map((c) => {
                  const addr = `${c}${r}`;
                  const cell = grid[addr] || {};
                  const shown = cell.f || cell.v || "";
                  return (
                    <td key={addr} className="border border-slate-200 p-0">
                      <input
                        aria-label={addr}
                        data-testid={`mentrix-sheets-cell-${addr}`}
                        value={shown}
                        onChange={(e) => setCell(addr, e.target.value)}
                        className="w-28 px-1 py-1 outline-none"
                      />
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
