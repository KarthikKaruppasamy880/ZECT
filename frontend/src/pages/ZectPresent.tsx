/**
 * ZECT Present — branded product surface (provider stays hidden/replaceable).
 * Workflow: New → Template gallery (Zinnia / Org / My) → Prompt → Generate → Notes / Rehearse / Export
 */
import { useEffect, useState } from "react";
import { Presentation, Sparkles, Upload, FileText, Mic2 } from "lucide-react";
import PresentDeckPanel from "@/components/PresentDeckPanel";
import {
  mentrixPresentonStatus,
  mentrixPresentationTemplates,
  mentrixPresentationTemplatePreview,
  mentrixPresentationTemplateUpload,
  mentrixPresentationTemplateDelete,
  type PresentTemplateCard,
} from "@/lib/api";

type Tmpl = PresentTemplateCard;

type ProviderLifecycle =
  | "STARTING"
  | "READY"
  | "TEMPLATE_NOT_READY"
  | "PROVIDER_UNAVAILABLE"
  | "GENERATION_FAILED";

const STEPS = ["New", "Template", "Generate", "Notes & Rehearse", "Export"] as const;
const DEFAULT_TEMPLATE = "zinnia-executive-v1";
const LIFECYCLES: ReadonlySet<string> = new Set([
  "STARTING",
  "READY",
  "TEMPLATE_NOT_READY",
  "PROVIDER_UNAVAILABLE",
  "GENERATION_FAILED",
]);

function migrateTemplateId(id: string): string {
  if (id === "zinnia-exec" || id === "zinnia-executive") return DEFAULT_TEMPLATE;
  if (id === "zinnia-delivery") return "zinnia-delivery-v1";
  if (id === "zinnia-risk") return "zinnia-risk-v1";
  return id;
}

function initialSelected(): string {
  try {
    return migrateTemplateId(localStorage.getItem("mentrix_present_template") || "") || DEFAULT_TEMPLATE;
  } catch {
    return DEFAULT_TEMPLATE;
  }
}

function TemplateCard({
  tmpl,
  selected,
  testId,
  onSelect,
  onDelete,
}: {
  tmpl: Tmpl;
  selected: boolean;
  testId: string;
  onSelect: () => void;
  onDelete?: () => void;
}) {
  const colors = tmpl.visual?.colors || [];
  const layouts = tmpl.visual?.layout_names || [];
  const ready = tmpl.visual?.ready ?? tmpl.native_ready;
  const fonts = tmpl.visual?.fonts;
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
      <div
        className="mb-2 h-16 rounded-lg border border-slate-200 overflow-hidden flex"
        data-testid={`${testId}-thumb`}
        aria-hidden
      >
        {(colors.length ? colors : ["#0f766e", "#44546A", "#FF7500", "#E7E6E6"]).map((c) => (
          <span key={c} className="flex-1" style={{ background: c }} />
        ))}
      </div>
      <div className="flex items-center gap-2 text-sm font-medium text-slate-900">
        <Sparkles className="h-4 w-4 text-teal-700 shrink-0" />
        <span className="truncate">{tmpl.name}</span>
      </div>
      <p className="mt-1 text-xs text-slate-500 line-clamp-2">{tmpl.preview}</p>
      <div className="mt-2 flex flex-wrap items-center gap-1">
        <span className="zect-chip bg-slate-100 text-slate-700">{tmpl.scope || "ZECT"}</span>
        <span
          className={`zect-chip ${ready ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800"}`}
        >
          {tmpl.visual?.readiness || (ready ? "READY" : "TEMPLATE_NOT_READY")}
        </span>
      </div>
      {fonts?.major ? (
        <p className="mt-1 text-[10px] text-slate-400 truncate">
          {fonts.major}
          {fonts.minor && fonts.minor !== fonts.major ? ` / ${fonts.minor}` : ""}
        </p>
      ) : null}
      {layouts.length > 0 ? (
        <p className="mt-1 text-[10px] text-slate-500 line-clamp-1" title={layouts.join(", ")}>
          {tmpl.visual?.layout_count || layouts.length} layouts · {layouts.slice(0, 3).join(" · ")}
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

export default function ZectPresent() {
  const [step, setStep] = useState(0);
  const [zinnia, setZinnia] = useState<Tmpl[]>([]);
  const [org, setOrg] = useState<Tmpl[]>([]);
  const [mine, setMine] = useState<Tmpl[]>([]);
  const [selected, setSelected] = useState<string>(initialSelected);
  const [preview, setPreview] = useState("");
  const [status, setStatus] = useState("");
  const [rewrite, setRewrite] = useState("");
  const [panelKey, setPanelKey] = useState(0);
  const [lifecycle, setLifecycle] = useState<ProviderLifecycle>("STARTING");
  const [orgScope, setOrgScope] = useState(false);
  const [hideNotReady, setHideNotReady] = useState(true);

  const refresh = () => {
    mentrixPresentationTemplates()
      .then((r) => {
        setZinnia(r.zinnia || []);
        setOrg(r.organization || []);
        setMine(r.my_templates || []);
      })
      .catch(() => setStatus("Template gallery unavailable"));
  };

  useEffect(() => {
    refresh();
    mentrixPresentonStatus()
      .then((s) => {
        const life = String(s.lifecycle || "");
        if (LIFECYCLES.has(life)) {
          setLifecycle(life as ProviderLifecycle);
        } else {
          setLifecycle(s.configured && s.reachable ? "READY" : "PROVIDER_UNAVAILABLE");
        }
      })
      .catch(() => setLifecycle("PROVIDER_UNAVAILABLE"));
  }, []);

  const selectTemplate = async (id: string) => {
    const canonical = migrateTemplateId(id);
    setSelected(canonical);
    try {
      localStorage.setItem("mentrix_present_template", canonical);
    } catch {
      /* ignore */
    }
    const p = await mentrixPresentationTemplatePreview(canonical).catch(() => null);
    const bits = [p?.preview || p?.name || canonical];
    const layouts = p?.visual?.layout_names || [];
    if (layouts.length) bits.push(layouts.slice(0, 4).join(" · "));
    if (p?.visual?.error) bits.push(`Preview error: ${p.visual.error}`);
    setPreview(bits.join(" — "));
    setStep((s) => (s > 1 ? s : 1));
  };

  const onUpload = async (file: File | null) => {
    if (!file) return;
    setStatus("Uploading template…");
    const scope = orgScope ? "ORG" : "USER";
    const out = await mentrixPresentationTemplateUpload(file, file.name, scope).catch((e) => ({
      ok: false as const,
      error: String(e),
    }));
    if (!out.ok) {
      setStatus(`Upload failed: ${out.error || "unknown"}`);
      return;
    }
    const bucket = out.template?.scope === "ORG" || orgScope ? "Organization" : "My Templates";
    setStatus(`Registered “${out.template?.name}” under ${bucket}`);
    refresh();
    if (out.template?.id) await selectTemplate(out.template.id);
  };

  const visible = (rows: Tmpl[]) =>
    hideNotReady ? rows.filter((t) => Boolean(t.visual?.ready ?? t.native_ready)) : rows;

  const onDeleteTemplate = async (id: string) => {
    if (!window.confirm("Remove this uploaded template?")) return;
    const out = await mentrixPresentationTemplateDelete(id).catch(() => ({
      ok: false as const,
      error: "delete_failed",
    }));
    if (!out.ok) {
      setStatus(out.error || "Could not delete template");
      return;
    }
    setStatus("Template removed");
    refresh();
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6" data-testid="zect-present-page">
      <header className="space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="text-xs uppercase tracking-[0.2em] text-teal-700">ZECT Present</p>
          <span
            data-testid="present-lifecycle-state"
            className={`ml-auto rounded-full border px-2 py-0.5 text-[10px] font-medium ${
              lifecycle === "READY"
                ? "border-emerald-600 text-emerald-700"
                : lifecycle === "TEMPLATE_NOT_READY"
                  ? "border-amber-500 text-amber-800"
                  : "border-slate-400 text-slate-600"
            }`}
          >
            {lifecycle}
          </span>
        </div>
        <h1 className="text-2xl font-semibold text-slate-900 flex items-center gap-2">
          <Presentation className="h-6 w-6 text-teal-700" />
          New Presentation
        </h1>
        <p className="text-sm text-slate-600">
          Choose a Zinnia or organization template, generate an editable PPTX, refine notes, and rehearse with
          Voicebox.
        </p>
      </header>

      <nav className="flex flex-wrap gap-2" data-testid="zect-present-steps">
        {STEPS.map((label, i) => (
          <button
            key={label}
            type="button"
            onClick={() => setStep(i)}
            className={`rounded-full px-3 py-1 text-xs font-medium border ${
              step === i
                ? "bg-teal-700 text-white border-teal-700"
                : "bg-white text-slate-600 border-slate-200 hover:border-teal-400"
            }`}
          >
            {i + 1}. {label}
          </button>
        ))}
      </nav>

      {step <= 1 && (
        <section className="space-y-4" data-testid="zect-present-gallery">
          <label className="block space-y-1">
            <span className="text-sm font-semibold text-slate-800">What should this presentation cover?</span>
            <textarea
              data-testid="zect-present-prompt"
              rows={5}
              defaultValue={(() => {
                try {
                  return localStorage.getItem("zect_mentrix_present_deck_prompt") || "";
                } catch {
                  return "";
                }
              })()}
              onChange={(e) => {
                try {
                  localStorage.setItem("zect_mentrix_present_deck_prompt", e.target.value);
                } catch {
                  /* ignore */
                }
              }}
              placeholder="Describe the audience, decisions needed, and key points. Attach a template below, then Generate."
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm text-slate-900"
            />
          </label>

          <div className="flex items-center justify-between gap-3 flex-wrap">
            <h2 className="text-sm font-semibold text-slate-800">Template gallery</h2>
            <div className="flex items-center gap-3">
              <label className="inline-flex items-center gap-1.5 text-xs text-slate-700 cursor-pointer">
                <input
                  data-testid="zect-present-upload-org-scope"
                  type="checkbox"
                  checked={orgScope}
                  onChange={(e) => setOrgScope(e.target.checked)}
                  className="rounded border-slate-400"
                />
                Organization scope
              </label>
              <label className="inline-flex items-center gap-1.5 text-xs text-slate-700 cursor-pointer">
                <input
                  data-testid="zect-present-hide-not-ready"
                  type="checkbox"
                  checked={hideNotReady}
                  onChange={(e) => setHideNotReady(e.target.checked)}
                  className="rounded border-slate-400"
                />
                Ready templates only
              </label>
              <label className="inline-flex items-center gap-1.5 text-xs text-teal-800 cursor-pointer">
                <Upload className="h-3.5 w-3.5" />
                Upload PPTX template
                <input
                  data-testid="zect-present-upload-template"
                  type="file"
                  accept=".pptx,application/vnd.openxmlformats-officedocument.presentationml.presentation"
                  className="hidden"
                  onChange={(e) => void onUpload(e.target.files?.[0] || null)}
                />
              </label>
            </div>
          </div>

          <div>
            <p className="text-[11px] uppercase tracking-wide text-slate-500 mb-2">Zinnia</p>
            <div className="grid sm:grid-cols-3 gap-3">
              {visible(zinnia).map((t) => (
                <TemplateCard
                  key={t.id}
                  tmpl={t}
                  selected={selected === t.id}
                  testId={`zect-present-template-${t.id}`}
                  onSelect={() => void selectTemplate(t.id)}
                />
              ))}
            </div>
          </div>

          <div>
            <p className="text-[11px] uppercase tracking-wide text-slate-500 mb-2">Organization</p>
            <div className="grid sm:grid-cols-3 gap-3">
              {visible(org).map((t) => (
                <TemplateCard
                  key={`org-${t.id}`}
                  tmpl={t}
                  selected={selected === t.id}
                  testId={`zect-present-template-${t.id}`}
                  onSelect={() => void selectTemplate(t.id)}
                  onDelete={t.id.startsWith("zinnia-") ? undefined : () => void onDeleteTemplate(t.id)}
                />
              ))}
            </div>
          </div>

          <div>
            <p className="text-[11px] uppercase tracking-wide text-slate-500 mb-2">My Templates</p>
            {mine.length === 0 ? (
              <p className="text-xs text-slate-500">No uploaded PPTX templates yet.</p>
            ) : (
              <div className="grid sm:grid-cols-3 gap-3">
                {visible(mine).map((t) => (
                  <TemplateCard
                    key={t.id}
                    tmpl={t}
                    selected={selected === t.id}
                    testId={`zect-present-my-${t.id}`}
                    onSelect={() => void selectTemplate(t.id)}
                    onDelete={() => void onDeleteTemplate(t.id)}
                  />
                ))}
              </div>
            )}
          </div>

          {preview && (
            <div
              data-testid="zect-present-template-preview"
              className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700"
            >
              Preview: {preview}
              <span className="ml-2 text-slate-400">(provider UUID hidden)</span>
            </div>
          )}

          <button
            type="button"
            data-testid="zect-present-continue-generate"
            className="zect-btn zect-btn-primary"
            onClick={() => {
              setPanelKey((k) => k + 1);
              setStep(2);
            }}
          >
            Generate presentation
          </button>
        </section>
      )}

      {step >= 2 && (
        <section className="space-y-3" data-testid="zect-present-workspace">
          <p className="text-xs text-slate-500">
            Selected template: <strong data-testid="zect-present-selected">{selected}</strong>
          </p>
          <PresentDeckPanel
            key={panelKey}
            variant="light"
            mode="create"
            initialTemplateId={selected}
            toneHint={rewrite}
          />

          <div className="rounded-xl border border-slate-200 bg-white p-3 space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium text-slate-800">
              <FileText className="h-4 w-4 text-teal-700" />
              Slide rewrite / executive tone (notes)
            </div>
            <textarea
              data-testid="zect-present-rewrite"
              value={rewrite}
              onChange={(e) => {
                setRewrite(e.target.value);
                try {
                  localStorage.setItem("zect_mentrix_present_deck_notes", e.target.value);
                } catch {
                  /* ignore */
                }
              }}
              rows={3}
              placeholder="Rewrite speaker notes: shorten, executive tone, or regenerate talking points…"
              className="w-full rounded border border-slate-300 px-2 py-1.5 text-xs"
            />
            <p className="text-[11px] text-slate-500 flex items-center gap-1">
              <Mic2 className="h-3.5 w-3.5" />
              Use Analyze deck + notes in the panel for rehearsal readiness; Narrate uses authorized Voicebox/clone.
            </p>
          </div>
        </section>
      )}

      {status && (
        <p data-testid="zect-present-status" className="text-xs text-slate-600">
          {status}
        </p>
      )}
    </div>
  );
}
