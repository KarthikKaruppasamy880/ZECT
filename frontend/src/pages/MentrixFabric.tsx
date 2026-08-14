import { useEffect, useState } from "react";
import { Network, Play, RefreshCw, AlertTriangle } from "lucide-react";
import { apiFetch, createSampleProcess, ingestWorkItem } from "@/lib/api";
import { showToast } from "@/components/Toast";
import { Link } from "react-router-dom";

type Surface = {
  surface_id: string;
  label: string;
  active: boolean;
  keywords: string[];
  workspace: string;
  project_key: string;
};

export default function MentrixFabric() {
  const [surfaces, setSurfaces] = useState<Surface[]>([]);
  const [text, setText] = useState("");
  const [classify, setClassify] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    const res = await apiFetch("/api/fabric/surfaces");
    if (res.ok) {
      const body = await res.json();
      setSurfaces(body.items || []);
    }
  };

  useEffect(() => {
    refresh().catch(() => showToast("error", "Failed to load surfaces"));
  }, []);

  const runClassify = async () => {
    setBusy(true);
    try {
      const res = await apiFetch("/api/fabric/classify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const body = await res.json();
      setClassify(body);
      if (!res.ok) showToast("error", "Classify failed");
    } finally {
      setBusy(false);
    }
  };

  const runFabric = async () => {
    setBusy(true);
    try {
      const res = await apiFetch("/api/fabric/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const body = await res.json();
      if (res.status === 409) {
        setClassify(body.detail || body);
        showToast("error", "Fabric refused — activate missing surfaces");
        return;
      }
      if (!res.ok) {
        showToast("error", body.detail?.error || "Run failed");
        return;
      }
      const sessions = body.sessions || [];
      showToast("success", `Started ${sessions.length} Coding Agent session(s)`);
      if (sessions[0]?.navigate) window.location.assign(sessions[0].navigate);
    } finally {
      setBusy(false);
    }
  };

  const toggleActive = async (s: Surface) => {
    const res = await apiFetch(`/api/fabric/surfaces/${s.surface_id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active: !s.active }),
    });
    if (res.ok) await refresh();
  };

  return (
    <div data-testid="mentrix-fabric-page">
      <div className="mb-6 flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Network className="h-6 w-6 text-teal-700" /> Mentrix Fabric
          </h1>
          <p className="text-sm text-slate-500">
            External process → Connector → ZECT WorkItem → Project → ASK/PLAN/AGENT. Ticket text is untrusted.
          </p>
        </div>
        <button type="button" onClick={() => refresh()} className="p-2 rounded hover:bg-slate-100">
          <RefreshCw className="h-4 w-4 text-slate-500" />
        </button>
      </div>

      <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4" data-testid="process-sample-card">
        <h2 className="text-sm font-semibold text-slate-800">Sample process</h2>
        <p className="mt-1 text-xs text-slate-500">
          Fix Failed Order Validation — isolated SAMPLE fixture. Maps Process → WorkItem → Project. Does not complete live Camunda tasks.
        </p>
        <button
          type="button"
          data-testid="process-sample-create"
          className="mt-2 rounded-lg bg-teal-700 px-3 py-1.5 text-xs text-white"
          onClick={async () => {
            try {
              const out = await createSampleProcess();
              showToast("success", out.work_item.title);
              window.location.assign(`/work-items`);
            } catch {
              showToast("error", "Could not create sample process");
            }
          }}
        >
          Create sample WorkItem
        </button>
      </div>

      <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4" data-testid="process-ingest-card">
        <h2 className="text-sm font-semibold text-slate-800">Map Jira / Camunda → WorkItem</h2>
        <p className="mt-1 text-xs text-slate-500">
          Uses the existing WorkItem ingest adapter. Ticket text is untrusted. Never completes a live process task.
        </p>
        <ProcessIngestForm />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="text-sm font-semibold text-slate-800 mb-3">Surfaces</h2>
          <ul className="space-y-2 max-h-80 overflow-y-auto">
            {surfaces.map((s) => (
              <li key={s.surface_id} className="flex items-center justify-between gap-2 p-2 bg-slate-50 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-slate-800">
                    {s.surface_id}{" "}
                    <span className="text-slate-400 font-normal">{s.label}</span>
                  </p>
                  <p className="text-[11px] text-slate-500">{(s.keywords || []).join(", ")}</p>
                </div>
                <button
                  type="button"
                  onClick={() => toggleActive(s)}
                  className={`text-xs px-2 py-1 rounded ${
                    s.active ? "bg-teal-100 text-teal-800" : "bg-slate-200 text-slate-600"
                  }`}
                >
                  {s.active ? "active" : "inactive"}
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="text-sm font-semibold text-slate-800 mb-3">Classify / Run</h2>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={5}
            placeholder="Describe the goal (e.g. BPMN change plus NGC rules)"
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm mb-3"
          />
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy || !text.trim()}
              onClick={runClassify}
              className="px-3 py-1.5 bg-slate-800 text-white rounded-lg text-sm disabled:opacity-50"
            >
              Classify
            </button>
            <button
              type="button"
              disabled={busy || !text.trim()}
              onClick={runFabric}
              className="px-3 py-1.5 bg-teal-700 text-white rounded-lg text-sm inline-flex items-center gap-1 disabled:opacity-50"
            >
              <Play className="h-3.5 w-3.5" /> Run Fabric
            </button>
            <Link to="/workspace" className="px-3 py-1.5 border border-slate-200 rounded-lg text-sm text-slate-700">
              Workspace
            </Link>
          </div>
          {classify && (
            <div className="mt-4 text-xs bg-slate-50 rounded-lg p-3" data-testid="fabric-classify-result">
              {(classify.refuse || classify.error === "fabric_refuse") && (
                <p className="flex items-center gap-1 text-amber-700 mb-2">
                  <AlertTriangle className="h-3.5 w-3.5" /> Refuse — activate missing surfaces
                </p>
              )}
              <pre className="whitespace-pre-wrap overflow-auto max-h-48">
                {JSON.stringify(classify, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ProcessIngestForm() {
  const [source, setSource] = useState("jira");
  const [externalId, setExternalId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [busy, setBusy] = useState(false);

  return (
    <form
      className="mt-3 flex flex-wrap items-end gap-2"
      data-testid="process-ingest-form"
      onSubmit={async (e) => {
        e.preventDefault();
        if (!externalId.trim()) return;
        setBusy(true);
        try {
          const pid = projectId.trim() ? Number(projectId) : undefined;
          const out = await ingestWorkItem({
            source,
            external_id: externalId.trim(),
            project_id: Number.isFinite(pid) ? pid : undefined,
            require_repo: false,
            raw: {
              key: externalId.trim(),
              id: externalId.trim(),
              title: `${source} ${externalId.trim()}`,
              description: "[untrusted-external] Mapped from Processes UI. Not a live completion.",
              project_id: Number.isFinite(pid) ? pid : undefined,
            },
          });
          showToast("success", `${out.work_item.source} → WorkItem #${out.work_item.id}`);
          window.location.assign("/work-items");
        } catch (err) {
          showToast("error", err instanceof Error ? err.message : "Ingest failed");
        } finally {
          setBusy(false);
        }
      }}
    >
      <label className="text-xs text-slate-600">
        Source
        <select
          data-testid="process-ingest-source"
          value={source}
          onChange={(e) => setSource(e.target.value)}
          className="mt-1 block rounded-lg border border-slate-200 px-2 py-1.5 text-xs"
        >
          <option value="jira">Jira</option>
          <option value="camunda">Camunda / Mentrix Process</option>
        </select>
      </label>
      <label className="text-xs text-slate-600">
        External id
        <input
          data-testid="process-ingest-external-id"
          value={externalId}
          onChange={(e) => setExternalId(e.target.value)}
          placeholder="ZECT-123 or task id"
          className="mt-1 block rounded-lg border border-slate-200 px-2 py-1.5 text-xs min-w-[10rem]"
        />
      </label>
      <label className="text-xs text-slate-600">
        Project id (optional)
        <input
          data-testid="process-ingest-project-id"
          value={projectId}
          onChange={(e) => setProjectId(e.target.value)}
          placeholder="numeric"
          className="mt-1 block rounded-lg border border-slate-200 px-2 py-1.5 text-xs w-24"
        />
      </label>
      <button
        type="submit"
        data-testid="process-ingest-submit"
        disabled={busy || !externalId.trim()}
        className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs text-white disabled:opacity-40"
      >
        {busy ? "Mapping…" : "Create WorkItem"}
      </button>
    </form>
  );
}
