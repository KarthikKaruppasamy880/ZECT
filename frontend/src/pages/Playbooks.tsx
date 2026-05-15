import { useState, useEffect, useCallback } from "react";
import {
  BookOpen, Plus, Play, Trash2, Edit3, X, Save, Clock, Star, ChevronDown, ChevronUp,
} from "lucide-react";
import {
  getPlaybooks, createPlaybook, updatePlaybook, deletePlaybook,
  runPlaybook, getPlaybookCategories,
} from "@/lib/api";

const CATEGORIES = ["general", "onboarding", "review", "deploy", "debug", "migration", "testing"];

export default function Playbooks() {
  const [playbooks, setPlaybooks] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterCat, setFilterCat] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [form, setForm] = useState({
    name: "", description: "", category: "general",
    steps: [{ order: 1, title: "", prompt: "" }],
  });

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const [res, cats] = await Promise.all([
        getPlaybooks(filterCat || undefined),
        getPlaybookCategories(),
      ]);
      setPlaybooks(res.items || []);
      setTotal(res.total || 0);
      void cats;
    } catch (e: any) {
      setError(e.message || "Failed to load playbooks");
    } finally {
      setLoading(false);
    }
  }, [filterCat]);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    try {
      await createPlaybook({
        name: form.name,
        description: form.description,
        category: form.category,
        steps: form.steps.filter(s => s.title || s.prompt),
      });
      setShowCreate(false);
      resetForm();
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleUpdate = async () => {
    if (!editId) return;
    try {
      await updatePlaybook(editId, {
        name: form.name,
        description: form.description,
        category: form.category,
        steps: form.steps.filter(s => s.title || s.prompt),
      });
      setEditId(null);
      resetForm();
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this playbook?")) return;
    try {
      await deletePlaybook(id);
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleRun = async (id: number) => {
    try {
      await runPlaybook(id);
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const resetForm = () => {
    setForm({ name: "", description: "", category: "general", steps: [{ order: 1, title: "", prompt: "" }] });
  };

  const startEdit = (pb: any) => {
    setEditId(pb.id);
    setForm({
      name: pb.name,
      description: pb.description,
      category: pb.category,
      steps: pb.steps?.length ? pb.steps : [{ order: 1, title: "", prompt: "" }],
    });
    setShowCreate(false);
  };

  const addStep = () => {
    setForm({
      ...form,
      steps: [...form.steps, { order: form.steps.length + 1, title: "", prompt: "" }],
    });
  };

  const updateStep = (idx: number, field: string, value: string) => {
    const steps = [...form.steps];
    steps[idx] = { ...steps[idx], [field]: value };
    setForm({ ...form, steps });
  };

  const removeStep = (idx: number) => {
    if (form.steps.length <= 1) return;
    setForm({ ...form, steps: form.steps.filter((_, i) => i !== idx) });
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <BookOpen className="h-6 w-6 text-purple-600" /> Playbooks
          </h1>
          <p className="text-sm text-slate-500 mt-1">{total} playbooks — reusable prompt templates and workflows</p>
        </div>
        <button
          onClick={() => { setShowCreate(true); setEditId(null); resetForm(); }}
          className="flex items-center gap-1.5 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm"
        >
          <Plus className="h-4 w-4" /> New Playbook
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">{error}</div>
      )}

      {/* Category filter */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setFilterCat("")}
          className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
            !filterCat ? "bg-purple-100 text-purple-700" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
          }`}
        >
          All
        </button>
        {CATEGORIES.map(c => (
          <button
            key={c}
            onClick={() => setFilterCat(filterCat === c ? "" : c)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              filterCat === c ? "bg-purple-100 text-purple-700" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {c.charAt(0).toUpperCase() + c.slice(1)}
          </button>
        ))}
      </div>

      {/* Create / Edit Form */}
      {(showCreate || editId) && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-900">{editId ? "Edit Playbook" : "New Playbook"}</h3>
            <button onClick={() => { setShowCreate(false); setEditId(null); }} className="text-slate-400 hover:text-slate-600">
              <X className="h-5 w-5" />
            </button>
          </div>
          <div className="flex gap-3">
            <input
              type="text"
              placeholder="Playbook Name"
              value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
              className="flex-1 px-4 py-2 border border-slate-300 rounded-lg text-sm"
            />
            <select
              value={form.category}
              onChange={e => setForm({ ...form, category: e.target.value })}
              className="px-4 py-2 border border-slate-300 rounded-lg text-sm"
            >
              {CATEGORIES.map(c => (
                <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
              ))}
            </select>
          </div>
          <textarea
            placeholder="Description"
            value={form.description}
            onChange={e => setForm({ ...form, description: e.target.value })}
            rows={2}
            className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm"
          />
          <div className="space-y-3">
            <p className="text-sm font-medium text-slate-700">Steps</p>
            {form.steps.map((step, idx) => (
              <div key={idx} className="flex gap-2 items-start">
                <span className="mt-2 text-xs text-slate-400 w-6 text-center">{idx + 1}</span>
                <div className="flex-1 space-y-2">
                  <input
                    type="text"
                    placeholder={`Step ${idx + 1} title`}
                    value={step.title}
                    onChange={e => updateStep(idx, "title", e.target.value)}
                    className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-sm"
                  />
                  <textarea
                    placeholder="Prompt / instructions for this step"
                    value={step.prompt}
                    onChange={e => updateStep(idx, "prompt", e.target.value)}
                    rows={2}
                    className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-sm font-mono"
                  />
                </div>
                {form.steps.length > 1 && (
                  <button onClick={() => removeStep(idx)} className="mt-2 text-slate-400 hover:text-red-500">
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))}
            <button onClick={addStep} className="text-sm text-purple-600 hover:text-purple-700">+ Add Step</button>
          </div>
          <button
            onClick={editId ? handleUpdate : handleCreate}
            disabled={!form.name}
            className="flex items-center gap-1.5 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm disabled:opacity-50"
          >
            <Save className="h-4 w-4" /> {editId ? "Update" : "Save"}
          </button>
        </div>
      )}

      {/* Playbooks List */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600" />
        </div>
      ) : playbooks.length === 0 ? (
        <div className="text-center py-12 text-slate-500">
          <BookOpen className="h-12 w-12 mx-auto mb-3 text-slate-300" />
          <p className="text-lg font-medium">No playbooks yet</p>
          <p className="text-sm mt-1">Create your first playbook to automate workflows</p>
        </div>
      ) : (
        <div className="space-y-3">
          {playbooks.map((pb: any) => (
            <div key={pb.id} className="bg-white border border-slate-200 rounded-xl overflow-hidden hover:shadow-sm transition-shadow">
              <div className="p-5">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-slate-900">{pb.name}</h3>
                      <span className="px-2 py-0.5 bg-purple-50 text-purple-600 rounded-full text-xs">{pb.category}</span>
                      {pb.avg_rating > 0 && (
                        <span className="flex items-center gap-0.5 text-xs text-amber-500">
                          <Star className="h-3 w-3 fill-current" /> {pb.avg_rating.toFixed(1)}
                        </span>
                      )}
                    </div>
                    {pb.description && <p className="text-sm text-slate-600 line-clamp-2">{pb.description}</p>}
                    <div className="flex items-center gap-4 mt-2 text-xs text-slate-400">
                      <span>{(pb.steps || []).length} steps</span>
                      <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> Used {pb.usage_count || 0} times</span>
                      <span>Created {pb.created_at ? new Date(pb.created_at).toLocaleDateString() : "—"}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 ml-3">
                    <button onClick={() => handleRun(pb.id)} className="p-1.5 text-slate-400 hover:text-green-600 rounded" title="Run Playbook">
                      <Play className="h-4 w-4" />
                    </button>
                    <button onClick={() => startEdit(pb)} className="p-1.5 text-slate-400 hover:text-purple-600 rounded">
                      <Edit3 className="h-4 w-4" />
                    </button>
                    <button onClick={() => handleDelete(pb.id)} className="p-1.5 text-slate-400 hover:text-red-600 rounded">
                      <Trash2 className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => setExpandedId(expandedId === pb.id ? null : pb.id)}
                      className="p-1.5 text-slate-400 hover:text-slate-600 rounded"
                    >
                      {expandedId === pb.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
              </div>
              {expandedId === pb.id && (pb.steps || []).length > 0 && (
                <div className="border-t border-slate-100 bg-slate-50 px-5 py-3">
                  <p className="text-xs font-medium text-slate-500 mb-2">Steps</p>
                  <ol className="space-y-2">
                    {(pb.steps || []).map((step: any, idx: number) => (
                      <li key={idx} className="flex gap-2 text-sm">
                        <span className="text-xs text-slate-400 mt-0.5 w-5">{idx + 1}.</span>
                        <div>
                          <p className="font-medium text-slate-700">{step.title || `Step ${idx + 1}`}</p>
                          {step.prompt && <p className="text-slate-500 text-xs mt-0.5 line-clamp-2">{step.prompt}</p>}
                        </div>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
