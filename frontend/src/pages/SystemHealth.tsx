import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { authHeaders } from "@/lib/api";

const API = import.meta.env.VITE_API_URL || "";

type Component = { id: string; name: string; status: string; detail?: unknown };

export default function SystemHealth() {
  const [status, setStatus] = useState("");
  const [components, setComponents] = useState<Component[]>([]);
  const [model, setModel] = useState<Record<string, unknown> | null>(null);
  const [desktop, setDesktop] = useState<Record<string, unknown> | null>(null);
  const [syncMsg, setSyncMsg] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [h, m, d] = await Promise.all([
          fetch(`${API}/api/system/health`, { headers: authHeaders() }),
          fetch(`${API}/api/system/model-readiness`, { headers: authHeaders() }),
          fetch(`${API}/api/system/desktop-readiness`, { headers: authHeaders() }),
        ]);
        if (!h.ok) throw new Error(await h.text());
        const health = await h.json();
        if (!cancelled) {
          setStatus(health.status || "");
          setComponents(health.components || []);
        }
        if (m.ok && !cancelled) setModel(await m.json());
        if (d.ok && !cancelled) setDesktop(await d.json());
      } catch (e: any) {
        if (!cancelled) setError(e?.message || "Failed to load system health");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const syncSkills = async () => {
    setSyncMsg("");
    try {
      const r = await fetch(`${API}/api/system/skills-fs/sync`, {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ direction: "bidirectional" }),
      });
      if (!r.ok) throw new Error(await r.text());
      const body = await r.json();
      const inbound = body.fs_to_db || body;
      const outbound = body.db_to_fs || {};
      setSyncMsg(
        `Bi-sync: FS→DB created ${inbound.created ?? 0}/updated ${inbound.updated ?? 0}; DB→FS written ${outbound.written ?? 0}`,
      );
    } catch (e: any) {
      setSyncMsg(e?.message || "Skills sync failed");
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto" data-testid="system-health-page">
      <h1 className="text-2xl font-semibold text-slate-900">System Health</h1>
      <p className="mt-1 text-sm text-slate-600">Readiness across Mentrix spine components (no secrets).</p>
      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      {status && (
        <p className="mt-4 text-sm" data-testid="system-health-status">
          Overall: <span className="font-semibold uppercase">{status}</span>
        </p>
      )}
      <ul className="mt-6 space-y-2">
        {components.map((c) => (
          <li
            key={c.id}
            className="rounded-lg border border-slate-200 px-4 py-3 flex justify-between gap-4"
            data-testid={`system-health-component-${c.id}`}
          >
            <div>
              <p className="font-medium text-slate-900">{c.name}</p>
              <p className="text-xs text-slate-500">{typeof c.detail === "string" ? c.detail : JSON.stringify(c.detail)}</p>
            </div>
            <span className="text-xs uppercase font-medium text-slate-600">{c.status}</span>
          </li>
        ))}
      </ul>
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button
          type="button"
          data-testid="skills-fs-sync"
          onClick={syncSkills}
          className="rounded-md bg-slate-900 px-3 py-2 text-sm text-white hover:bg-slate-800"
        >
          Sync Skills DB ↔ filesystem
        </button>
        {syncMsg && <p className="text-sm text-slate-600" data-testid="skills-fs-sync-result">{syncMsg}</p>}
      </div>
      {model && (
        <pre className="mt-6 overflow-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-100" data-testid="model-readiness">
          {JSON.stringify(model, null, 2)}
        </pre>
      )}
      {desktop && (
        <pre className="mt-4 overflow-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-100" data-testid="desktop-readiness">
          {JSON.stringify(desktop, null, 2)}
        </pre>
      )}
      <p className="mt-8 text-sm">
        <Link className="text-teal-700 hover:underline" to="/security-incidents">Security Agent</Link>
      </p>
    </div>
  );
}
