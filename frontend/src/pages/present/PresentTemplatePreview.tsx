import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  mentrixPresentationTemplatePreview,
  mentrixPresentationTemplateSlides,
} from "@/lib/api";

export default function PresentTemplatePreview() {
  const { templateId = "" } = useParams();
  const nav = useNavigate();
  const [name, setName] = useState(templateId);
  const [reason, setReason] = useState("");
  const [slides, setSlides] = useState<string[]>([]);
  const [cover, setCover] = useState("");

  useEffect(() => {
    if (!templateId) return;
    void mentrixPresentationTemplatePreview(templateId)
      .then((p) => {
        setName(p.name || templateId);
        setCover(p.visual?.cover_data_url || "");
        setReason(p.visual?.error || p.error || (p.ok ? "" : "Preview unavailable"));
      })
      .catch(() => setReason("Preview unavailable"));
    void mentrixPresentationTemplateSlides(templateId)
      .then((r) => setSlides(r.slides || []))
      .catch(() => setSlides([]));
  }, [templateId]);

  const thumbs = slides.length ? slides : cover ? [cover] : [];

  return (
    <div className="space-y-4" data-testid="present-template-preview">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-slate-900">{name}</h2>
        <div className="flex gap-2">
          <button
            type="button"
            className="zect-btn zect-btn-primary text-xs"
            data-testid="present-template-use"
            onClick={() => nav(`/present/create?template=${encodeURIComponent(templateId)}`)}
          >
            Use template
          </button>
          <Link to="/present/templates" className="zect-btn zect-btn-secondary text-xs">
            Gallery
          </Link>
        </div>
      </div>
      {reason ? (
        <p className="text-xs text-amber-800" data-testid="present-template-preview-reason">
          {reason}
        </p>
      ) : null}
      <div className="flex gap-2 overflow-x-auto pb-2" data-testid="present-template-preview-strip">
        {thumbs.length === 0 ? (
          <p className="text-xs text-slate-500">No slide PNG yet — upload a PPTX master.</p>
        ) : (
          thumbs.map((src, i) => (
            <img
              key={i}
              src={src}
              alt={`Slide ${i + 1}`}
              className="h-36 w-64 shrink-0 rounded-lg border border-slate-200 object-cover"
              data-testid={`present-template-preview-slide-${i}`}
            />
          ))
        )}
      </div>
    </div>
  );
}
