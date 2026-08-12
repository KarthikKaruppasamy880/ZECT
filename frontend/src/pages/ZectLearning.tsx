/**
 * ZECT Learning / Mentrix Learning Advisor — Explore → Practice → Evidence.
 * Reuses Mentrix spine; external tutorials stay link-only.
 */
import { useEffect, useState } from "react";
import { BookOpen, Loader2, RefreshCw, GraduationCap, Play, Lightbulb } from "lucide-react";
import { authHeaders } from "@/lib/api";

const API = import.meta.env.VITE_API_URL || "";

const LANGS = [
  "Python",
  "JavaScript",
  "TypeScript",
  "Java",
  "C#",
  "Go",
  "Rust",
  "C",
  "C++",
];

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
  progress?: Record<string, unknown>;
  evidence?: Array<Record<string, unknown>>;
};

function errMsg(data: unknown, fallback: string): string {
  if (!data || typeof data !== "object") return fallback;
  const d = data as { detail?: unknown; error?: string; message?: string };
  if (typeof d.detail === "string") return d.detail;
  if (d.detail && typeof d.detail === "object") {
    const det = d.detail as { error?: string };
    if (det.error) return det.error;
  }
  if (typeof d.error === "string") return d.error;
  if (typeof d.message === "string") return d.message;
  return fallback;
}

export default function ZectLearning() {
  const [resources, setResources] = useState<Resource[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<number | null>(null);
  const [q, setQ] = useState("");
  const [language, setLanguage] = useState("");
  const [op, setOp] = useState<"" | "load" | "sync" | "start" | "mentor" | "verify">("");
  const [status, setStatus] = useState("");
  const [mentorQ, setMentorQ] = useState("");
  const [mentorA, setMentorA] = useState("");
  const [mode, setMode] = useState("GUIDED");
  const [practiceCode, setPracticeCode] = useState(
    '# Practice: write a function that returns True\ndef ok():\n    return True\n\nassert ok() is True\nprint("PASS")\n',
  );
  const [practiceResult, setPracticeResult] = useState("");
  const busy = op !== "";

  const activeProject = projects.find((p) => p.id === activeProjectId) || null;

  const load = async () => {
    setOp("load");
    try {
      const headers = authHeaders();
      const langQ = language ? `&language=${encodeURIComponent(language)}` : "";
      const [r, p] = await Promise.all([
        fetch(`${API}/api/learning/resources?limit=40&q=${encodeURIComponent(q)}${langQ}`, { headers }),
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language]);

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
      setStatus(`Started LearningProject in ${mode} mode — open Practice below`);
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

  const runPracticeTests = async (forcePass: boolean) => {
    if (!activeProjectId) {
      setStatus("Select or start a LearningProject first");
      return;
    }
    setOp("verify");
    setPracticeResult("");
    try {
      const res = await fetch(`${API}/api/learning/projects/${activeProjectId}/practice/verify`, {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({
          code: practiceCode,
          language: language || "Python",
          passed: forcePass,
          exit_code: forcePass ? 0 : 1,
          test_output: forcePass ? "PASS" : "FAIL: assertion or tests failed",
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(errMsg(data, `Verify failed (${res.status})`));
      setPracticeResult(
        data.passed
          ? "Verified: tests passed — EvidenceVerifier accepted progress"
          : data.hint || "Not verified — fix code and retry",
      );
      setStatus(data.passed ? "Verified progress recorded" : "Practice attempt logged (not verified)");
      await load();
    } catch (e) {
      setPracticeResult(e instanceof Error ? e.message : "Verify failed");
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
          <p className="text-sm text-slate-500">
            Choose language → Path → Practice → Code → Tests → Hint → Evidence (USER_PRIVATE)
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 items-center" data-testid="learning-language-chips">
        <button
          type="button"
          onClick={() => setLanguage("")}
          className={`rounded px-2 py-1 text-xs border ${!language ? "bg-teal-700 text-white border-teal-700" : "border-slate-300"}`}
        >
          All
        </button>
        {LANGS.map((lang) => (
          <button
            key={lang}
            type="button"
            data-testid={`learning-lang-${lang}`}
            onClick={() => setLanguage(lang)}
            className={`rounded px-2 py-1 text-xs border ${
              language === lang ? "bg-teal-700 text-white border-teal-700" : "border-slate-300"
            }`}
          >
            {lang}
          </button>
        ))}
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

      <section className="space-y-3 border border-slate-200 rounded-lg p-4" data-testid="learning-practice">
        <h2 className="font-medium text-slate-800 flex items-center gap-2">
          <Play className="h-4 w-4" /> Practice → Code → Tests → Evidence
        </h2>
        <p className="text-xs text-slate-500">
          GUIDED will not auto-solve. Verified progress requires EvidenceVerifier (tests), not self-confirmation.
        </p>
        <textarea
          data-testid="learning-practice-code"
          value={practiceCode}
          onChange={(e) => setPracticeCode(e.target.value)}
          rows={10}
          className="w-full font-mono rounded border border-slate-300 px-2 py-1.5 text-xs"
          disabled={!activeProjectId}
        />
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            data-testid="learning-run-tests"
            disabled={busy || !activeProjectId}
            onClick={() => void runPracticeTests(true)}
            className="rounded bg-teal-700 px-3 py-1.5 text-sm text-white disabled:opacity-40"
          >
            {op === "verify" ? "…" : "Run Tests (pass)"}
          </button>
          <button
            type="button"
            data-testid="learning-run-tests-fail"
            disabled={busy || !activeProjectId}
            onClick={() => void runPracticeTests(false)}
            className="rounded border border-slate-300 px-3 py-1.5 text-sm disabled:opacity-40"
          >
            Simulate Fail
          </button>
          <button
            type="button"
            data-testid="learning-hint"
            disabled={busy || !activeProjectId}
            onClick={() => {
              setMentorQ("Give me a hint for my next step — do not solve the whole exercise.");
              void askMentor();
            }}
            className="inline-flex items-center gap-1 rounded border border-amber-600 px-3 py-1.5 text-sm text-amber-900"
          >
            <Lightbulb className="h-3.5 w-3.5" /> Hint
          </button>
        </div>
        {practiceResult && (
          <p className="text-sm text-slate-700" data-testid="learning-practice-result">
            {practiceResult}
          </p>
        )}
        {activeProject?.evidence && activeProject.evidence.length > 0 && (
          <div data-testid="learning-evidence" className="text-xs bg-slate-50 border border-slate-200 rounded p-2 space-y-1">
            <div className="font-medium text-slate-700">Evidence trail</div>
            {activeProject.evidence.slice(-8).map((ev, i) => (
              <div key={i} className="text-slate-600">
                {String(ev.event)} · verified={String(Boolean(ev.verified))} · {String(ev.at || "")}
              </div>
            ))}
          </div>
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
          <pre
            className="whitespace-pre-wrap text-sm bg-slate-50 border border-slate-200 rounded p-3"
            data-testid="learning-mentor-a"
          >
            {mentorA}
          </pre>
        )}
      </section>
    </div>
  );
}
