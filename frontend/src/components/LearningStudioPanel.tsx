/**
 * Learning Studio — catalog/lesson/quiz grounded in indexed Lattice + Knowledge
 * Base content for the active workspace. Distinct from the Path/Lesson/Practice
 * coding-tutor flow on this same page: this teaches *this* codebase/company
 * knowledge, sourced only from what's actually indexed. Never invents content —
 * if the index isn't READY, the only action offered is re-index.
 */
import { useEffect, useState } from "react";
import { BookMarked, Loader2, RefreshCw } from "lucide-react";
import { authHeaders } from "@/lib/api";
import { useWorkspaceRepoContext } from "@/hooks/useWorkspaceRepoContext";

const API = import.meta.env.VITE_API_URL || "";

type SourceRef = { type: string; id: string; path?: string; title?: string };
type Topic = { topic_id: string; title: string; kind: string; source_refs: SourceRef[] };
type Lesson = { topic_id: string; body: string; source_refs: SourceRef[] };
type QuizQuestion = { question: string; answer: string; source_ref: SourceRef };

export default function LearningStudioPanel() {
  const { projectKey } = useWorkspaceRepoContext();
  const [status, setStatus] = useState<{ state: string } | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [quiz, setQuiz] = useState<QuizQuestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadCatalog = async () => {
    if (!projectKey) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(
        `${API}/api/learning-studio/catalog?project_key=${encodeURIComponent(projectKey)}`,
        { headers: authHeaders() },
      );
      const data = await res.json();
      setStatus(data.status || null);
      setTopics(data.topics || []);
    } catch {
      setError("Could not load Learning Studio catalog.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCatalog();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectKey]);

  const openLesson = async (topicId: string) => {
    setLoading(true);
    setError("");
    setQuiz([]);
    try {
      const res = await fetch(
        `${API}/api/learning-studio/lesson/${encodeURIComponent(topicId)}?project_key=${encodeURIComponent(projectKey || "")}`,
        { headers: authHeaders() },
      );
      if (!res.ok) {
        setError("Lesson not available — re-index may be required.");
        setLesson(null);
        return;
      }
      setLesson(await res.json());
    } catch {
      setError("Could not load lesson.");
    } finally {
      setLoading(false);
    }
  };

  const generateQuiz = async (topicId: string) => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(
        `${API}/api/learning-studio/quiz/${encodeURIComponent(topicId)}/generate?project_key=${encodeURIComponent(projectKey || "")}`,
        { method: "POST", headers: authHeaders() },
      );
      if (!res.ok) {
        setError("Quiz not available for this topic.");
        return;
      }
      const data = await res.json();
      setQuiz(data.questions || []);
    } catch {
      setError("Could not generate quiz.");
    } finally {
      setLoading(false);
    }
  };

  const notReady = status && status.state !== "READY";

  return (
    <div
      className="rounded-xl border border-slate-200 bg-white p-4 space-y-3"
      data-testid="learning-studio-panel"
    >
      <div className="flex items-center gap-2">
        <BookMarked className="h-5 w-5 text-teal-700" />
        <h2 className="text-sm font-semibold text-slate-900">Learning Studio</h2>
        {loading && <Loader2 className="h-4 w-4 animate-spin text-slate-400" />}
      </div>
      <p className="text-xs text-slate-500">
        Grounded in this workspace's indexed Lattice graph and Knowledge Base — never invented.
      </p>

      {!projectKey && (
        <p className="text-xs text-amber-700" data-testid="learning-studio-no-project">
          Select a project/repository to load Learning Studio.
        </p>
      )}

      {projectKey && notReady && (
        <div
          className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800"
          data-testid="learning-studio-not-ready"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Index state: {status?.state}. Re-index before Learning Studio content is available.
        </div>
      )}

      {error && <p className="text-xs text-red-600">{error}</p>}

      {projectKey && !notReady && (
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1" data-testid="learning-studio-catalog">
            {topics.length === 0 && <p className="text-xs text-slate-400">No indexed topics yet.</p>}
            {topics.map((t) => (
              <button
                key={t.topic_id}
                type="button"
                onClick={() => openLesson(t.topic_id)}
                className="block w-full rounded border border-slate-200 px-2 py-1.5 text-left text-xs hover:bg-slate-50"
                data-testid={`learning-studio-topic-${t.topic_id}`}
              >
                {t.title} <span className="text-slate-400">({t.kind})</span>
              </button>
            ))}
          </div>

          <div className="space-y-2" data-testid="learning-studio-lesson">
            {lesson && (
              <>
                <p className="text-xs text-slate-700 whitespace-pre-wrap">{lesson.body}</p>
                <p className="text-[11px] text-slate-400">
                  Source: {lesson.source_refs.map((r) => r.path || r.title || r.id).join(", ")}
                </p>
                <button
                  type="button"
                  onClick={() => generateQuiz(lesson.topic_id)}
                  className="rounded border border-teal-700 px-2 py-1 text-xs text-teal-900"
                  data-testid="learning-studio-generate-quiz"
                >
                  Generate quiz
                </button>
                {quiz.map((q, i) => (
                  <div key={i} className="rounded border border-slate-100 p-2 text-xs">
                    <p className="font-medium">{q.question}</p>
                    <p className="text-slate-500">{q.answer}</p>
                  </div>
                ))}
              </>
            )}
            {!lesson && <p className="text-xs text-slate-400">Pick a topic to open its lesson.</p>}
          </div>
        </div>
      )}
    </div>
  );
}
