import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  BookOpen, Plus, Play, Trash2, Edit3, X, Save, Clock, Star, ChevronDown, ChevronUp, Loader2,
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
  const [runTarget, setRunTarget] = useState<any | null>(null);
  const [runVars, setRunVars] = useState<Record<string, string>>({});
  const [running, setRunning] = useState(false);
  const [lastRun, setLastRun] = useState<any | null>(null);
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

  const openRun = (pb: any) => {
    const vars: Record<string, string> = {};
    for (const v of pb.variables || []) {
      const key = typeof v === "string" ? v : v?.name || v?.key;
      if (key) vars[String(key)] = "";
    }
    const joined = JSON.stringify(pb.steps || []);
    const found = joined.matchAll(/\{\{\s*([^}]+?)\s*\}\}/g);
    for (const m of found) {
      const key = m[1].trim();
      if (key && !(key in vars)) vars[key] = "";
    }
    setRunTarget(pb);
    setRunVars(vars);
    setLastRun(null);
  };

  const handleRunConfirm = async () => {
    if (!runTarget) return;
    try {
      setRunning(true);
      setError("");
      const result = await runPlaybook(runTarget.id, runVars);
      setLastRun(result);
      setRunTarget(null);
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRunning(false);
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
    <div className="max-w-6xl mx-auto space-y-6" data-testid="playbooks-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <BookOpen className="h-6 w-6 text-purple-600" /> Playbooks
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            {total} playbooks — multi-step Mentrix workflows with variables. Reuse prompts to ship faster
            and avoid retyping context.
          </p>
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

      {lastRun && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm" data-testid="playbook-last-run">
          <div className="flex items-center justify-between gap-3">
            <p className="font-semibold text-emerald-900">
              Run #{lastRun.id} — {lastRun.status} ({lastRun.steps_completed}/{lastRun.total_steps} steps)
            </p>
            <Link to="/mentrix" className="text-emerald-800 underline text-xs font-medium">
              Open Mentrix Delivery
            </Link>
          </div>
          {lastRun.output_summary && (
            <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap text-xs text-emerald-950/80">
              {lastRun.output_summary}
            </pre>
          )}
        </div>
      )}

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

      {(showCreate || editId) && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-900">{editId ? "Edit Playbook" : "New Playbook"}</h3>
            <button onClick={() => { setShowCreate(false); setEditId(null); }} className="text-slate-400 hover:text-slate-600">
              <X className="h-5 w-5" />
            </button>
          </div>
          <div className="grid md:grid-cols-2 gap-3">
            <input
              type="text"
              placeholder="Playbook Name"
              value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
              className="px-4 py-2 border border-slate-300 rounded-lg text-sm"
            />
            <select
              value={form.category}
              onChange={e => setForm({ ...form, category: e.target.value })}
              className="px-4 py-2 border border-slate-300 rounded-lg text-sm"
            >
              {CATEGORIES.map(c => (
                <option key={c} value={c}>{c}</option>
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
            <p className="text-sm font-medium text-slate-700">Steps (use {"{{variable}}"} placeholders)</p>
            {form.steps.map((step, idx) => (
              <div key={idx} className="flex gap-2 items-start">
                <div className="flex-1 space-y-2">
                  <input
                    type="text"
                    placeholder={`Step ${idx + 1} title`}
                    value={step.title}
                    onChange={e => updateStep(idx, "title", e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                  <textarea
                    placeholder="Prompt"
                    value={step.prompt}
                    onChange={e => updateStep(idx, "prompt", e.target.value)}
                    rows={2}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <button type="button" onClick={() => removeStep(idx)} className="text-slate-400 hover:text-red-600 p-1">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
            <button type="button" onClick={addStep} className="text-sm text-purple-600 hover:underline">
              + Add step
            </button>
          </div>
          <button
            onClick={editId ? handleUpdate : handleCreate}
            className="flex items-center gap-1.5 px-4 py-2 bg-purple-600 text-white rounded-lg text-sm"
          >
            <Save className="h-4 w-4" /> {editId ? "Save" : "Create"}
          </button>
        </div>
      )}

      {runTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" data-testid="playbook-run-modal">
          <div className="w-full max-w-md rounded-xl bg-white p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-slate-900">Run {runTarget.name}</h3>
              <button type="button" onClick={() => setRunTarget(null)} className="text-slate-400">
                <X className="h-5 w-5" />
              </button>
            </div>
            {Object.keys(runVars).length === 0 ? (
              <p className="text-sm text-slate-500">No variables detected — run with step prompts as-is.</p>
            ) : (
              <div className="space-y-2">
                {Object.keys(runVars).map((key) => (
                  <div key={key}>
                    <label className="text-xs font-medium text-slate-600">{key}</label>
                    <input
                      type="text"
                      value={runVars[key]}
                      onChange={(e) => setRunVars({ ...runVars, [key]: e.target.value })}
                      className="mt-0.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                    />
                  </div>
                ))}
              </div>
            )}
            <button
              type="button"
              disabled={running}
              onClick={handleRunConfirm}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {running ? "Running…" : "Execute playbook"}
            </button>
          </div>
        </div>
      )}

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
                    </div>
                  </div>
                  <div className="flex items-center gap-1 ml-3">
                    <button onClick={() => openRun(pb)} className="p-1.5 text-slate-400 hover:text-green-600 rounded" title="Run Playbook" data-testid="playbook-run-btn">
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
