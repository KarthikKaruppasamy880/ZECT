import { useState, useEffect, useCallback } from "react";
import {
  Calendar, Plus, Play, Pause, Trash2, Edit3, X, Save, Clock, AlertCircle,
  RefreshCw,
} from "lucide-react";
import {
  getSchedules, createSchedule, updateSchedule, deleteSchedule,
  toggleSchedule, triggerSchedule,
} from "@/lib/api";

const TASK_TYPES = ["review", "build", "deploy", "report", "custom"];
const SCHEDULE_TYPES = ["cron", "interval", "once"];

const CRON_PRESETS = [
  { label: "Every hour", value: "0 * * * *" },
  { label: "Daily at 9 AM", value: "0 9 * * *" },
  { label: "Weekdays at 9 AM", value: "0 9 * * 1-5" },
  { label: "Weekly on Monday", value: "0 9 * * 1" },
  { label: "Monthly on 1st", value: "0 9 1 * *" },
];

export default function ScheduledTasks() {
  const [schedules, setSchedules] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState({
    name: "", description: "", schedule_type: "cron", cron_expression: "0 9 * * 1-5",
    interval_minutes: 60, task_type: "review",
    task_config: { owner: "", repo: "", branch: "main" },
  });

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const res = await getSchedules();
      setSchedules(res.items || []);
      setTotal(res.total || 0);
    } catch (e: any) {
      setError(e.message || "Failed to load schedules");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    try {
      await createSchedule({
        name: form.name,
        description: form.description,
        schedule_type: form.schedule_type,
        cron_expression: form.schedule_type === "cron" ? form.cron_expression : undefined,
        interval_minutes: form.schedule_type === "interval" ? form.interval_minutes : undefined,
        task_type: form.task_type,
        task_config: form.task_config,
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
      await updateSchedule(editId, {
        name: form.name,
        description: form.description,
        cron_expression: form.cron_expression,
        task_config: form.task_config,
      });
      setEditId(null);
      resetForm();
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this schedule?")) return;
    try {
      await deleteSchedule(id);
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleToggle = async (id: number) => {
    try {
      await toggleSchedule(id);
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleTrigger = async (id: number) => {
    try {
      await triggerSchedule(id);
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const resetForm = () => {
    setForm({
      name: "", description: "", schedule_type: "cron", cron_expression: "0 9 * * 1-5",
      interval_minutes: 60, task_type: "review",
      task_config: { owner: "", repo: "", branch: "main" },
    });
  };

  const startEdit = (s: any) => {
    setEditId(s.id);
    setForm({
      name: s.name,
      description: s.description || "",
      schedule_type: s.schedule_type,
      cron_expression: s.cron_expression || "0 9 * * 1-5",
      interval_minutes: s.interval_minutes || 60,
      task_type: s.task_type,
      task_config: s.task_config || { owner: "", repo: "", branch: "main" },
    });
    setShowCreate(false);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Calendar className="h-6 w-6 text-orange-600" /> Scheduled Tasks
          </h1>
          <p className="text-sm text-slate-500 mt-1">{total} schedules — cron-based recurring automated tasks</p>
        </div>
        <button
          onClick={() => { setShowCreate(true); setEditId(null); resetForm(); }}
          className="flex items-center gap-1.5 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 text-sm"
        >
          <Plus className="h-4 w-4" /> New Schedule
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">{error}</div>
      )}

      {/* Create / Edit Form */}
      {(showCreate || editId) && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-900">{editId ? "Edit Schedule" : "New Schedule"}</h3>
            <button onClick={() => { setShowCreate(false); setEditId(null); }} className="text-slate-400 hover:text-slate-600">
              <X className="h-5 w-5" />
            </button>
          </div>
          <div className="grid md:grid-cols-2 gap-3">
            <input
              type="text"
              placeholder="Schedule Name"
              value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
              className="px-4 py-2 border border-slate-300 rounded-lg text-sm"
            />
            <select
              value={form.task_type}
              onChange={e => setForm({ ...form, task_type: e.target.value })}
              className="px-4 py-2 border border-slate-300 rounded-lg text-sm"
            >
              {TASK_TYPES.map(t => (
                <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
              ))}
            </select>
          </div>
          <textarea
            placeholder="Description (optional)"
            value={form.description}
            onChange={e => setForm({ ...form, description: e.target.value })}
            rows={2}
            className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm"
          />

          {/* Schedule Type */}
          <div className="space-y-3">
            <div className="flex gap-2">
              {SCHEDULE_TYPES.map(t => (
                <button
                  key={t}
                  onClick={() => setForm({ ...form, schedule_type: t })}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    form.schedule_type === t ? "bg-orange-100 text-orange-700" : "bg-slate-100 text-slate-600"
                  }`}
                >
                  {t === "cron" ? "Cron" : t === "interval" ? "Interval" : "One-time"}
                </button>
              ))}
            </div>
            {form.schedule_type === "cron" && (
              <div className="space-y-2">
                <input
                  type="text"
                  placeholder="Cron expression (e.g. 0 9 * * 1-5)"
                  value={form.cron_expression}
                  onChange={e => setForm({ ...form, cron_expression: e.target.value })}
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm font-mono"
                />
                <div className="flex gap-2 flex-wrap">
                  {CRON_PRESETS.map(p => (
                    <button
                      key={p.value}
                      onClick={() => setForm({ ...form, cron_expression: p.value })}
                      className="px-2 py-1 bg-slate-100 text-slate-600 rounded text-xs hover:bg-slate-200"
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {form.schedule_type === "interval" && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-600">Every</span>
                <input
                  type="number"
                  value={form.interval_minutes}
                  onChange={e => setForm({ ...form, interval_minutes: Number(e.target.value) })}
                  className="w-24 px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  min={1}
                />
                <span className="text-sm text-slate-600">minutes</span>
              </div>
            )}
          </div>

          {/* Task Config */}
          <div className="grid md:grid-cols-3 gap-3">
            <input
              type="text"
              placeholder="GitHub Owner"
              value={form.task_config.owner || ""}
              onChange={e => setForm({ ...form, task_config: { ...form.task_config, owner: e.target.value } })}
              className="px-4 py-2 border border-slate-300 rounded-lg text-sm"
            />
            <input
              type="text"
              placeholder="Repository"
              value={form.task_config.repo || ""}
              onChange={e => setForm({ ...form, task_config: { ...form.task_config, repo: e.target.value } })}
              className="px-4 py-2 border border-slate-300 rounded-lg text-sm"
            />
            <input
              type="text"
              placeholder="Branch"
              value={form.task_config.branch || ""}
              onChange={e => setForm({ ...form, task_config: { ...form.task_config, branch: e.target.value } })}
              className="px-4 py-2 border border-slate-300 rounded-lg text-sm"
            />
          </div>

          <button
            onClick={editId ? handleUpdate : handleCreate}
            disabled={!form.name}
            className="flex items-center gap-1.5 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 text-sm disabled:opacity-50"
          >
            <Save className="h-4 w-4" /> {editId ? "Update" : "Create Schedule"}
          </button>
        </div>
      )}

      {/* Schedules List */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-600" />
        </div>
      ) : schedules.length === 0 ? (
        <div className="text-center py-12 text-slate-500">
          <Calendar className="h-12 w-12 mx-auto mb-3 text-slate-300" />
          <p className="text-lg font-medium">No scheduled tasks yet</p>
          <p className="text-sm mt-1">Create your first schedule to automate recurring tasks</p>
        </div>
      ) : (
        <div className="space-y-3">
          {schedules.map((s: any) => (
            <div key={s.id} className={`bg-white border rounded-xl p-5 transition-all ${
              s.is_active ? "border-slate-200" : "border-slate-200 opacity-60"
            }`}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-slate-900">{s.name}</h3>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      s.is_active ? "bg-green-50 text-green-700" : "bg-slate-100 text-slate-500"
                    }`}>
                      {s.is_active ? "Active" : "Paused"}
                    </span>
                    <span className="px-2 py-0.5 bg-orange-50 text-orange-600 rounded-full text-xs">{s.task_type}</span>
                  </div>
                  {s.description && <p className="text-sm text-slate-600">{s.description}</p>}
                  <div className="flex items-center gap-4 mt-2 text-xs text-slate-400">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {s.schedule_type === "cron" ? s.cron_expression : `Every ${s.interval_minutes} min`}
                    </span>
                    <span>{s.run_count || 0} runs</span>
                    {s.failure_count > 0 && (
                      <span className="flex items-center gap-1 text-red-500">
                        <AlertCircle className="h-3 w-3" /> {s.failure_count} failures
                      </span>
                    )}
                    {s.last_run_at && <span>Last: {new Date(s.last_run_at).toLocaleString()}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-1 ml-3">
                  <button onClick={() => handleTrigger(s.id)} className="p-1.5 text-slate-400 hover:text-green-600 rounded" title="Run Now">
                    <Play className="h-4 w-4" />
                  </button>
                  <button onClick={() => handleToggle(s.id)} className="p-1.5 text-slate-400 hover:text-orange-600 rounded" title={s.is_active ? "Pause" : "Resume"}>
                    {s.is_active ? <Pause className="h-4 w-4" /> : <RefreshCw className="h-4 w-4" />}
                  </button>
                  <button onClick={() => startEdit(s)} className="p-1.5 text-slate-400 hover:text-indigo-600 rounded">
                    <Edit3 className="h-4 w-4" />
                  </button>
                  <button onClick={() => handleDelete(s.id)} className="p-1.5 text-slate-400 hover:text-red-600 rounded">
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
