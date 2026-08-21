import type { PresentTemplateCard } from "@/lib/api";

type Props = {
  tmpl: PresentTemplateCard;
  selected: boolean;
  testId: string;
  onSelect: () => void;
  onDelete?: () => void;
};

export default function PresentTemplateCardView({ tmpl, selected, testId, onSelect, onDelete }: Props) {
  const colors = tmpl.visual?.colors || [];
  const layouts = tmpl.visual?.layout_names || [];
  const ready = tmpl.visual?.ready ?? tmpl.native_ready;
  const cover = tmpl.visual?.cover_data_url || "";
  return (
    <div
      className={`relative rounded-xl border p-3 ${
        selected ? "border-teal-600 bg-teal-50 ring-2 ring-teal-600/30" : "border-slate-200 bg-white"
      }`}
    >
      <button
        type="button"
        data-testid={testId}
        onClick={onSelect}
        className="w-full text-left hover:border-teal-500"
      >
        {cover ? (
          <img
            src={cover}
            alt=""
            className="mb-2 h-24 w-full rounded-lg border border-slate-200 object-cover"
            data-testid={`${testId}-thumb`}
          />
        ) : (
          <div
            className="mb-2 h-16 rounded-lg border border-slate-200 overflow-hidden flex"
            data-testid={`${testId}-thumb`}
            aria-hidden
          >
            {(colors.length ? colors : ["#0f766e", "#44546A", "#FF7500", "#E7E6E6"]).map((c) => (
              <span key={c} className="flex-1" style={{ background: c }} />
            ))}
          </div>
        )}
        <p className="text-sm font-semibold text-slate-900">{tmpl.name}</p>
        <p className="text-[11px] text-slate-500">
          {tmpl.scope || "ZINNIA"} · {tmpl.visual?.layout_count ?? layouts.length} layouts
        </p>
        <span
          className={`mt-1 inline-block rounded-full px-2 py-0.5 text-[10px] font-medium ${
            ready ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800"
          }`}
        >
          {tmpl.visual?.readiness || (ready ? "READY" : "TEMPLATE_NOT_READY")}
        </span>
        {!ready ? (
          <p className="mt-1 text-[10px] text-amber-800" data-testid={`${testId}-not-ready-hint`}>
            Not mapped to a Presenton master — pick a READY Zinnia card or upload PPTX. Community packs are not imported.
          </p>
        ) : null}
      </button>
      {onDelete ? (
        <button
          type="button"
          data-testid={`${testId}-delete`}
          className="absolute top-2 right-2 rounded border border-rose-200 bg-white px-1.5 py-0.5 text-[10px] text-rose-700"
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
        >
          Delete
        </button>
      ) : null}
    </div>
  );
}
