import { useState, useEffect, useCallback } from "react";
import {
  BookOpen, Plus, Search, Tag, Trash2, Edit3, X, Save, Filter,
} from "lucide-react";
import {
  getKnowledgeEntries, createKnowledgeEntry, updateKnowledgeEntry,
  deleteKnowledgeEntry, getKnowledgeCategories,
} from "@/lib/api";

const CATEGORIES = ["general", "coding", "review", "deploy", "architecture", "testing", "debug"];

export default function KnowledgeBase() {
  const [entries, setEntries] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [filterCat, setFilterCat] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState({ title: "", content: "", category: "general", tags: "" });

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const [res, cats] = await Promise.all([
        getKnowledgeEntries(filterCat || undefined, search || undefined),
        getKnowledgeCategories(),
      ]);
      setEntries(res.items || []);
      setTotal(res.total || 0);
      setCategories(cats || []);
    } catch (e: any) {
      setError(e.message || "Failed to load knowledge base");
    } finally {
      setLoading(false);
    }
  }, [filterCat, search]);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    try {
      await createKnowledgeEntry({
        title: form.title,
        content: form.content,
        category: form.category,
        tags: form.tags.split(",").map(t => t.trim()).filter(Boolean),
      });
      setShowCreate(false);
      setForm({ title: "", content: "", category: "general", tags: "" });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleUpdate = async () => {
    if (!editId) return;
    try {
      await updateKnowledgeEntry(editId, {
        title: form.title,
        content: form.content,
        category: form.category,
        tags: form.tags.split(",").map(t => t.trim()).filter(Boolean),
      });
      setEditId(null);
      setForm({ title: "", content: "", category: "general", tags: "" });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this knowledge entry?")) return;
    try {
      await deleteKnowledgeEntry(id);
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const startEdit = (entry: any) => {
    setEditId(entry.id);
    setForm({
      title: entry.title,
      content: entry.content,
      category: entry.category,
      tags: (entry.tags || []).join(", "),
    });
    setShowCreate(false);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <BookOpen className="h-6 w-6 text-indigo-600" /> Knowledge Base
          </h1>
          <p className="text-sm text-slate-500 mt-1">{total} entries — persistent tips, instructions, project notes</p>
        </div>
        <button
          onClick={() => { setShowCreate(true); setEditId(null); setForm({ title: "", content: "", category: "general", tags: "" }); }}
          className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm"
        >
          <Plus className="h-4 w-4" /> New Entry
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">{error}</div>
      )}

      {/* Search & Filter */}
      <div className="flex gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search knowledge..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg text-sm"
          />
        </div>
        <div className="relative">
          <Filter className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <select
            value={filterCat}
            onChange={e => setFilterCat(e.target.value)}
            className="pl-10 pr-8 py-2 border border-slate-300 rounded-lg text-sm appearance-none bg-white"
          >
            <option value="">All Categories</option>
            {CATEGORIES.map(c => (
              <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Category chips */}
      {categories.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {categories.map((c: any) => (
            <button
              key={c.category}
              onClick={() => setFilterCat(filterCat === c.category ? "" : c.category)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                filterCat === c.category
                  ? "bg-indigo-100 text-indigo-700"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {c.category} ({c.count})
            </button>
          ))}
        </div>
      )}

      {/* Create / Edit Form */}
      {(showCreate || editId) && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-900">{editId ? "Edit Entry" : "New Knowledge Entry"}</h3>
            <button onClick={() => { setShowCreate(false); setEditId(null); }} className="text-slate-400 hover:text-slate-600">
              <X className="h-5 w-5" />
            </button>
          </div>
          <input
            type="text"
            placeholder="Title"
            value={form.title}
            onChange={e => setForm({ ...form, title: e.target.value })}
            className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm"
          />
          <textarea
            placeholder="Content — write your knowledge, tips, or instructions here..."
            value={form.content}
            onChange={e => setForm({ ...form, content: e.target.value })}
            rows={6}
            className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm font-mono"
          />
          <div className="flex gap-3">
            <select
              value={form.category}
              onChange={e => setForm({ ...form, category: e.target.value })}
              className="px-4 py-2 border border-slate-300 rounded-lg text-sm"
            >
              {CATEGORIES.map(c => (
                <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
              ))}
            </select>
            <input
              type="text"
              placeholder="Tags (comma-separated)"
              value={form.tags}
              onChange={e => setForm({ ...form, tags: e.target.value })}
              className="flex-1 px-4 py-2 border border-slate-300 rounded-lg text-sm"
            />
          </div>
          <button
            onClick={editId ? handleUpdate : handleCreate}
            disabled={!form.title || !form.content}
            className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm disabled:opacity-50"
          >
            <Save className="h-4 w-4" /> {editId ? "Update" : "Save"}
          </button>
        </div>
      )}

      {/* Entries List */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
        </div>
      ) : entries.length === 0 ? (
        <div className="text-center py-12 text-slate-500">
          <BookOpen className="h-12 w-12 mx-auto mb-3 text-slate-300" />
          <p className="text-lg font-medium">No knowledge entries yet</p>
          <p className="text-sm mt-1">Create your first entry to start building your knowledge base</p>
        </div>
      ) : (
        <div className="space-y-3">
          {entries.map((entry: any) => (
            <div key={entry.id} className="bg-white border border-slate-200 rounded-xl p-5 hover:shadow-sm transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-slate-900 truncate">{entry.title}</h3>
                    <span className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full text-xs">{entry.category}</span>
                  </div>
                  <p className="text-sm text-slate-600 line-clamp-2 whitespace-pre-wrap">{entry.content}</p>
                  {entry.tags && entry.tags.length > 0 && (
                    <div className="flex items-center gap-1.5 mt-2">
                      <Tag className="h-3 w-3 text-slate-400" />
                      {entry.tags.map((t: string) => (
                        <span key={t} className="px-1.5 py-0.5 bg-indigo-50 text-indigo-600 rounded text-xs">{t}</span>
                      ))}
                    </div>
                  )}
                  <div className="flex items-center gap-4 mt-2 text-xs text-slate-400">
                    <span>Used {entry.usage_count || 0} times</span>
                    <span>Created {entry.created_at ? new Date(entry.created_at).toLocaleDateString() : "—"}</span>
                  </div>
                </div>
                <div className="flex items-center gap-1 ml-3">
                  <button onClick={() => startEdit(entry)} className="p-1.5 text-slate-400 hover:text-indigo-600 rounded">
                    <Edit3 className="h-4 w-4" />
                  </button>
                  <button onClick={() => handleDelete(entry.id)} className="p-1.5 text-slate-400 hover:text-red-600 rounded">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
