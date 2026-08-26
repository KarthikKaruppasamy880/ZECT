import { PRESENT_ICON_GLYPHS } from "@/lib/presentInsertDefaults";

type Props = {
  onConfirm: (iconId: string) => void;
  onClose: () => void;
};

export default function PresentInsertIconDialog({ onConfirm, onClose }: Props) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      data-testid="present-insert-icon-dialog"
      onClick={onClose}
    >
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-4 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-sm font-semibold text-slate-900">Insert icon</h3>
        <p className="mt-1 text-xs text-slate-500">Theme-safe symbols export as editable shapes in PowerPoint.</p>
        <div className="mt-3 grid grid-cols-4 gap-2">
          {PRESENT_ICON_GLYPHS.map((icon) => (
            <button
              key={icon.id}
              type="button"
              data-testid={`present-insert-icon-${icon.id}`}
              className="flex flex-col items-center rounded border border-slate-200 p-2 hover:border-teal-500 hover:bg-teal-50"
              onClick={() => onConfirm(icon.id)}
            >
              <span className="text-xl">{icon.glyph}</span>
              <span className="mt-1 text-[10px] text-slate-600">{icon.label}</span>
            </button>
          ))}
        </div>
        <div className="mt-4 flex justify-end">
          <button type="button" className="rounded border px-3 py-1 text-xs" onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
