import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Copy, FilePlus2, MoreVertical, Sparkles, Trash2, Upload } from "lucide-react";
import {
  encodeDeckId,
  mentrixPresentDeckDelete,
  mentrixPresentDeckDuplicate,
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
  const [menuPath, setMenuPath] = useState<string | null>(null);
  const [busyPath, setBusyPath] = useState("");

  const refreshDecks = () => {
    setDecksLoading(true);
    mentrixPresentDecks()
      .then((r) => setDecks(r.items || []))
      .catch(() => setDecks([]))
      .finally(() => setDecksLoading(false));
  };

  useEffect(() => {
    refreshDecks();
    mentrixPresentationTemplates()
      .then((r) => setZinnia(r.zinnia || []))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const created: string[] = [];
    decks.slice(0, 8).forEach((d) => {
      mentrixPresentSlidePreview(d.path, 0)
        .then((preview) => {
          if (cancelled) {
            URL.revokeObjectURL(preview.url);
            return;
          }
          created.push(preview.url);
          setThumbs((prev) => ({ ...prev, [d.path]: preview.url }));
        })
        .catch(() => undefined);
    });
    return () => {
      cancelled = true;
      created.forEach((u) => URL.revokeObjectURL(u));
    };
  }, [decks]);

  const onDelete = async (path: string) => {
    if (!window.confirm("Delete this presentation from Documents? This cannot be undone.")) return;
    setBusyPath(path);
    try {
      await mentrixPresentDeckDelete(path);
      setMenuPath(null);
      refreshDecks();
    } catch {
      /* keep card */
    } finally {
      setBusyPath("");
    }
  };

  const onDeleteAll = async () => {
    if (!decks.length) return;
    const ok = window.confirm(
      `Delete all ${decks.length} recent presentations from Documents? This cannot be undone.`,
    );
    if (!ok) return;
    setBusyPath("*");
    try {
      for (const d of decks) {
        await mentrixPresentDeckDelete(d.path);
      }
      setMenuPath(null);
      refreshDecks();
    } catch {
      refreshDecks();
    } finally {
      setBusyPath("");
    }
  };

  const onDuplicate = async (path: string) => {
    setBusyPath(path);
    try {
      await mentrixPresentDeckDuplicate(path);
      setMenuPath(null);
      refreshDecks();
    } catch {
      /* keep card */
    } finally {
      setBusyPath("");
    }
  };

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
          <p className="text-xs text-slate-600">Start from an empty deck and edit in Studio.</p>
        </Link>
        <Link
          to="/present/import"
          data-testid="present-import"
          className="rounded-xl border border-slate-200 bg-white p-4 hover:border-teal-500"
        >
          <Upload className="h-5 w-5 text-slate-700" />
          <p className="mt-2 font-semibold text-slate-900">Import PPTX</p>
          <p className="text-xs text-slate-600">Open an existing deck in Studio / Rehearse.</p>
        </Link>
      </div>

      <section>
        <div className="mb-2 flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-slate-800">Recent presentations</h2>
          {decks.length > 0 ? (
            <button
              type="button"
              data-testid="present-delete-all-recent"
              className="inline-flex items-center gap-1 rounded border border-rose-200 px-2 py-1 text-[11px] text-rose-800 hover:bg-rose-50 disabled:opacity-40"
              disabled={Boolean(busyPath)}
              onClick={() => void onDeleteAll()}
            >
              <Trash2 className="h-3.5 w-3.5" /> Delete all recent
            </button>
          ) : null}
        </div>
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
              <div key={d.path} className="relative rounded-xl border border-slate-200 bg-white p-3 hover:border-teal-500">
                <Link to={`/present/d/${encodeDeckId(d.path)}/edit`} className="block" data-testid={`present-open-studio-${d.name}`}>
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
                <button
                  type="button"
                  data-testid={`present-deck-menu-${d.name}`}
                  className="absolute top-2 right-2 rounded border border-slate-200 bg-white p-1 text-slate-600"
                  disabled={busyPath === d.path}
                  onClick={() => setMenuPath((p) => (p === d.path ? null : d.path))}
                  aria-label="Deck actions"
                >
                  <MoreVertical className="h-4 w-4" />
                </button>
                {menuPath === d.path ? (
                  <div className="absolute top-10 right-2 z-10 w-36 rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
                    <button
                      type="button"
                      data-testid={`present-deck-duplicate-${d.name}`}
                      className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs text-slate-700 hover:bg-slate-50"
                      onClick={() => void onDuplicate(d.path)}
                    >
                      <Copy className="h-3.5 w-3.5" /> Duplicate
                    </button>
                    <button
                      type="button"
                      data-testid={`present-deck-delete-${d.name}`}
                      className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs text-rose-700 hover:bg-rose-50"
                      onClick={() => void onDelete(d.path)}
                    >
                      <Trash2 className="h-3.5 w-3.5" /> Delete
                    </button>
                  </div>
                ) : null}
              </div>
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
