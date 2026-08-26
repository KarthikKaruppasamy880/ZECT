import { useState } from "react";

type Props = {
  onConfirm: (rows: number, cols: number) => void;
  onClose: () => void;
};

export default function PresentInsertTableDialog({ onConfirm, onClose }: Props) {
  const [rows, setRows] = useState(4);
  const [cols, setCols] = useState(3);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      data-testid="present-insert-table-dialog"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xs rounded-xl border border-slate-200 bg-white p-4 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-sm font-semibold text-slate-900">Insert table</h3>
        <p className="mt-1 text-xs text-slate-500">Choose rows and columns for an editable table.</p>
        <div className="mt-3 grid grid-cols-2 gap-3">
          <label className="text-xs text-slate-600">
            Rows
            <input
              type="number"
              min={2}
              max={12}
              data-testid="present-insert-table-rows"
              className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
              value={rows}
              onChange={(e) => setRows(Math.min(12, Math.max(2, Number(e.target.value) || 2)))}
            />
          </label>
          <label className="text-xs text-slate-600">
            Columns
            <input
              type="number"
              min={2}
              max={8}
              data-testid="present-insert-table-cols"
              className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
              value={cols}
              onChange={(e) => setCols(Math.min(8, Math.max(2, Number(e.target.value) || 2)))}
            />
          </label>
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <button type="button" className="rounded border border-slate-200 px-3 py-1 text-xs" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            data-testid="present-insert-table-confirm"
            className="rounded bg-teal-700 px-3 py-1 text-xs text-white"
            onClick={() => onConfirm(rows, cols)}
          >
            Insert
          </button>
        </div>
      </div>
    </div>
  );
}
