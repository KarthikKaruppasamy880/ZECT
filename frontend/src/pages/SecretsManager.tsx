import { useState, useEffect, useCallback } from "react";
import {
  KeyRound, Plus, Trash2, Edit3, X, Save, Eye, EyeOff, RotateCw, Shield,
} from "lucide-react";
import { getSecrets, createSecret, updateSecret, deleteSecret, rotateSecret } from "@/lib/api";

const SECRET_TYPES = ["api_key", "token", "password", "certificate", "ssh_key", "custom"];
const SCOPES = ["global", "project", "user"];

export default function SecretsManager() {
  const [secrets, setSecrets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [revealedIds, setRevealedIds] = useState<Set<number>>(new Set());
  const [form, setForm] = useState({ name: "", value: "", description: "", secret_type: "api_key", scope: "global" });

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const res = await getSecrets();
      setSecrets(res || []);
    } catch (e: any) {
      setError(e.message || "Failed to load secrets");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    try {
      await createSecret({
        name: form.name,
        value: form.value,
        description: form.description,
        secret_type: form.secret_type,
        scope: form.scope,
      });
      setShowCreate(false);
      setForm({ name: "", value: "", description: "", secret_type: "api_key", scope: "global" });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleUpdate = async () => {
    if (!editId) return;
    try {
      await updateSecret(editId, {
        description: form.description,
        ...(form.value ? { value: form.value } : {}),
      });
      setEditId(null);
      setForm({ name: "", value: "", description: "", secret_type: "api_key", scope: "global" });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this secret? This cannot be undone.")) return;
    try {
      await deleteSecret(id);
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleRotate = async (id: number) => {
    const newValue = prompt("Enter new secret value:");
    if (!newValue) return;
    try {
      await rotateSecret(id, newValue);
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const toggleReveal = (id: number) => {
    const next = new Set(revealedIds);
    if (next.has(id)) next.delete(id); else next.add(id);
    setRevealedIds(next);
  };

  const startEdit = (s: any) => {
    setEditId(s.id);
    setForm({ name: s.name, value: "", description: s.description || "", secret_type: s.secret_type, scope: s.scope });
    setShowCreate(false);
  };

  const maskValue = (val: string) => val ? "•".repeat(Math.min(val.length, 32)) : "•••••••••";

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <KeyRound className="h-6 w-6 text-rose-600" /> Secrets Manager
          </h1>
          <p className="text-sm text-slate-500 mt-1">{secrets.length} secrets — encrypted storage for API keys, tokens, and credentials</p>
        </div>
        <button
          onClick={() => { setShowCreate(true); setEditId(null); setForm({ name: "", value: "", description: "", secret_type: "api_key", scope: "global" }); }}
          className="flex items-center gap-1.5 px-4 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700 text-sm"
        >
          <Plus className="h-4 w-4" /> Add Secret
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">{error}</div>
      )}

      {/* Security Notice */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
        <Shield className="h-5 w-5 text-amber-600 mt-0.5 shrink-0" />
        <div>
          <p className="text-sm font-medium text-amber-800">Secrets are encrypted at rest</p>
          <p className="text-xs text-amber-600 mt-0.5">Values are encrypted using Fernet symmetric encryption. Set <code className="bg-amber-100 px-1 rounded">ZECT_ENCRYPT_KEY</code> in your environment for production use.</p>
        </div>
      </div>

      {/* Create / Edit Form */}
      {(showCreate || editId) && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-900">{editId ? "Edit Secret" : "Add New Secret"}</h3>
            <button onClick={() => { setShowCreate(false); setEditId(null); }} className="text-slate-400 hover:text-slate-600">
              <X className="h-5 w-5" />
            </button>
          </div>
          <div className="grid md:grid-cols-2 gap-3">
            <input
              type="text"
              placeholder="Secret Name (e.g. OPENAI_API_KEY)"
              value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
              disabled={!!editId}
              className="px-4 py-2 border border-slate-300 rounded-lg text-sm font-mono disabled:bg-slate-50"
            />
            <select
              value={form.secret_type}
              onChange={e => setForm({ ...form, secret_type: e.target.value })}
              disabled={!!editId}
              className="px-4 py-2 border border-slate-300 rounded-lg text-sm disabled:bg-slate-50"
            >
              {SECRET_TYPES.map(t => (
                <option key={t} value={t}>{t.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</option>
              ))}
            </select>
          </div>
          <input
            type="password"
            placeholder={editId ? "New value (leave blank to keep existing)" : "Secret Value"}
            value={form.value}
            onChange={e => setForm({ ...form, value: e.target.value })}
            className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm font-mono"
          />
          <div className="grid md:grid-cols-2 gap-3">
            <input
              type="text"
              placeholder="Description (optional)"
              value={form.description}
              onChange={e => setForm({ ...form, description: e.target.value })}
              className="px-4 py-2 border border-slate-300 rounded-lg text-sm"
            />
            <select
              value={form.scope}
              onChange={e => setForm({ ...form, scope: e.target.value })}
              className="px-4 py-2 border border-slate-300 rounded-lg text-sm"
            >
              {SCOPES.map(s => (
                <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
              ))}
            </select>
          </div>
          <button
            onClick={editId ? handleUpdate : handleCreate}
            disabled={!editId && (!form.name || !form.value)}
            className="flex items-center gap-1.5 px-4 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700 text-sm disabled:opacity-50"
          >
            <Save className="h-4 w-4" /> {editId ? "Update" : "Save Secret"}
          </button>
        </div>
      )}

      {/* Secrets List */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-rose-600" />
        </div>
      ) : secrets.length === 0 ? (
        <div className="text-center py-12 text-slate-500">
          <KeyRound className="h-12 w-12 mx-auto mb-3 text-slate-300" />
          <p className="text-lg font-medium">No secrets stored</p>
          <p className="text-sm mt-1">Add your first secret to securely store API keys and credentials</p>
        </div>
      ) : (
        <div className="space-y-3">
          {secrets.map((s: any) => (
            <div key={s.id} className="bg-white border border-slate-200 rounded-xl p-5 hover:shadow-sm transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-slate-900 font-mono text-sm">{s.name}</h3>
                    <span className="px-2 py-0.5 bg-rose-50 text-rose-600 rounded-full text-xs">{s.secret_type}</span>
                    <span className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full text-xs">{s.scope}</span>
                    {!s.is_active && <span className="px-2 py-0.5 bg-red-50 text-red-600 rounded-full text-xs">Inactive</span>}
                  </div>
                  {s.description && <p className="text-sm text-slate-600">{s.description}</p>}
                  <div className="flex items-center gap-2 mt-2">
                    <code className="text-xs bg-slate-100 px-2 py-1 rounded font-mono text-slate-500">
                      {revealedIds.has(s.id) && s.value ? s.value : maskValue(s.encrypted_value || "")}
                    </code>
                  </div>
                  <div className="flex items-center gap-4 mt-2 text-xs text-slate-400">
                    <span>Version {s.version || 1}</span>
                    {s.last_rotated_at && <span>Rotated {new Date(s.last_rotated_at).toLocaleDateString()}</span>}
                    <span>Created {s.created_at ? new Date(s.created_at).toLocaleDateString() : "—"}</span>
                  </div>
                </div>
                <div className="flex items-center gap-1 ml-3">
                  <button onClick={() => toggleReveal(s.id)} className="p-1.5 text-slate-400 hover:text-indigo-600 rounded" title="Reveal/Hide">
                    {revealedIds.has(s.id) ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                  <button onClick={() => handleRotate(s.id)} className="p-1.5 text-slate-400 hover:text-amber-600 rounded" title="Rotate">
                    <RotateCw className="h-4 w-4" />
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
