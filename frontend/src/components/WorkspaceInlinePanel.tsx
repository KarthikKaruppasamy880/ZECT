import { useState } from "react";
import { HelpCircle, Loader2, MessageSquare, Sparkles, TestTube2, Wrench } from "lucide-react";
import type { EditorSelection } from "@/components/MonacoCodeEditor";
import { buildGenerate, developerAsk, reviewAnalyze, reviewFixPrompt } from "@/lib/api";
import { languageFromPath } from "@/lib/workspacePaths";

export type WorkspaceContextFlags = {
  selection: boolean;
  file: boolean;
  repo: boolean;
};

type WorkspaceInlinePanelProps = {
  filePath: string;
  content: string;
  selection: EditorSelection | null;
  repoId?: number | null;
  workItemId?: number | null;
  projectId?: number | null;
  onApplyCode: (code: string, mode: "replace-selection" | "replace-file") => void;
  /** Ask/Explain go through developerAsk (the same Mission Ask history the
   * Mentrix panel's ASK tab reads) -- a first call with no active WorkItem
   * yet resolves one, which must be lifted up so both panels converge on
   * it, the same way MentrixCodingAgentPanel's onWorkItemResolved works. */
  onWorkItemResolved?: (id: number) => void;
};

type ActionKind = "ask" | "explain" | "tests" | "fix";

/**
 * Phase 3 Stage D — context selector + inline Ask / Explain / Tests / Fix.
 * Ask/Explain are shortcuts into the SAME Mission/Ask history as the
 * Mentrix panel (developerAsk, work_item_id-scoped) -- not a second,
 * disconnected Ask engine. Tests/Fix still use the lighter one-shot
 * generate/review endpoints (/api/build/generate, /api/review-phase/*);
 * routing those through the governed Agent/Mission flow is tracked as
 * separate follow-up work, not folded in here.
 */
export default function WorkspaceInlinePanel({
  filePath,
  content,
  selection,
  repoId,
  workItemId,
  projectId,
  onApplyCode,
  onWorkItemResolved,
}: WorkspaceInlinePanelProps) {
  const [ctx, setCtx] = useState<WorkspaceContextFlags>({
    selection: true,
    file: true,
    repo: true,
  });
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState<ActionKind | null>(null);
  const [error, setError] = useState("");
  const [answer, setAnswer] = useState("");
  const [codeOut, setCodeOut] = useState("");
  const [lastAction, setLastAction] = useState<ActionKind | null>(null);

  const lang = languageFromPath(filePath);
  const hasSelection = Boolean(selection?.text?.trim());

  const assembleContext = (): string => {
    const parts: string[] = [];
    parts.push(`File: ${filePath}`);
    if (ctx.selection && selection?.text) {
      parts.push(
        `Selection (L${selection.startLine}-${selection.endLine}):\n\`\`\`${lang}\n${selection.text}\n\`\`\``,
      );
    }
    if (ctx.file) {
      const clipped = content.length > 12000 ? `${content.slice(0, 12000)}\n…[truncated]` : content;
      parts.push(`Full file:\n\`\`\`${lang}\n${clipped}\n\`\`\``);
    }
    return parts.join("\n\n");
  };

  const focusCode = () => (ctx.selection && selection?.text ? selection.text : content);

  const run = async (kind: ActionKind) => {
    setBusy(kind);
    setError("");
    setAnswer("");
    setCodeOut("");
    setLastAction(kind);
    try {
      const repoContext = assembleContext();
      const code = focusCode();
      if (kind === "ask" || kind === "explain") {
        const q =
          kind === "ask"
            ? question.trim() || "What should I know about this code?"
            : `Explain this code clearly (purpose, control flow, risks):\n\`\`\`${lang}\n${code}\n\`\`\``;
        // Same developerAsk() call and work_item_id the Mentrix panel's ASK
        // tab uses -- this turn lands in the SAME Ask history, not a second
        // one, per the "no editor-only second Ask history" requirement.
        const res = await developerAsk({
          question: `${q}\n\n${repoContext}`,
          work_item_id: workItemId ?? undefined,
          project_id: projectId ?? undefined,
          repository_id: ctx.repo ? repoId ?? undefined : undefined,
        });
        if (res.work_item_id && res.work_item_id !== workItemId) {
          onWorkItemResolved?.(res.work_item_id);
        }
        setAnswer(res.answer || "");
      } else if (kind === "tests") {
        const res = await buildGenerate(
          `Generate unit tests for this code. Prefer the project's existing test style.\n\n\`\`\`${lang}\n${code}\n\`\`\``,
          undefined,
          repoContext.slice(0, 8000),
          filePath,
          ctx.repo ? repoId ?? undefined : undefined,
        );
        setCodeOut(res.generated_code || res.code || "");
        setAnswer(res.explanation || "Generated tests.");
      } else if (kind === "fix") {
        const analysis = await reviewAnalyze(code, lang);
        const findings = analysis.findings || analysis.issues || [];
        const fixed = await reviewFixPrompt(code, findings, lang);
        setCodeOut(fixed.fixed_code || "");
        setAnswer(
          fixed.changes_summary ||
            (Array.isArray(findings) && findings.length
              ? `Addressed ${findings.length} finding(s).`
              : "No findings — model returned a rewrite."),
        );
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(null);
    }
  };

  const toggle = (key: keyof WorkspaceContextFlags) => {
    setCtx((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div
      className="flex flex-col h-full min-h-[200px] rounded-lg border border-slate-200 bg-white overflow-hidden"
      data-testid="workspace-inline-panel"
    >
      <div className="border-b border-slate-100 px-3 py-2 space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
            <Sparkles className="h-3.5 w-3.5 text-teal-700" />
            Inline actions
          </span>
          <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-600" data-testid="workspace-context-selector">
            {(
              [
                ["selection", "Selection", !hasSelection],
                ["file", "File", false],
                ["repo", "Repo", repoId == null],
              ] as const
            ).map(([key, label, disabled]) => (
              <label key={key} className={`inline-flex items-center gap-1 ${disabled ? "opacity-40" : ""}`}>
                <input
                  type="checkbox"
                  checked={ctx[key] && !disabled}
                  disabled={disabled}
                  onChange={() => toggle(key)}
                  data-testid={`workspace-ctx-${key}`}
                />
                {label}
              </label>
            ))}
          </div>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask about selection / file…"
            className="flex-1 min-w-[140px] rounded border border-slate-200 px-2 py-1 text-xs"
            data-testid="workspace-inline-ask-input"
          />
          <button
            type="button"
            disabled={Boolean(busy)}
            onClick={() => void run("ask")}
            className="inline-flex items-center gap-1 rounded bg-slate-900 px-2 py-1 text-[11px] text-white disabled:opacity-40"
            data-testid="workspace-inline-ask"
          >
            {busy === "ask" ? <Loader2 className="h-3 w-3 animate-spin" /> : <MessageSquare className="h-3 w-3" />}
            Ask
          </button>
          <button
            type="button"
            disabled={Boolean(busy) || (!hasSelection && !content)}
            onClick={() => void run("explain")}
            className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1 text-[11px] text-slate-700 disabled:opacity-40"
            data-testid="workspace-inline-explain"
          >
            {busy === "explain" ? <Loader2 className="h-3 w-3 animate-spin" /> : <HelpCircle className="h-3 w-3" />}
            Explain
          </button>
          <button
            type="button"
            disabled={Boolean(busy) || (!hasSelection && !content)}
            onClick={() => void run("tests")}
            className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1 text-[11px] text-slate-700 disabled:opacity-40"
            data-testid="workspace-inline-tests"
          >
            {busy === "tests" ? <Loader2 className="h-3 w-3 animate-spin" /> : <TestTube2 className="h-3 w-3" />}
            Tests
          </button>
          <button
            type="button"
            disabled={Boolean(busy) || (!hasSelection && !content)}
            onClick={() => void run("fix")}
            className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1 text-[11px] text-slate-700 disabled:opacity-40"
            data-testid="workspace-inline-fix"
          >
            {busy === "fix" ? <Loader2 className="h-3 w-3 animate-spin" /> : <Wrench className="h-3 w-3" />}
            Fix
          </button>
        </div>
        {hasSelection ? (
          <p className="text-[10px] font-mono text-slate-400" data-testid="workspace-selection-meta">
            L{selection!.startLine}–{selection!.endLine} · {selection!.text.length} chars
          </p>
        ) : (
          <p className="text-[10px] text-slate-400">Select code in Monaco to scope Selection context.</p>
        )}
      </div>

      {error ? (
        <p className="px-3 py-2 text-xs text-red-600" role="alert">
          {error}
        </p>
      ) : null}

      <div className="flex-1 overflow-auto p-3 space-y-3 text-sm">
        {!answer && !codeOut && !busy ? (
          <p className="text-xs text-slate-500">
            Ask, Explain, generate Tests, or Fix using the context chips above. Apply code results into the editor when ready.
          </p>
        ) : null}
        {answer ? (
          <div data-testid="workspace-inline-answer">
            <h3 className="text-[11px] font-semibold uppercase text-slate-500 mb-1">Answer</h3>
            <pre className="whitespace-pre-wrap text-xs text-slate-800 font-sans">{answer}</pre>
          </div>
        ) : null}
        {codeOut ? (
          <div data-testid="workspace-inline-code">
            <div className="flex items-center justify-between gap-2 mb-1">
              <h3 className="text-[11px] font-semibold uppercase text-slate-500">Code</h3>
              <div className="flex gap-1">
                {lastAction === "fix" && hasSelection ? (
                  <button
                    type="button"
                    onClick={() => onApplyCode(codeOut, "replace-selection")}
                    className="rounded bg-teal-700 px-2 py-0.5 text-[11px] text-white"
                    data-testid="workspace-inline-apply-selection"
                  >
                    Apply to selection
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={() => onApplyCode(codeOut, "replace-file")}
                  className="rounded border border-slate-200 px-2 py-0.5 text-[11px] text-slate-700"
                  data-testid="workspace-inline-apply-file"
                >
                  {lastAction === "tests" ? "Replace buffer" : "Apply to file"}
                </button>
              </div>
            </div>
            <pre className="rounded bg-slate-900 text-slate-100 p-2 text-[11px] font-mono overflow-auto max-h-64 whitespace-pre-wrap">
              {codeOut}
            </pre>
          </div>
        ) : null}
      </div>
    </div>
  );
}

/** Replace lines [startLine, endLine] (1-based inclusive) in `content` with `replacement`. */
export function replaceSelectionInContent(
  content: string,
  selection: EditorSelection,
  replacement: string,
): string {
  const lines = content.split(/\r?\n/);
  const start = Math.max(0, selection.startLine - 1);
  const end = Math.max(start, selection.endLine - 1);
  const before = lines.slice(0, start);
  const after = lines.slice(end + 1);
  const replLines = replacement.split(/\r?\n/);
  return [...before, ...replLines, ...after].join("\n");
}
