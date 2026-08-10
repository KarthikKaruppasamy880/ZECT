/**
 * ZECT Learning / Mentrix Learning Advisor — Explore + Projects + Mentor.
 * Reuses Mentrix spine; external tutorials stay link-only.
 */
import { useEffect, useState } from "react";
import { BookOpen, Loader2, RefreshCw, GraduationCap } from "lucide-react";
import { authHeaders } from "@/lib/api";

const API = import.meta.env.VITE_API_URL || "";

type Resource = {
  id: number;
  title: string;
  source_url: string;
  language: string;
  difficulty: string;
  skills: string[];
  content_policy: string;
  attribution: string;
};

type Project = {
  id: number;
  title: string;
  mode: string;
  status: string;
  resource_id?: number;
};

function errMsg(data: unknown, fallback: string): string {
  if (!data || typeof data !== "object") return fallback;
  const d = data as { detail?: unknown; error?: string; message?: string };
  if (typeof d.detail === "string") return d.detail;
  if (typeof d.error === "string") return d.error;
  if (typeof d.message === "string") return d.message;
  return fallback;
}

export default function ZectLearning() {
  const [resources, setResources] = useState<Resource[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<number | null>(null);
  const [q, setQ] = useState("");
  const [op, setOp] = useState<"" | "load" | "sync" | "start" | "mentor">("");
  const [status, setStatus] = useState("");
  const [mentorQ, setMentorQ] = useState("");
  const [mentorA, setMentorA] = useState("");
  const [mode, setMode] = useState("GUIDED");
  const busy = op !== "";

  const load = async () => {
    setOp("load");
    try {
      const headers = authHeaders();
      const [r, p] = await Promise.all([
        fetch(`${API}/api/learning/resources?limit=40&q=${encodeURIComponent(q)}`, { headers }),
        fetch(`${API}/api/learning/projects`, { headers }),
      ]);
      if (!r.ok) {
        const data = await r.json().catch(() => ({}));
        setStatus(errMsg(data, `Failed to load resources (${r.status})`));
        setResources([]);
      } else {
        const data = await r.json();
        setResources(data.resources || []);
      }
      if (!p.ok) {
        const data = await p.json().catch(() => ({}));
        setStatus((s) => s || errMsg(data, `Failed to load projects (${p.status})`));
        setProjects([]);
      } else {
        const data = await p.json();
        const list = data.projects || [];
        setProjects(list);
        setActiveProjectId((prev) => {
          if (prev && list.some((x: Project) => x.id === prev)) return prev;
          return list[0]?.id ?? null;
        });
      }
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Failed to load learning data");
    } finally {
      setOp("");
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const syncCatalog = async () => {
    setOp("sync");
    setStatus("");
    try {
      const res = await fetch(`${API}/api/learning/sources/pbl/sync`, {
        method: "POST",
        headers: authHeaders(),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(errMsg(data, `Sync failed (${res.status})`));
      setStatus(
        data.ok
          ? `Catalog synced: ${data.total} resources (external_link_only)`
          : `Sync blocked: ${data.error || "unknown"}`,
      );
      await load();
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Sync failed");
    } finally {
      setOp("");
    }
  };

  const startProject = async (resourceId: number, title: string) => {
    setOp("start");
    try {
      const res = await fetch(`${API}/api/learning/projects`, {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ resource_id: resourceId, mode, title }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(errMsg(data, await res.text().catch(() => "Start failed")));
      if (data?.id) setActiveProjectId(data.id);
      setStatus(`Started LearningProject in ${mode} mode`);
      await load();
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Start failed");
    } finally {
      setOp("");
    }
  };

  const askMentor = async () => {
    if (!mentorQ.trim()) return;
    setOp("mentor");
    try {
      const res = await fetch(`${API}/api/learning/mentor/ask`, {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({
          question: mentorQ,
          mode,
          project_id: activeProjectId || undefined,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(errMsg(data, `Mentor failed (${res.status})`));
      setMentorA(data.answer || "No answer returned.");
    } catch (e) {
      setMentorA(e instanceof Error ? e.message : "Mentor failed");
    } finally {
      setOp("");
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6" data-testid="zect-learning-page">
      <div className="flex items-center gap-3">
        <GraduationCap className="h-7 w-7 text-teal-700" />
        <div>
          <h1 className="text-xl font-semibold text-slate-900">ZECT Learning</h1>
          <p className="text-sm text-slate-500">Mentrix Learning Advisor — curated catalog links, not rehosted tutorials</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 items-center">
        <input
          data-testid="learning-search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void load()}
          placeholder="Search language / skill…"
          className="rounded border border-slate-300 px-3 py-1.5 text-sm"
        />
        <button
          type="button"
          disabled={busy}
          onClick={() => void load()}
          className="rounded border border-slate-300 px-3 py-1.5 text-sm"
        >
          Search
        </button>
        <button
          type="button"
          data-testid="learning-sync-pbl"
          disabled={busy}
          onClick={() => void syncCatalog()}
          className="inline-flex items-center gap-1 rounded bg-teal-700 px-3 py-1.5 text-sm text-white disabled:opacity-50"
        >
          {op === "sync" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
          Sync PBL catalog
        </button>
        <select
          data-testid="learning-mode"
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          className="rounded border border-slate-300 px-2 py-1.5 text-sm"
        >
          <option value="GUIDED">GUIDED</option>
          <option value="PAIR">PAIR</option>
          <option value="DEMO">DEMO</option>
          <option value="AUTONOMOUS">AUTONOMOUS</option>
        </select>
      </div>

      {status && (
        <p className="text-sm text-slate-600" data-testid="learning-status">
          {status}
        </p>
      )}

      <section>
        <h2 className="font-medium text-slate-800 mb-2 flex items-center gap-2">
          <BookOpen className="h-4 w-4" /> Explore
        </h2>
        {resources.length === 0 ? (
          <p className="text-sm text-slate-500">Sync catalog to load resources, or fix the load error above.</p>
        ) : (
          <ul className="space-y-2">
            {resources.slice(0, 30).map((r) => (
              <li key={r.id} className="border border-slate-200 rounded-lg px-3 py-2 text-sm flex justify-between gap-2">
                <div>
                  <a href={r.source_url} target="_blank" rel="noreferrer" className="text-teal-800 font-medium">
                    {r.title}
                  </a>
                  <div className="text-xs text-slate-500">
                    {r.language} · {r.difficulty} · {r.content_policy}
                  </div>
                </div>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void startProject(r.id, r.title)}
                  className="text-xs rounded border border-teal-700 px-2 py-1 text-teal-800"
                >
                  {op === "start" ? "…" : "Start"}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="font-medium text-slate-800 mb-2">My Progress</h2>
        {projects.length === 0 ? (
          <p className="text-sm text-slate-500">No LearningProjects yet.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {projects.map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  className={`text-left w-full rounded px-2 py-1 ${
                    activeProjectId === p.id ? "bg-teal-50 text-teal-900" : "text-slate-700"
                  }`}
                  onClick={() => setActiveProjectId(p.id)}
                >
                  {p.title} — {p.mode} / {p.status}
                  {activeProjectId === p.id ? " (selected)" : ""}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-2">
        <h2 className="font-medium text-slate-800">Ask Mentor</h2>
        <textarea
          data-testid="learning-mentor-q"
          value={mentorQ}
          onChange={(e) => setMentorQ(e.target.value)}
          rows={3}
          className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
          placeholder="Ask for a hint (GUIDED will not auto-complete the exercise)…"
        />
        <button
          type="button"
          disabled={busy || !mentorQ.trim()}
          onClick={() => void askMentor()}
          className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white disabled:opacity-40"
        >
          {op === "mentor" ? "…" : "Ask"}
        </button>
        {mentorA && (
          <pre className="whitespace-pre-wrap text-sm bg-slate-50 border border-slate-200 rounded p-3" data-testid="learning-mentor-a">
            {mentorA}
          </pre>
        )}
      </section>
    </div>
  );
}
