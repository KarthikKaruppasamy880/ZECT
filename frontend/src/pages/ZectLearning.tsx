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

export default function ZectLearning() {
  const [resources, setResources] = useState<Resource[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [mentorQ, setMentorQ] = useState("");
  const [mentorA, setMentorA] = useState("");
  const [mode, setMode] = useState("GUIDED");

  const load = async () => {
    const headers = authHeaders();
    const [r, p] = await Promise.all([
      fetch(`${API}/api/learning/resources?limit=40&q=${encodeURIComponent(q)}`, { headers }),
      fetch(`${API}/api/learning/projects`, { headers }),
    ]);
    if (r.ok) {
      const data = await r.json();
      setResources(data.resources || []);
    }
    if (p.ok) {
      const data = await p.json();
      setProjects(data.projects || []);
    }
  };

  useEffect(() => {
    void load().catch(() => undefined);
  }, []);

  const syncCatalog = async () => {
    setBusy(true);
    setStatus("");
    try {
      const res = await fetch(`${API}/api/learning/sources/pbl/sync`, {
        method: "POST",
        headers: authHeaders(),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.error || "sync failed");
      setStatus(
        data.ok
          ? `Catalog synced: ${data.total} resources (external_link_only)`
          : `Sync blocked: ${data.error || "unknown"}`,
      );
      await load();
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Sync failed");
    } finally {
      setBusy(false);
    }
  };

  const startProject = async (resourceId: number, title: string) => {
    setBusy(true);
    try {
      const res = await fetch(`${API}/api/learning/projects`, {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ resource_id: resourceId, mode, title }),
      });
      if (!res.ok) throw new Error(await res.text());
      await load();
      setStatus(`Started LearningProject in ${mode} mode`);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Start failed");
    } finally {
      setBusy(false);
    }
  };

  const askMentor = async () => {
    if (!mentorQ.trim()) return;
    setBusy(true);
    try {
      const res = await fetch(`${API}/api/learning/mentor/ask`, {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ question: mentorQ, mode, project_id: projects[0]?.id }),
      });
      const data = await res.json();
      setMentorA(data.answer || JSON.stringify(data));
    } catch (e) {
      setMentorA(e instanceof Error ? e.message : "Mentor failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6" data-testid="zect-learning-page">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-slate-900 flex items-center gap-2">
          <GraduationCap className="h-6 w-6 text-teal-700" />
          ZECT Learning
        </h1>
        <p className="text-sm text-slate-600">
          Mentrix Learning Advisor — curated catalog metadata/links with attribution. Tutorial bodies stay external.
        </p>
      </header>

      <div className="flex flex-wrap gap-2 items-center">
        <input
          className="rounded border border-slate-300 px-3 py-1.5 text-sm flex-1 min-w-[180px]"
          placeholder="Search language / skill / title"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          data-testid="learning-search"
        />
        <button
          type="button"
          className="rounded bg-slate-900 text-white text-sm px-3 py-1.5"
          onClick={() => void load()}
        >
          Search
        </button>
        <button
          type="button"
          disabled={busy}
          className="inline-flex items-center gap-1 rounded border border-teal-700 text-teal-800 text-sm px-3 py-1.5"
          onClick={() => void syncCatalog()}
          data-testid="learning-sync-pbl"
        >
          {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
          Sync PBL catalog
        </button>
        <select
          className="rounded border border-slate-300 text-sm px-2 py-1.5"
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          data-testid="learning-mode"
        >
          <option value="GUIDED">GUIDED</option>
          <option value="PAIR">PAIR</option>
          <option value="DEMO">DEMO</option>
          <option value="AUTONOMOUS">AUTONOMOUS</option>
        </select>
      </div>
      {status && <p className="text-xs text-slate-600">{status}</p>}

      <section className="grid md:grid-cols-2 gap-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
          <h2 className="text-sm font-semibold flex items-center gap-1">
            <BookOpen className="h-4 w-4" /> Explore
          </h2>
          <ul className="space-y-2 max-h-96 overflow-auto text-sm">
            {resources.map((r) => (
              <li key={r.id} className="border-b border-slate-100 pb-2">
                <div className="font-medium text-slate-800">{r.title}</div>
                <div className="text-xs text-slate-500">
                  {r.language} · {r.difficulty} · {r.content_policy}
                </div>
                <div className="flex gap-2 mt-1">
                  <a
                    className="text-xs text-teal-700 underline"
                    href={r.source_url}
                    target="_blank"
                    rel="noreferrer noopener"
                  >
                    Open external tutorial
                  </a>
                  <button
                    type="button"
                    className="text-xs text-slate-800 underline"
                    onClick={() => void startProject(r.id, r.title)}
                  >
                    Start project
                  </button>
                </div>
              </li>
            ))}
            {!resources.length && <li className="text-xs text-slate-500">Sync catalog to load resources.</li>}
          </ul>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
            <h2 className="text-sm font-semibold">My Progress</h2>
            <ul className="text-sm space-y-1 max-h-40 overflow-auto">
              {projects.map((p) => (
                <li key={p.id}>
                  {p.title} · <span className="text-xs text-slate-500">{p.mode} / {p.status}</span>
                </li>
              ))}
              {!projects.length && <li className="text-xs text-slate-500">No LearningProjects yet.</li>}
            </ul>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
            <h2 className="text-sm font-semibold">Ask Mentor</h2>
            <textarea
              className="w-full rounded border border-slate-300 text-sm p-2"
              rows={3}
              value={mentorQ}
              onChange={(e) => setMentorQ(e.target.value)}
              placeholder="Ask Mentrix Learning Advisor…"
              data-testid="learning-mentor-q"
            />
            <button
              type="button"
              className="rounded bg-teal-700 text-white text-sm px-3 py-1.5"
              disabled={busy}
              onClick={() => void askMentor()}
            >
              Ask
            </button>
            {mentorA && (
              <pre className="text-xs whitespace-pre-wrap bg-slate-50 rounded p-2 border border-slate-100">{mentorA}</pre>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
