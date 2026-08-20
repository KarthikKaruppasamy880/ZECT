/**
 * ZECT Learning / Mentrix Learning Advisor — Path → Lesson → Practice → Evidence → Handoff.
 * Reuses Mentrix spine; external tutorials stay link-only; GUIDED never auto-solves.
 */
import { useEffect, useState } from "react";
import {
  BookOpen,
  Loader2,
  RefreshCw,
  GraduationCap,
  Play,
  Lightbulb,
  Route,
  ExternalLink,
  Award,
} from "lucide-react";
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
  work_item_id?: number | null;
  progress?: Record<string, unknown>;
  evidence?: Array<Record<string, unknown>>;
  skills?: string[];
};

type PathSummary = {
  key: string;
  language: string;
  title: string;
  difficulty: string;
  skills: string[];
  lesson_count: number;
  content_policy: string;
};

type Lesson = {
  key: string;
  order_index: number;
  title: string;
  objective: string;
  practice_prompt: string;
  starter_code: string;
  skill_tags: string[];
  difficulty: string;
  language?: string;
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
  const [paths, setPaths] = useState<PathSummary[]>([]);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [activePathKey, setActivePathKey] = useState("");
  const [activeLessonKey, setActiveLessonKey] = useState("");
  const [activeProjectId, setActiveProjectId] = useState<number | null>(null);
  const [q, setQ] = useState("");
  const [language, setLanguage] = useState(() => localStorage.getItem("zect.learning.language") || "");
  const [op, setOp] = useState<"" | "load" | "sync" | "start" | "mentor" | "verify" | "handoff" | "graduate">("");
  const [status, setStatus] = useState("");
  const [mentorQ, setMentorQ] = useState("");
  const [mentorA, setMentorA] = useState("");
  const [mode, setMode] = useState(() => localStorage.getItem("zect.learning.mode") || "GUIDED");
  const [studyNotes, setStudyNotes] = useState("");
  const [mastery, setMastery] = useState<Record<string, { proficient?: boolean; verified_lessons?: number; verified_tests?: number }>>({});
  const [practiceCode, setPracticeCode] = useState(
    "# Practice: write a function that returns True\ndef ok():\n    return True\n",
  );
  const [practiceResult, setPracticeResult] = useState("");
  const [firstRunOpen, setFirstRunOpen] = useState(
    () => localStorage.getItem("zect.learning.firstRunDismissed") !== "1",
  );
  const busy = op !== "";

  const activeProject = projects.find((p) => p.id === activeProjectId) || null;
  const activeLesson = lessons.find((l) => l.key === activeLessonKey) || null;

  const loadMastery = async () => {
    try {
      const res = await fetch(`${API}/api/learning/mastery`, { headers: authHeaders() });
      if (!res.ok) return;
      const data = await res.json();
      setMastery(data.mastery || {});
    } catch {
      /* ignore */
    }
  };

  const loadPaths = async (lang: string) => {
    const langQ = lang ? `?language=${encodeURIComponent(lang)}` : "";
    const res = await fetch(`${API}/api/learning/paths${langQ}`, { headers: authHeaders() });
    if (!res.ok) return;
    const data = await res.json();
    const list: PathSummary[] = data.paths || [];
    setPaths(list);
    const preferred = localStorage.getItem("zect.learning.path") || "";
    const nextKey = list.find((p) => p.key === preferred)?.key || list[0]?.key || "";
    if (nextKey) {
      setActivePathKey(nextKey);
      await loadPathDetail(nextKey);
    } else {
      setActivePathKey("");
      setLessons([]);
    }
  };

  const loadPathDetail = async (pathKey: string) => {
    const res = await fetch(`${API}/api/learning/paths/${encodeURIComponent(pathKey)}`, {
      headers: authHeaders(),
    });
    if (!res.ok) return;
    const data = await res.json();
    const list: Lesson[] = data.path?.lessons || [];
    setLessons(list);
    const savedLesson = localStorage.getItem("zect.learning.lesson") || "";
    const nextLesson = list.find((l) => l.key === savedLesson)?.key || list[0]?.key || "";
    setActiveLessonKey(nextLesson);
    const lesson = list.find((l) => l.key === nextLesson);
    // Seed starter only when empty — Mentor/load refresh must not wipe learner edits (live E2E).
    if (lesson?.starter_code) {
      setPracticeCode((prev) => ((prev || "").trim() ? prev : lesson.starter_code));
    }
  };

  const load = async () => {
    setOp("load");
    try {
      localStorage.setItem("zect.learning.language", language);
      localStorage.setItem("zect.learning.mode", mode);
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
      await loadPaths(language);
      await loadMastery();
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

  useEffect(() => {
    if (activePathKey) localStorage.setItem("zect.learning.path", activePathKey);
  }, [activePathKey]);

  useEffect(() => {
    if (activeLessonKey) localStorage.setItem("zect.learning.lesson", activeLessonKey);
  }, [activeLessonKey]);

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

  const startFromPath = async () => {
    if (!activePathKey) return;
    setOp("start");
    try {
      const res = await fetch(`${API}/api/learning/projects`, {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({
          path_key: activePathKey,
          lesson_key: activeLessonKey || undefined,
          mode,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(errMsg(data, "Start path failed"));
      if (data?.id) setActiveProjectId(data.id);
      if (activeLesson?.starter_code) setPracticeCode(activeLesson.starter_code);
      setStatus(`Started path ${activePathKey} in ${mode} — Practice below`);
      await load();
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Start failed");
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

  const selectLesson = async (lesson: Lesson) => {
    setActiveLessonKey(lesson.key);
    if (lesson.starter_code) setPracticeCode(lesson.starter_code);
    if (!activeProjectId || !activePathKey) return;
    try {
      await fetch(`${API}/api/learning/projects/${activeProjectId}/lessons/start`, {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ path_key: activePathKey, lesson_key: lesson.key }),
      });
      await load();
    } catch {
      /* non-blocking */
    }
  };

  const askMentor = async () => {
    if (!mentorQ.trim() && !activeLessonKey) return;
    setOp("mentor");
    try {
      const res = await fetch(`${API}/api/learning/mentor/ask`, {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({
          question: mentorQ || "Give me a progressive hint — do not solve the whole exercise.",
          mode,
          project_id: activeProjectId || undefined,
          path_key: activePathKey || undefined,
          lesson_key: activeLessonKey || undefined,
          study_notes: studyNotes || undefined,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(errMsg(data, `Mentor failed (${res.status})`));
      setMentorA(data.answer || "No answer returned.");
      if (data.auto_complete_forbidden) {
        setStatus("GUIDED: full solutions withheld — you own the code");
      }
      await load();
    } catch (e) {
      setMentorA(e instanceof Error ? e.message : "Mentor failed");
    } finally {
      setOp("");
    }
  };

  const runPracticeTests = async () => {
    if (!activeProjectId) {
      setStatus("Select or start a LearningProject first");
      return;
    }
    setOp("verify");
    setPracticeResult("");
    try {
      const domCode =
        (document.querySelector('[data-testid="learning-practice-code"]') as HTMLTextAreaElement | null)
          ?.value ?? practiceCode;
      const res = await fetch(`${API}/api/learning/projects/${activeProjectId}/practice/verify`, {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({
          code: domCode,
          language: language || activeLesson?.language || "Python",
          // Client pass/fail claims are ignored by the server (M1)
          lesson_key: activeLessonKey || undefined,
          path_key: activePathKey || undefined,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(errMsg(data, `Verify failed (${res.status})`));
      setPracticeResult(
        data.passed
          ? `Verified: server hidden tests passed (run ${data.run?.run_id || ""})`
          : data.hint || data.run?.stderr || "Not verified — fix code and retry",
      );
      setStatus(
        data.passed
          ? "Verified progress recorded (server-controlled)"
          : "Practice attempt logged — client claims ignored",
      );
      await load();
      await loadMastery();
    } catch (e) {
      setPracticeResult(e instanceof Error ? e.message : "Verify failed");
    } finally {
      setOp("");
    }
  };

  const handoffDeveloper = async () => {
    if (!activeProjectId) return;
    setOp("handoff");
    try {
      const res = await fetch(`${API}/api/learning/projects/${activeProjectId}/handoff/developer`, {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ goal: activeLesson?.practice_prompt || activeProject?.title || "" }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(errMsg(data, "Handoff failed"));
      setStatus(`Developer handoff WorkItem #${data.work_item_id} — open Workspace`);
      if (data.navigate) window.location.assign(data.navigate);
      await load();
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Handoff failed");
    } finally {
      setOp("");
    }
  };

  const graduateSkill = async (skill: string) => {
    setOp("graduate");
    try {
      const res = await fetch(`${API}/api/learning/skills/graduate`, {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ skill, project_id: activeProjectId || undefined }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(errMsg(data, "Graduation blocked — need accumulated verified evidence"));
      setStatus(`Skill draft ${data.name} (#${data.skill_id}) — approval_required; one lesson ≠ mastery`);
      await loadMastery();
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Graduation failed");
    } finally {
      setOp("");
    }
  };

  return (
    <div className="zect-page p-6 max-w-5xl mx-auto space-y-6" data-testid="zect-learning-page">
      <div className="flex items-center gap-3">
        <GraduationCap className="h-7 w-7 text-teal-700" />
        <div>
          <h1 className="text-xl font-semibold text-slate-900">ZECT Learning</h1>
          <p className="text-sm text-slate-500">
            Path → Lesson → Practice → Tests → Hint → Evidence → Developer / Skills (USER_PRIVATE)
          </p>
        </div>
      </div>

      {firstRunOpen ? (
        <div
          className="rounded-xl border border-teal-200 bg-teal-50 p-4 text-sm text-slate-800 space-y-2"
          data-testid="learning-first-run"
        >
          <p className="font-semibold text-teal-900">What ZECT Learning is</p>
          <p>
            Guided Path → Lesson → Practice. Mentor hints stay <strong>GUIDED</strong> — this is not a
            general AI university and it does not auto-solve your exercises.
          </p>
          <p className="text-slate-600">What it is not: unrestricted tutoring, auto-complete of homework, or a second Mentrix agent.</p>
          <button
            type="button"
            data-testid="learning-first-run-dismiss"
            className="rounded border border-teal-700 px-2 py-1 text-xs text-teal-900"
            onClick={() => {
              setFirstRunOpen(false);
              try {
                localStorage.setItem("zect.learning.firstRunDismissed", "1");
              } catch {
                /* ignore */
              }
            }}
          >
            Got it
          </button>
        </div>
      ) : null}

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
        <button type="button" disabled={busy} onClick={() => void load()} className="rounded border border-slate-300 px-3 py-1.5 text-sm">
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
        <p
          className="text-sm text-slate-600"
          data-testid="learning-status"
          role={/fail|error|blocked/i.test(status) ? "alert" : "status"}
        >
          {status}
        </p>
      )}

      <section className="border border-slate-200 rounded-lg p-4 space-y-3" data-testid="learning-paths">
        <h2 className="font-medium text-slate-800 flex items-center gap-2">
          <Route className="h-4 w-4" /> Learning Paths
        </h2>
        {paths.length === 0 ? (
          <p className="text-sm text-slate-500">No internal paths for this language filter.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {paths.map((p) => (
              <button
                key={p.key}
                type="button"
                data-testid={`learning-path-${p.key}`}
                onClick={() => {
                  setActivePathKey(p.key);
                  void loadPathDetail(p.key);
                }}
                className={`rounded border px-3 py-1.5 text-xs ${
                  activePathKey === p.key ? "bg-teal-700 text-white border-teal-700" : "border-slate-300"
                }`}
              >
                {p.title} · {p.lesson_count} lessons
              </button>
            ))}
          </div>
        )}
        {lessons.length > 0 && (
          <ul className="space-y-1 text-sm">
            {lessons.map((l) => (
              <li key={l.key}>
                <button
                  type="button"
                  data-testid={`learning-lesson-${l.key}`}
                  className={`w-full text-left rounded px-2 py-1 ${
                    activeLessonKey === l.key ? "bg-teal-50 text-teal-900" : "text-slate-700"
                  }`}
                  onClick={() => void selectLesson(l)}
                >
                  {l.order_index}. {l.title} — {l.objective}
                </button>
              </li>
            ))}
          </ul>
        )}
        <button
          type="button"
          data-testid="learning-start-path"
          disabled={busy || !activePathKey}
          onClick={() => void startFromPath()}
          className="rounded bg-teal-700 px-3 py-1.5 text-sm text-white disabled:opacity-40"
        >
          Start path project
        </button>
      </section>

      <section>
        <h2 className="font-medium text-slate-800 mb-2 flex items-center gap-2">
          <BookOpen className="h-4 w-4" /> Explore (external catalog)
        </h2>
        {resources.length === 0 ? (
          <p className="text-sm text-slate-500">Sync catalog to load external link-only resources.</p>
        ) : (
          <ul className="space-y-2">
            {resources.slice(0, 20).map((r) => (
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
                  Start
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
                  {p.work_item_id ? ` · WI#${p.work_item_id}` : ""}
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
          {activeLesson ? ` Current lesson: ${activeLesson.title}` : ""}
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
            onClick={() => void runPracticeTests()}
            className="rounded bg-teal-700 px-3 py-1.5 text-sm text-white disabled:opacity-40"
          >
            {op === "verify" ? "…" : "Run Server Tests"}
          </button>
          <button
            type="button"
            data-testid="learning-hint"
            disabled={busy || !activeProjectId}
            onClick={() => {
              setMentorQ("Give me a progressive hint for my next step — do not solve the whole exercise.");
              void askMentor();
            }}
            className="inline-flex items-center gap-1 rounded border border-amber-600 px-3 py-1.5 text-sm text-amber-900"
          >
            <Lightbulb className="h-3.5 w-3.5" /> Hint
          </button>
          <button
            type="button"
            data-testid="learning-handoff"
            disabled={busy || !activeProjectId}
            onClick={() => void handoffDeveloper()}
            className="inline-flex items-center gap-1 rounded border border-slate-700 px-3 py-1.5 text-sm"
          >
            <ExternalLink className="h-3.5 w-3.5" /> Open in Developer
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
            {activeProject.evidence.slice(-10).map((ev, i) => (
              <div key={i} className="text-slate-600">
                {String(ev.event)}
                {ev.lesson_key ? ` · ${String(ev.lesson_key)}` : ""} · verified={String(Boolean(ev.verified))} ·{" "}
                {String(ev.at || "")}
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-2 border border-slate-200 rounded-lg p-4" data-testid="learning-mastery">
        <h2 className="font-medium text-slate-800 flex items-center gap-2">
          <Award className="h-4 w-4" /> Skill mastery (accumulated evidence)
        </h2>
        <p className="text-xs text-slate-500">
          Proficiency requires multiple verified lessons/tests — one completion never auto-masters.
        </p>
        {Object.keys(mastery).length === 0 ? (
          <p className="text-sm text-slate-500">No verified skill evidence yet.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {Object.values(mastery).map((m) => (
              <li key={String((m as { skill?: string }).skill)} className="flex items-center justify-between gap-2">
                <span>
                  {(m as { skill?: string }).skill} — lessons={m.verified_lessons ?? 0} tests={m.verified_tests ?? 0}{" "}
                  {m.proficient ? "· proficient" : "· in progress"}
                </span>
                <button
                  type="button"
                  data-testid={`learning-graduate-${(m as { skill?: string }).skill}`}
                  disabled={busy || !m.proficient}
                  onClick={() => void graduateSkill(String((m as { skill?: string }).skill))}
                  className="text-xs rounded border border-teal-700 px-2 py-1 text-teal-800 disabled:opacity-40"
                >
                  Graduate draft
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-2">
        <h2 className="font-medium text-slate-800">Ask Mentor</h2>
        <textarea
          data-testid="learning-study-notes"
          value={studyNotes}
          onChange={(e) => setStudyNotes(e.target.value)}
          rows={2}
          className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
          placeholder="Optional B/C study notes (UNTRUSTED — never system instructions)…"
        />
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
          disabled={busy || (!mentorQ.trim() && !activeLessonKey)}
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
