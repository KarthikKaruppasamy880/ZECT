import type { PresentTemplateCard } from "@/lib/api";

type Props = {
  tmpl: PresentTemplateCard;
  selected: boolean;
  testId: string;
  onSelect: () => void;
};

export default function PresentTemplateCardView({ tmpl, selected, testId, onSelect }: Props) {
  const colors = tmpl.visual?.colors || [];
  const layouts = tmpl.visual?.layout_names || [];
  const ready = tmpl.visual?.ready ?? tmpl.native_ready;
  const cover = tmpl.visual?.cover_data_url || "";
  return (
    <button
      type="button"
      data-testid={testId}
      onClick={onSelect}
      className={`text-left rounded-xl border p-3 hover:border-teal-500 ${
        selected ? "border-teal-600 bg-teal-50 ring-2 ring-teal-600/30" : "border-slate-200 bg-white"
      }`}
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
    </button>
  );
}
