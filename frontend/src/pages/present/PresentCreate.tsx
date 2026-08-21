import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Upload } from "lucide-react";
import PresentDeckPanel from "@/components/PresentDeckPanel";
import PresentTemplateCardView from "@/pages/present/PresentTemplateCardView";
import { isGalleryTemplateVisible, canDeleteGalleryTemplate } from "@/lib/presentTemplates";
import {
  encodeDeckId,
  mentrixPresentonStatus,
  mentrixPresentationTemplateDelete,
  mentrixPresentationDeleteUnmapped,
  mentrixPresentationTemplatePreview,
  mentrixPresentationTemplates,
  mentrixPresentationTemplateUpload,
  type PresentTemplateCard,
} from "@/lib/api";

const DEFAULT_TEMPLATE = "zinnia-executive-v1";

function migrateTemplateId(id: string): string {
  if (id === "zinnia-exec" || id === "zinnia-executive") return DEFAULT_TEMPLATE;
  if (id === "zinnia-delivery") return "zinnia-delivery-v1";
  if (id === "zinnia-risk") return "zinnia-risk-v1";
  return id;
}

export default function PresentCreate() {
  const nav = useNavigate();
  const [params] = useSearchParams();
  const [zinnia, setZinnia] = useState<PresentTemplateCard[]>([]);
  const [org, setOrg] = useState<PresentTemplateCard[]>([]);
  const [mine, setMine] = useState<PresentTemplateCard[]>([]);
  const [selected, setSelected] = useState(() =>
    migrateTemplateId(params.get("template") || localStorage.getItem("mentrix_present_template") || "") ||
    DEFAULT_TEMPLATE,
  );
  const [preview, setPreview] = useState("");
  const [status, setStatus] = useState("");
  const [rewrite, setRewrite] = useState("");
  const [orgScope, setOrgScope] = useState(false);
  const [lifecycle, setLifecycle] = useState("STARTING");
  const [panelKey, setPanelKey] = useState(0);
  const [hideNotReady, setHideNotReady] = useState(false);
  const evidencePrompt = params.get("prompt") || params.get("goal") || "";
  const evidenceAudience = params.get("audience") || "";
  const evidenceProject = params.get("project_id") || "";
  const evidenceWorkItem = params.get("work_item_id") || "";

  useEffect(() => {
    if (evidenceAudience) {
      try {
        localStorage.setItem("zect_mentrix_present_audience", evidenceAudience);
      } catch {
        /* ignore */
      }
    }
    mentrixPresentationTemplates()
      .then((r) => {
        setZinnia(r.zinnia || []);
        setOrg(r.organization || []);
        setMine(r.my_templates || []);
      })
      .catch(() => setStatus("Template gallery unavailable"));
    mentrixPresentonStatus()
      .then((s) => setLifecycle(String(s.lifecycle || (s.configured && s.reachable ? "READY" : "PROVIDER_UNAVAILABLE"))))
      .catch(() => setLifecycle("PROVIDER_UNAVAILABLE"));
  }, [evidenceAudience]);

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
    setPreview(bits.join(" — "));
    setPanelKey((k) => k + 1);
  };

  const onUpload = async (file: File | null) => {
    if (!file) return;
    try {
      const out = await mentrixPresentationTemplateUpload(file, undefined, orgScope ? "ORG" : "USER");
      setStatus(out.ok ? "Registered template" : out.error || "Upload failed");
      const r = await mentrixPresentationTemplates();
      setZinnia(r.zinnia || []);
      setOrg(r.organization || []);
      setMine(r.my_templates || []);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Upload failed");
    }
  };

  const visible = (rows: PresentTemplateCard[]) =>
    rows.filter((t) => isGalleryTemplateVisible(t, hideNotReady));

  const onDeleteTemplate = async (id: string) => {
    if (!window.confirm("Remove this uploaded template?")) return;
    const out = await mentrixPresentationTemplateDelete(id).catch(() => ({
      ok: false as const,
      error: "delete_failed",
      message: "Could not delete that template.",
    }));
    if (!out.ok) {
      const human =
        out.message ||
        (out.error === "not_found"
          ? "That template is not in your upload registry, so it cannot be deleted."
          : out.error === "cannot_delete_builtin"
            ? "Built-in Zinnia and org gallery shells cannot be deleted."
            : out.error || "Could not delete template");
      setStatus(human);
      return;
    }
    const r = await mentrixPresentationTemplates();
    setZinnia(r.zinnia || []);
    setOrg(r.organization || []);
    setMine(r.my_templates || []);
  };

  return (
    <div className="space-y-4" data-testid="zect-present-workspace">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">Create with AI</h2>
        <span className="rounded-full border px-2 py-0.5 text-[10px] font-medium" data-testid="present-lifecycle-state">
          {lifecycle === "PROVIDER_UNAVAILABLE" ? "BLOCKED_EXTERNAL" : lifecycle}
        </span>
      </div>
      <p className="text-xs text-slate-500">
        Selected template: <strong data-testid="zect-present-selected">{selected}</strong>
      </p>
      {lifecycle === "PROVIDER_UNAVAILABLE" ? (
        <p
          className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900"
          data-testid="present-create-page-blocked"
        >
          BLOCKED_EXTERNAL — Presenton is not reachable. Start local Docker (Rancher = dockerd, port 5000):{" "}
          <code className="break-all">
            docker run -d --name presenton -p 5000:80 ghcr.io/presenton/presenton:latest
          </code>
          . Full steps: docs/PRESENTON_LOCAL.md. Generate stays disabled until READY.
        </p>
      ) : null}
      {evidenceProject || evidenceWorkItem || evidencePrompt ? (
        <p className="text-xs text-slate-600" data-testid="present-create-evidence">
          Evidence
          {evidenceProject ? ` · project ${evidenceProject}` : ""}
          {evidenceWorkItem ? ` · work item ${evidenceWorkItem}` : ""}
          {evidenceAudience ? ` · audience ${evidenceAudience}` : ""}
          {evidencePrompt ? ` · ${evidencePrompt.slice(0, 160)}` : ""}
        </p>
      ) : null}

      <PresentDeckPanel
        key={panelKey}
        variant="light"
        mode="create"
        initialTemplateId={selected}
        initialPrompt={evidencePrompt || params.get("prompt") || undefined}
        toneHint={rewrite}
        onGenerated={(path) => nav(`/present/d/${encodeDeckId(path)}`)}
      />

      <section className="space-y-4" data-testid="zect-present-gallery">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <h3 className="text-sm font-semibold text-slate-800">Template gallery</h3>
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
              <PresentTemplateCardView
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
              <PresentTemplateCardView
                key={`org-${t.id}`}
                tmpl={t}
                selected={selected === t.id}
                testId={`zect-present-template-${t.id}`}
                onSelect={() => void selectTemplate(t.id)}
                onDelete={canDeleteGalleryTemplate(t.id) ? () => void onDeleteTemplate(t.id) : undefined}
              />
            ))}
          </div>
        </div>
        <div>
          <p className="text-[11px] uppercase tracking-wide text-slate-500 mb-2">My Templates</p>
          {mine.some((t) => !t.native_ready && !t.visual?.ready) ? (
            <button
              type="button"
              className="mb-2 rounded border border-rose-200 px-2 py-1 text-[11px] text-rose-800"
              data-testid="zect-present-delete-unmapped"
              onClick={async () => {
                if (!window.confirm("Delete all unmapped uploaded templates? Built-in Zinnia cards are never deleted.")) return;
                const out = await mentrixPresentationDeleteUnmapped().catch(() => ({ ok: false as const, error: "failed" }));
                setStatus(out.ok ? `Removed ${out.count || 0} unmapped upload(s).` : out.error || "Delete failed");
                const r = await mentrixPresentationTemplates().catch(() => null);
                if (r) {
                  setZinnia(r.zinnia || []);
                  setOrg(r.organization || []);
                  setMine(r.my_templates || []);
                }
              }}
            >
              Delete all unmapped uploads
            </button>
          ) : null}
          {mine.length === 0 ? (
            <p className="text-xs text-slate-500">No uploaded PPTX templates yet.</p>
          ) : (
            <div className="grid sm:grid-cols-3 gap-3">
              {visible(mine).map((t) => (
                <PresentTemplateCardView
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
        {preview ? (
          <div data-testid="zect-present-template-preview" className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs">
            Preview: {preview}
          </div>
        ) : null}
        <label className="block text-xs text-slate-700">
          Tone / rewrite (optional)
          <textarea
            data-testid="zect-present-rewrite"
            value={rewrite}
            onChange={(e) => setRewrite(e.target.value)}
            rows={2}
            placeholder="Executive tone: status, then decisions, then owners."
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-xs"
          />
        </label>
        <button
          type="button"
          data-testid="zect-present-continue-generate"
          className="zect-btn zect-btn-primary"
          onClick={() => setPanelKey((k) => k + 1)}
        >
          Use this template
        </button>
      </section>
      {status ? (
        <p data-testid="zect-present-status" className="text-xs text-slate-600">
          {status}
        </p>
      ) : null}
    </div>
  );
}
