import { useState } from "react";

const DIAGRAM_TYPES = [
  { id: "flow", label: "Flow" },
  { id: "process", label: "Process" },
  { id: "timeline", label: "Timeline" },
  { id: "architecture", label: "Architecture" },
  { id: "comparison", label: "Comparison" },
];

type Props = {
  onConfirm: (diagramType: string, nodes: string[]) => void;
  onClose: () => void;
};

export default function PresentInsertDiagramDialog({ onConfirm, onClose }: Props) {
  const [diagramType, setDiagramType] = useState("flow");
  const [nodesText, setNodesText] = useState("Step 1\nStep 2\nStep 3");

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      data-testid="present-insert-diagram-dialog"
      onClick={onClose}
    >
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-4 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-sm font-semibold text-slate-900">Insert diagram</h3>
        <label className="mt-3 block text-xs text-slate-600">
          Diagram type
          <select
            data-testid="present-insert-diagram-type"
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
            value={diagramType}
            onChange={(e) => setDiagramType(e.target.value)}
          >
            {DIAGRAM_TYPES.map((t) => (
              <option key={t.id} value={t.id}>
                {t.label}
              </option>
            ))}
          </select>
        </label>
        <label className="mt-3 block text-xs text-slate-600">
          Labels (one per line)
          <textarea
            data-testid="present-insert-diagram-nodes"
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
            rows={4}
            value={nodesText}
            onChange={(e) => setNodesText(e.target.value)}
          />
        </label>
        <div className="mt-4 flex justify-end gap-2">
          <button type="button" className="rounded border px-3 py-1 text-xs" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            data-testid="present-insert-diagram-confirm"
            className="rounded bg-teal-700 px-3 py-1 text-xs text-white"
            onClick={() => {
              const nodes = nodesText.split("\n").map((s) => s.trim()).filter(Boolean).slice(0, 6);
              onConfirm(diagramType, nodes.length >= 2 ? nodes : ["Step 1", "Step 2", "Step 3"]);
            }}
          >
            Insert
          </button>
        </div>
      </div>
    </div>
  );
}
