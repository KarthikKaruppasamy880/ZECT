import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { encodeDeckId, mentrixPresentBlank } from "@/lib/api";
import { BLANK_LAYOUT_OPTIONS, type BlankLayoutId } from "@/lib/presentLayouts";

export default function PresentBlank() {
  const nav = useNavigate();
  const [layout, setLayout] = useState<BlankLayoutId>("title_slide");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");

  const create = async () => {
    setBusy(true);
    setStatus("");
    try {
      const out = await mentrixPresentBlank(layout);
      nav(`/present/d/${encodeDeckId(out.path)}/edit`, { replace: true });
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Blank deck failed");
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl p-6" data-testid="present-blank-page">
      <h1 className="text-lg font-semibold text-slate-900">Blank presentation</h1>
      <p className="mt-1 text-sm text-slate-600">Choose a starting layout. Help text stays in the editor — never on your slides.</p>
      <div className="mt-4 grid gap-2 sm:grid-cols-2" data-testid="present-blank-layout-picker">
        {BLANK_LAYOUT_OPTIONS.map((opt) => (
          <button
            key={opt.id}
            type="button"
            data-testid={`present-blank-layout-${opt.id}`}
            disabled={busy}
            onClick={() => setLayout(opt.id)}
            className={`rounded-xl border p-3 text-left transition ${
              layout === opt.id ? "border-teal-600 bg-teal-50 ring-1 ring-teal-600" : "border-slate-200 bg-white hover:border-slate-300"
            }`}
          >
            <p className="text-sm font-medium text-slate-900">{opt.label}</p>
            <p className="mt-0.5 text-xs text-slate-500">{opt.description}</p>
          </button>
        ))}
      </div>
      <div className="mt-6 flex items-center gap-3">
        <button
          type="button"
          data-testid="present-blank-create"
          disabled={busy}
          onClick={() => void create()}
          className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-40"
        >
          {busy ? "Creating…" : "Create presentation"}
        </button>
        {status ? <p className="text-sm text-rose-700">{status}</p> : null}
      </div>
    </div>
  );
}
