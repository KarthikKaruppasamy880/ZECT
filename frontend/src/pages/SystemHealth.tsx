import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { authHeaders } from "@/lib/api";

const API = import.meta.env.VITE_API_URL || "";

type Component = { id: string; name: string; status: string; detail?: unknown };

export default function SystemHealth() {
  const [status, setStatus] = useState("");
  const [components, setComponents] = useState<Component[]>([]);
  const [model, setModel] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [h, m] = await Promise.all([
          fetch(`${API}/api/system/health`, { headers: authHeaders() }),
          fetch(`${API}/api/system/model-readiness`, { headers: authHeaders() }),
        ]);
        if (!h.ok) throw new Error(await h.text());
        const health = await h.json();
        if (!cancelled) {
          setStatus(health.status || "");
          setComponents(health.components || []);
        }
        if (m.ok && !cancelled) setModel(await m.json());
      } catch (e: any) {
        if (!cancelled) setError(e?.message || "Failed to load system health");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

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
          <li key={c.id} className="rounded-lg border border-slate-200 px-4 py-3 flex justify-between gap-4">
            <div>
              <p className="font-medium text-slate-900">{c.name}</p>
              <p className="text-xs text-slate-500">{typeof c.detail === "string" ? c.detail : JSON.stringify(c.detail)}</p>
            </div>
            <span className="text-xs uppercase font-medium text-slate-600">{c.status}</span>
          </li>
        ))}
      </ul>
      {model && (
        <pre className="mt-6 overflow-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-100" data-testid="model-readiness">
          {JSON.stringify(model, null, 2)}
        </pre>
      )}
      <p className="mt-8 text-sm">
        <Link className="text-teal-700 hover:underline" to="/security-incidents">Security Agent</Link>
      </p>
    </div>
  );
}
