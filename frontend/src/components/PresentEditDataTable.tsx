import { useMemo, useState } from "react";
import type { PresentBlock } from "@/lib/api";
import { PRESENT_CHART_TYPES, chartTypeLabel } from "@/lib/presentChartTypes";

type PresentEditDataTableProps = {
  block: PresentBlock;
  onSave: (content: Record<string, unknown>) => void;
  onClose: () => void;
};

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? { ...value } : {};
}

export default function PresentEditDataTable({ block, onSave, onClose }: PresentEditDataTableProps) {
  const initial = asRecord(block.content);
  const [chartType, setChartType] = useState(String(initial.chart_type || "column"));
  const [title, setTitle] = useState(String(initial.title || ""));
  const [categories, setCategories] = useState<string[]>(
    Array.isArray(initial.categories) ? initial.categories.map(String) : ["A", "B"],
  );
  const [seriesName, setSeriesName] = useState(() => {
    const series = Array.isArray(initial.series) ? initial.series : [];
    const first = series[0] && typeof series[0] === "object" ? (series[0] as Record<string, unknown>) : {};
    return String(first.name || "Series");
  });
  const [values, setValues] = useState<string[]>(() => {
    const series = Array.isArray(initial.series) ? initial.series : [];
    const first = series[0] && typeof series[0] === "object" ? (series[0] as Record<string, unknown>) : {};
    const raw = Array.isArray(first.values) ? first.values : [1, 2];
    return raw.map((v) => String(v));
  });

  const preview = useMemo(() => {
    const nums = values.map((v) => Number(v) || 0);
    const max = Math.max(1, ...nums);
    return categories.map((cat, i) => ({ cat, n: nums[i] || 0, pct: Math.round(((nums[i] || 0) / max) * 100) }));
  }, [categories, values]);

  const setRow = (index: number, cat: string, value: string) => {
    setCategories((prev) => prev.map((c, i) => (i === index ? cat : c)));
    setValues((prev) => prev.map((v, i) => (i === index ? value : v)));
  };

  const addRow = () => {
    setCategories((prev) => [...prev, `Cat ${prev.length + 1}`]);
    setValues((prev) => [...prev, "0"]);
  };

  const removeRow = (index: number) => {
    if (categories.length <= 2) return;
    setCategories((prev) => prev.filter((_, i) => i !== index));
    setValues((prev) => prev.filter((_, i) => i !== index));
  };

  const save = () => {
    onSave({
      ...initial,
      title,
      chart_type: chartType,
      categories,
      series: [{ name: seriesName, values: values.map((v) => Number(v) || 0) }],
      legend: true,
    });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      data-testid="present-edit-data-table"
      onClick={onClose}
    >
      <div
        className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2">
          <h3 className="text-sm font-semibold text-slate-900">Edit Data Table</h3>
          <div className="flex gap-2">
            <button
              type="button"
              data-testid="present-edit-data-clear"
              className="rounded border border-slate-200 px-2 py-1 text-xs text-slate-700"
              onClick={() => {
                setCategories(["A", "B"]);
                setValues(["0", "0"]);
                setTitle("");
              }}
            >
              Clear data
            </button>
            <button
              type="button"
              data-testid="present-edit-data-save"
              className="rounded bg-teal-700 px-3 py-1 text-xs text-white"
              onClick={save}
            >
              Save
            </button>
            <button type="button" className="px-2 text-slate-500" onClick={onClose} aria-label="Close">
              ×
            </button>
          </div>
        </div>
        <div className="grid min-h-0 flex-1 gap-4 overflow-auto p-4 md:grid-cols-2">
          <div className="space-y-3">
            <label className="block text-xs text-slate-600">
              Chart type
              <select
                data-testid="present-edit-data-type"
                className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
                value={chartType}
                onChange={(e) => setChartType(e.target.value)}
              >
                {PRESENT_CHART_TYPES.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.label}
                  </option>
                ))}
              </select>
            </label>
            <p className="text-[11px] font-medium text-slate-700" data-testid="present-edit-data-preview-label">
              {title || chartTypeLabel(chartType)} preview
            </p>
            <div className="space-y-1 rounded-lg border border-slate-200 bg-slate-50 p-3" data-testid="present-edit-data-preview">
              {preview.map((row) => (
                <div key={row.cat} className="flex items-center gap-2 text-[11px]">
                  <span className="w-24 truncate text-slate-600">{row.cat}</span>
                  <div className="h-2 flex-1 rounded bg-slate-200">
                    <div className="h-2 rounded bg-teal-600" style={{ width: `${row.pct}%` }} />
                  </div>
                  <span className="w-8 text-right text-slate-700">{row.n}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="space-y-2">
            <label className="block text-xs text-slate-600">
              Title
              <input
                data-testid="present-edit-data-title"
                className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </label>
            <label className="block text-xs text-slate-600">
              Series
              <input
                data-testid="present-edit-data-series"
                className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
                value={seriesName}
                onChange={(e) => setSeriesName(e.target.value)}
              />
            </label>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="py-1">Label</th>
                  <th className="py-1">{seriesName || "Value"}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {categories.map((cat, i) => (
                  <tr key={`${cat}-${i}`}>
                    <td className="pr-1">
                      <input
                        data-testid={`present-edit-data-cat-${i}`}
                        className="w-full rounded border border-slate-300 px-1 py-1"
                        value={cat}
                        onChange={(e) => setRow(i, e.target.value, values[i] || "0")}
                      />
                    </td>
                    <td className="pr-1">
                      <input
                        data-testid={`present-edit-data-val-${i}`}
                        className="w-full rounded border border-slate-300 px-1 py-1"
                        value={values[i] || "0"}
                        onChange={(e) => setRow(i, cat, e.target.value)}
                      />
                    </td>
                    <td>
                      <button type="button" className="text-rose-700" onClick={() => removeRow(i)}>
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button
              type="button"
              data-testid="present-edit-data-add-row"
              className="rounded border border-slate-200 px-2 py-1 text-xs"
              onClick={addRow}
            >
              + Row
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
