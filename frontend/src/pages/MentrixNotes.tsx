import { useState, useEffect, useCallback } from "react";
import { StickyNote, Plus, Search, Tag, Trash2, X, Save } from "lucide-react";
import { listMentrixNotes, createMentrixNote, deleteMentrixNote, type MentrixNote } from "@/lib/api";

export default function MentrixNotes() {
  const [notes, setNotes] = useState<MentrixNote[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [newText, setNewText] = useState("");
  const [newTags, setNewTags] = useState("");

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const res = await listMentrixNotes(200);
      setNotes(res.notes || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load notes");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleCreate = async () => {
    if (!newText.trim()) return;
    try {
      await createMentrixNote(
        newText.trim(),
        newTags.split(",").map((t) => t.trim()).filter(Boolean),
      );
      setShowCreate(false);
      setNewText("");
      setNewTags("");
      void load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save note");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this note?")) return;
    try {
      await deleteMentrixNote(id);
      setNotes((prev) => prev.filter((n) => n.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete note");
    }
  };

  const q = search.trim().toLowerCase();
  const filtered = q
    ? notes.filter(
        (n) => n.text.toLowerCase().includes(q) || (n.tags || []).some((t) => t.toLowerCase().includes(q)),
      )
    : notes;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <StickyNote className="h-6 w-6 text-teal-600" /> Mentrix Notes
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            {notes.length} notes — manual (say "remember" / "note that") and auto-logged Companion exchanges
          </p>
        </div>
        <button
          type="button"
          data-testid="mentrix-notes-new"
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-1.5 px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 text-sm"
        >
          <Plus className="h-4 w-4" /> New note
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">{error}</div>
      )}

      <div className="relative">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
        <input
          type="text"
          data-testid="mentrix-notes-search"
          placeholder="Search notes or tags…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg text-sm"
        />
      </div>

      {showCreate && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-900">New note</h3>
            <button type="button" onClick={() => setShowCreate(false)} className="text-slate-400 hover:text-slate-600">
              <X className="h-5 w-5" />
            </button>
          </div>
          <textarea
            data-testid="mentrix-notes-new-text"
            placeholder="Write a note…"
            value={newText}
            onChange={(e) => setNewText(e.target.value)}
            rows={4}
            className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm"
          />
          <input
            type="text"
            data-testid="mentrix-notes-new-tags"
            placeholder="Tags (comma-separated)"
            value={newTags}
            onChange={(e) => setNewTags(e.target.value)}
            className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm"
          />
          <button
            type="button"
            data-testid="mentrix-notes-save"
            onClick={() => void handleCreate()}
            disabled={!newText.trim()}
            className="flex items-center gap-1.5 px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 text-sm disabled:opacity-50"
          >
            <Save className="h-4 w-4" /> Save
          </button>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-slate-500" data-testid="mentrix-notes-empty">
          <StickyNote className="h-12 w-12 mx-auto mb-3 text-slate-300" />
          <p className="text-lg font-medium">{notes.length === 0 ? "No notes yet" : "No notes match your search"}</p>
          <p className="text-sm mt-1">
            {notes.length === 0
              ? "Say \"remember\" or \"note that\" to Companion, or every exchange auto-logs here."
              : "Try a different search term."}
          </p>
        </div>
      ) : (
        <div className="space-y-3" data-testid="mentrix-notes-list">
          {filtered.map((note) => (
            <div key={note.id} className="bg-white border border-slate-200 rounded-xl p-5 hover:shadow-sm transition-shadow">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-700 whitespace-pre-wrap">{note.text}</p>
                  <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
                    {note.tags && note.tags.length > 0 && (
                      <span className="flex items-center gap-1.5">
                        <Tag className="h-3 w-3" />
                        {note.tags.map((t) => (
                          <span key={t} className="px-1.5 py-0.5 bg-teal-50 text-teal-700 rounded text-xs">
                            {t}
                          </span>
                        ))}
                      </span>
                    )}
                    <span>{note.createdAt ? new Date(note.createdAt).toLocaleString() : "—"}</span>
                  </div>
                </div>
                <button
                  type="button"
                  data-testid="mentrix-notes-delete"
                  onClick={() => void handleDelete(note.id)}
                  className="p-1.5 text-slate-400 hover:text-red-600 rounded shrink-0"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
