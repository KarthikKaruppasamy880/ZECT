import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FilePlus2, Sparkles, Upload } from "lucide-react";
import {
  encodeDeckId,
  mentrixPresentDecks,
  mentrixPresentSlidePreview,
  mentrixPresentationTemplates,
  type PresentTemplateCard,
} from "@/lib/api";
import PresentTemplateCardView from "@/pages/present/PresentTemplateCardView";

export default function PresentDashboard() {
  const nav = useNavigate();
  const [decks, setDecks] = useState<Array<{ name: string; path: string; slide_count: number }>>([]);
  const [thumbs, setThumbs] = useState<Record<string, string>>({});
  const [zinnia, setZinnia] = useState<PresentTemplateCard[]>([]);
  const [decksLoading, setDecksLoading] = useState(true);

  useEffect(() => {
    mentrixPresentDecks()
      .then((r) => setDecks(r.items || []))
      .catch(() => setDecks([]))
      .finally(() => setDecksLoading(false));
    mentrixPresentationTemplates()
      .then((r) => setZinnia(r.zinnia || []))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const created: string[] = [];
    decks.slice(0, 8).forEach((d) => {
      mentrixPresentSlidePreview(d.path, 0)
        .then((url) => {
          if (cancelled) {
            URL.revokeObjectURL(url);
            return;
          }
          created.push(url);
          setThumbs((prev) => ({ ...prev, [d.path]: url }));
        })
        .catch(() => undefined);
    });
    return () => {
      cancelled = true;
      created.forEach((u) => URL.revokeObjectURL(u));
    };
  }, [decks]);

  return (
    <div className="space-y-6" data-testid="present-dashboard">
      <div className="grid sm:grid-cols-3 gap-3">
        <Link
          to="/present/create"
          data-testid="present-create-with-ai"
          className="rounded-xl border border-teal-200 bg-teal-50 p-4 hover:border-teal-500"
        >
          <Sparkles className="h-5 w-5 text-teal-800" />
          <p className="mt-2 font-semibold text-slate-900">Create with AI</p>
          <p className="text-xs text-slate-600">Prompt, choose a template, generate a reviewable draft.</p>
        </Link>
        <Link
          to="/present/blank"
          data-testid="present-blank"
          className="text-left rounded-xl border border-slate-200 bg-white p-4 hover:border-teal-500"
        >
          <FilePlus2 className="h-5 w-5 text-slate-700" />
          <p className="mt-2 font-semibold text-slate-900">Blank presentation</p>
          <p className="text-xs text-slate-600">Start from an empty deck and edit in Review.</p>
        </Link>
        <Link
          to="/present/import"
          data-testid="present-import"
          className="rounded-xl border border-slate-200 bg-white p-4 hover:border-teal-500"
        >
          <Upload className="h-5 w-5 text-slate-700" />
          <p className="mt-2 font-semibold text-slate-900">Import PPTX</p>
          <p className="text-xs text-slate-600">Open an existing deck in Review / Rehearse.</p>
        </Link>
      </div>

      <section>
        <h2 className="text-sm font-semibold text-slate-800 mb-2">Recent presentations</h2>
        {decksLoading ? (
          <p className="text-xs text-slate-500" role="status" data-testid="present-decks-loading">
            Loading presentations…
          </p>
        ) : decks.length === 0 ? (
          <p className="text-xs text-slate-500" data-testid="present-decks-empty">
            No generated decks in your Documents folder yet.
          </p>
        ) : (
          <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-3" data-testid="present-recent-decks">
            {decks.map((d) => (
              <Link
                key={d.path}
                to={`/present/d/${encodeDeckId(d.path)}`}
                className="rounded-xl border border-slate-200 bg-white p-3 hover:border-teal-500"
              >
                {thumbs[d.path] ? (
                  <img
                    src={thumbs[d.path]}
                    alt=""
                    className="mb-2 h-24 w-full rounded-lg border border-slate-200 object-cover"
                  />
                ) : (
                  <div className="mb-2 h-16 rounded-lg bg-slate-100" />
                )}
                <p className="text-sm font-medium text-slate-900 truncate">{d.name}</p>
                <p className="text-[11px] text-slate-500">{d.slide_count} slides</p>
              </Link>
            ))}
          </div>
        )}
      </section>

      <section data-testid="zect-present-gallery">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold text-slate-800">Templates</h2>
          <Link to="/present/templates" className="text-xs text-teal-800">
            Browse all
          </Link>
        </div>
        <div className="grid sm:grid-cols-3 gap-3">
          {zinnia.map((t) => (
            <PresentTemplateCardView
              key={t.id}
              tmpl={t}
              selected={false}
              testId={`zect-present-template-${t.id}`}
              onSelect={() => nav(`/present/create?template=${encodeURIComponent(t.id)}`)}
            />
          ))}
        </div>
      </section>
    </div>
  );
}
