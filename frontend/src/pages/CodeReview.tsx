import { useState } from "react";
import { reviewPR, reviewSnippet, reviewPRInline, postPRComment, getPRComments } from "@/lib/api";
import type { ReviewResponse, ReviewFinding } from "@/types";
import {
  Shield,
  Bug,
  Zap,
  Code2,
  Layers,
  BookOpen,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Info,
  ChevronDown,
  ChevronRight,
  FileCode,
  Loader2,
  Sparkles,
  ClipboardList,
  ThumbsUp,
  Lightbulb,
  Copy,
  Wand2,
  Check,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/* Severity helpers                                                    */
/* ------------------------------------------------------------------ */
const SEVERITY_CONFIG: Record<string, { color: string; bg: string; icon: typeof AlertTriangle; label: string }> = {
  critical: { color: "text-red-700", bg: "bg-red-100", icon: XCircle, label: "Critical" },
  high: { color: "text-orange-700", bg: "bg-orange-100", icon: AlertTriangle, label: "High" },
  medium: { color: "text-yellow-700", bg: "bg-yellow-100", icon: Info, label: "Medium" },
  low: { color: "text-blue-700", bg: "bg-blue-100", icon: Info, label: "Low" },
  info: { color: "text-slate-600", bg: "bg-slate-100", icon: Info, label: "Info" },
};

const CATEGORY_ICONS: Record<string, typeof Bug> = {
  bugs: Bug,
  vulnerabilities: Shield,
  performance: Zap,
  code_quality: Code2,
  architecture: Layers,
  best_practices: BookOpen,
};

const CATEGORY_LABELS: Record<string, string> = {
  bugs: "Bugs & Logic Errors",
  vulnerabilities: "Security Vulnerabilities",
  performance: "Performance Issues",
  code_quality: "Code Quality",
  architecture: "Architecture",
  best_practices: "Best Practices",
};

function SeverityBadge({ severity }: { severity: string }) {
  const cfg = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.info;
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${cfg.bg} ${cfg.color}`}>
      <Icon className="h-3 w-3" />
      {cfg.label}
    </span>
  );
}

function QualityScoreRing({ score }: { score: number }) {
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 80 ? "#22c55e" : score >= 60 ? "#eab308" : score >= 40 ? "#f97316" : "#ef4444";

  return (
    <div className="relative w-28 h-28">
      <svg className="w-28 h-28 -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={radius} fill="none" stroke="#e2e8f0" strokeWidth="8" />
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-1000"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold text-slate-900">{score}</span>
        <span className="text-[10px] text-slate-500 uppercase tracking-wider">Quality</span>
      </div>
    </div>
  );
}

function FindingCard({ finding, index }: { finding: ReviewFinding; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const CatIcon = CATEGORY_ICONS[finding.category] || Code2;

  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start gap-3 p-4 text-left hover:bg-slate-50 transition-colors"
      >
        <span className="text-xs text-slate-400 font-mono mt-0.5 w-5 shrink-0">#{index + 1}</span>
        <CatIcon className="h-4 w-4 text-slate-500 mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <SeverityBadge severity={finding.severity} />
            <span className="text-sm font-medium text-slate-900 truncate">{finding.title}</span>
          </div>
          {finding.file && (
            <div className="flex items-center gap-1 mt-1 text-xs text-slate-500">
              <FileCode className="h-3 w-3" />
              {finding.file}
              {finding.line != null && <span className="text-slate-400">:{finding.line}</span>}
            </div>
          )}
        </div>
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-slate-400 mt-0.5 shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-slate-400 mt-0.5 shrink-0" />
        )}
      </button>

      {expanded && (
        <div className="border-t border-slate-100 p-4 bg-slate-50 space-y-3">
          <p className="text-sm text-slate-700">{finding.description}</p>

          {finding.code_snippet && (
            <div className="rounded bg-slate-900 p-3 overflow-x-auto">
              <pre className="text-xs text-slate-200 font-mono whitespace-pre-wrap">{finding.code_snippet}</pre>
            </div>
          )}

          {finding.suggestion && (
            <div className="flex items-start gap-2 bg-green-50 border border-green-200 rounded p-3">
              <Lightbulb className="h-4 w-4 text-green-600 mt-0.5 shrink-0" />
              <div>
                <p className="text-xs font-semibold text-green-800 uppercase mb-1">Suggestion</p>
                <p className="text-sm text-green-700">{finding.suggestion}</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main component                                                      */
/* ------------------------------------------------------------------ */
export default function CodeReview() {
  const [mode, setMode] = useState<"pr" | "snippet">("pr");
  const [owner, setOwner] = useState("KarthikKaruppasamy880");
  const [repo, setRepo] = useState("ZECT");
  const [prNumber, setPrNumber] = useState("");
  const [snippetCode, setSnippetCode] = useState("");
  const [snippetLang, setSnippetLang] = useState("typescript");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [review, setReview] = useState<ReviewResponse | null>(null);
  const [activeFilter, setActiveFilter] = useState<string | null>(null);
  const [promptCopied, setPromptCopied] = useState(false);
  const [showPrompt, setShowPrompt] = useState(false);
  // Inline PR review state
  const [inlineReviewLoading, setInlineReviewLoading] = useState(false);
  const [inlineComments, setInlineComments] = useState<any[]>([]);
  const [showInlinePanel, setShowInlinePanel] = useState(false);
  const [newComment, setNewComment] = useState("");
  const [commentPath, setCommentPath] = useState("");
  const [commentLine, setCommentLine] = useState("");
  const [postingComment, setPostingComment] = useState(false);
  const [inlineSuccess, setInlineSuccess] = useState("");

  const runReview = async () => {
    setError(null);
    setLoading(true);
    setReview(null);
    setActiveFilter(null);
    try {
      if (mode === "pr") {
        if (!owner || !repo || !prNumber) {
          setError("Please fill in owner, repo, and PR number.");
          return;
        }
        const result = await reviewPR(owner, repo, Number(prNumber));
        setReview(result);
      } else {
        if (!snippetCode.trim()) {
          setError("Please paste some code to review.");
          return;
        }
        const result = await reviewSnippet(snippetCode, snippetLang || undefined);
        setReview(result);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Review failed");
    } finally {
      setLoading(false);
    }
  };

  const filteredFindings = review
    ? activeFilter
      ? review.findings.filter((f) => f.category === activeFilter)
      : review.findings
    : [];

  const severityCounts = review
    ? review.findings.reduce<Record<string, number>>((acc, f) => {
        acc[f.severity] = (acc[f.severity] || 0) + 1;
        return acc;
      }, {})
    : {};

  // Inline PR review functions
  const runInlineReview = async () => {
    if (!owner || !repo || !prNumber) {
      setError("Please fill in owner, repo, and PR number.");
      return;
    }
    setInlineReviewLoading(true);
    setError(null);
    setInlineSuccess("");
    try {
      const result = await reviewPRInline(owner, repo, Number(prNumber), true);
      setReview(result.review || result);
      setShowInlinePanel(true);
      setInlineSuccess(`Posted ${result.posted_comments?.length || 0} inline comments to PR #${prNumber}`);
      // Load existing comments
      loadPRComments();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Inline review failed");
    } finally {
      setInlineReviewLoading(false);
    }
  };

  const loadPRComments = async () => {
    if (!owner || !repo || !prNumber) return;
    try {
      const comments = await getPRComments(owner, repo, Number(prNumber));
      setInlineComments(comments);
    } catch { /* ignore */ }
  };

  const handlePostComment = async () => {
    if (!newComment.trim() || !owner || !repo || !prNumber) return;
    setPostingComment(true);
    try {
      await postPRComment(
        owner, repo, Number(prNumber), newComment,
        undefined,
        commentPath || undefined,
        commentLine ? Number(commentLine) : undefined
      );
      setNewComment("");
      setCommentPath("");
      setCommentLine("");
      setInlineSuccess("Comment posted to GitHub!");
      loadPRComments();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to post comment");
    } finally {
      setPostingComment(false);
    }
  };

  const generateFixPrompt = (r: ReviewResponse): string => {
    const lines: string[] = [];
    lines.push("# ZECT Code Review — Fix Prompt");
    lines.push("");
    if (r.repo) lines.push(`**Repository:** ${r.repo}`);
    if (r.pr_number) lines.push(`**PR:** #${r.pr_number}`);
    lines.push(`**Quality Score:** ${r.quality_score}/100`);
    lines.push(`**Total Issues:** ${r.total_issues}`);
    lines.push("");
    lines.push("## Instructions");
    lines.push("Fix ALL of the following issues identified by the ZECT Code Review Engine.");
    lines.push("For each issue, apply the suggested fix. Do not introduce new issues.");
    lines.push("After fixing, run lint and type checks to ensure 0 errors.");
    lines.push("");

    // Group findings by severity
    const bySeverity: Record<string, ReviewFinding[]> = {};
    for (const f of r.findings) {
      (bySeverity[f.severity] ||= []).push(f);
    }

    const severityOrder = ["critical", "high", "medium", "low", "info"];
    for (const sev of severityOrder) {
      const items = bySeverity[sev];
      if (!items || items.length === 0) continue;
      lines.push(`## ${sev.toUpperCase()} (${items.length} issue${items.length > 1 ? "s" : ""})`);
      lines.push("");
      for (const f of items) {
        lines.push(`### ${f.title}`);
        lines.push(`- **Category:** ${CATEGORY_LABELS[f.category] || f.category}`);
        if (f.file) lines.push(`- **File:** ${f.file}${f.line != null ? `:${f.line}` : ""}`);
        lines.push(`- **Problem:** ${f.description}`);
        if (f.suggestion) lines.push(`- **Fix:** ${f.suggestion}`);
        if (f.code_snippet) {
          lines.push("- **Code:**");
          lines.push("```");
          lines.push(f.code_snippet);
          lines.push("```");
        }
        lines.push("");
      }
    }

    if (r.recommendations.length > 0) {
      lines.push("## Additional Recommendations");
      for (const rec of r.recommendations) {
        lines.push(`- ${rec}`);
      }
      lines.push("");
    }

    lines.push("## Completion Criteria");
    lines.push("1. All issues above are resolved");
    lines.push("2. No new issues introduced");
    lines.push("3. Lint passes with 0 errors");
    lines.push("4. TypeScript compiles with 0 errors");
    lines.push("5. All existing tests pass");

    return lines.join("\n");
  };

  return (
    <div className="max-w-6xl">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <Shield className="h-6 w-6 text-indigo-600" />
          ZECT Code Review Engine
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          AI-powered code analysis — identifies bugs, vulnerabilities, performance issues, and architectural problems
        </p>
      </div>

      {/* Input Panel */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        {/* Mode tabs */}
        <div className="flex gap-1 mb-5 bg-slate-100 rounded-lg p-1 w-fit">
          <button
            onClick={() => setMode("pr")}
            className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
              mode === "pr" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            PR Review
          </button>
          <button
            onClick={() => setMode("snippet")}
            className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
              mode === "snippet" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Code Snippet
          </button>
        </div>

        {mode === "pr" ? (
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Repository Owner</label>
              <input
                type="text"
                value={owner}
                onChange={(e) => setOwner(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="KarthikKaruppasamy880"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Repository Name</label>
              <input
                type="text"
                value={repo}
                onChange={(e) => setRepo(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="ZECT"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">PR Number</label>
              <input
                type="text"
                value={prNumber}
                onChange={(e) => setPrNumber(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="10"
              />
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Language</label>
              <select
                value={snippetLang}
                onChange={(e) => setSnippetLang(e.target.value)}
                className="border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="typescript">TypeScript</option>
                <option value="python">Python</option>
                <option value="javascript">JavaScript</option>
                <option value="java">Java</option>
                <option value="go">Go</option>
                <option value="rust">Rust</option>
                <option value="csharp">C#</option>
                <option value="unknown">Other</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Code</label>
              <textarea
                value={snippetCode}
                onChange={(e) => setSnippetCode(e.target.value)}
                rows={10}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="Paste your code here..."
              />
            </div>
          </div>
        )}

        <div className="mt-5 flex items-center gap-3">
          <button
            onClick={runReview}
            disabled={loading}
            className="flex items-center gap-2 bg-indigo-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Analysing...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Run ZECT Review
              </>
            )}
          </button>
          {mode === "pr" && (
            <button
              onClick={runInlineReview}
              disabled={inlineReviewLoading || !owner || !repo || !prNumber}
              className="flex items-center gap-2 bg-green-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-green-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {inlineReviewLoading ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> Posting Inline Review...</>
              ) : (
                <><FileCode className="h-4 w-4" /> Review &amp; Post to GitHub</>
              )}
            </button>
          )}
          {error && <p className="text-sm text-red-600">{error}</p>}
          {inlineSuccess && <p className="text-sm text-green-600">{inlineSuccess}</p>}
        </div>
      </div>

      {/* Inline PR Comments Panel */}
      {showInlinePanel && mode === "pr" && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
              <FileCode className="h-4 w-4 text-green-600" />
              Inline PR Comments ({inlineComments.length})
            </h3>
            <button onClick={loadPRComments} className="text-xs text-indigo-600 hover:text-indigo-700">Refresh</button>
          </div>

          {/* Post new comment */}
          <div className="bg-slate-50 rounded-lg p-4 space-y-3">
            <p className="text-xs font-medium text-slate-600 uppercase tracking-wide">Post a Comment to PR</p>
            <div className="grid grid-cols-2 gap-3">
              <input
                type="text"
                placeholder="File path (optional, e.g. src/app.ts)"
                value={commentPath}
                onChange={(e) => setCommentPath(e.target.value)}
                className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:border-green-500 outline-none"
              />
              <input
                type="text"
                placeholder="Line number (optional)"
                value={commentLine}
                onChange={(e) => setCommentLine(e.target.value)}
                className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:border-green-500 outline-none"
              />
            </div>
            <textarea
              placeholder="Write your review comment..."
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:border-green-500 outline-none"
            />
            <button
              onClick={handlePostComment}
              disabled={postingComment || !newComment.trim()}
              className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
            >
              {postingComment ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              Post Comment to GitHub
            </button>
          </div>

          {/* Existing comments list */}
          {inlineComments.length > 0 && (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {inlineComments.map((comment: any, i: number) => (
                <div key={i} className="border border-slate-200 rounded-lg p-3 bg-slate-50">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium text-slate-700">{comment.user || "ZECT"}</span>
                    <span className="text-xs text-slate-400">{comment.created_at}</span>
                    {comment.path && (
                      <span className="text-xs text-indigo-600 font-mono">{comment.path}:{comment.line}</span>
                    )}
                  </div>
                  <p className="text-sm text-slate-700">{comment.body}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center mb-6">
          <Loader2 className="h-10 w-10 animate-spin text-indigo-500 mx-auto mb-4" />
          <p className="text-sm font-medium text-slate-700">ZECT Review Engine is analysing...</p>
          <p className="text-xs text-slate-500 mt-1">Scanning for bugs, vulnerabilities, and code quality issues</p>
        </div>
      )}

      {/* Results */}
      {review && !loading && (
        <div className="space-y-6">
          {/* Summary Header */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <div className="flex items-start gap-6">
              <QualityScoreRing score={review.quality_score} />
              <div className="flex-1">
                <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <ClipboardList className="h-5 w-5 text-indigo-600" />
                  Review Summary
                </h2>
                {review.repo && (
                  <p className="text-xs text-slate-500 mt-0.5">
                    {review.repo} — PR #{review.pr_number}
                  </p>
                )}
                <p className="text-sm text-slate-700 mt-2">{review.summary}</p>

                {/* Severity breakdown bar */}
                <div className="flex items-center gap-4 mt-4">
                  {(["critical", "high", "medium", "low", "info"] as const).map((sev) =>
                    severityCounts[sev] ? (
                      <div key={sev} className="flex items-center gap-1">
                        <SeverityBadge severity={sev} />
                        <span className="text-xs font-medium text-slate-600">{severityCounts[sev]}</span>
                      </div>
                    ) : null,
                  )}
                </div>

                {/* Token usage */}
                <div className="flex items-center gap-4 mt-3 text-xs text-slate-500">
                  <span>Model: {review.model}</span>
                  <span>Tokens: {review.tokens_used.toLocaleString()}</span>
                  <span>Issues: {review.total_issues}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Category breakdown */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">Issue Categories</h3>
            <div className="grid grid-cols-3 gap-3">
              {Object.entries(review.categories).map(([cat, count]) => {
                const CatIcon = CATEGORY_ICONS[cat] || Code2;
                const isActive = activeFilter === cat;
                return (
                  <button
                    key={cat}
                    onClick={() => setActiveFilter(isActive ? null : cat)}
                    className={`flex items-center gap-3 p-3 rounded-lg border text-left transition-colors ${
                      isActive
                        ? "border-indigo-300 bg-indigo-50"
                        : count > 0
                          ? "border-slate-200 hover:border-indigo-200 hover:bg-indigo-50/50"
                          : "border-slate-100 bg-slate-50 opacity-50 cursor-default"
                    }`}
                    disabled={count === 0}
                  >
                    <CatIcon className={`h-5 w-5 ${isActive ? "text-indigo-600" : "text-slate-500"}`} />
                    <div>
                      <p className="text-sm font-medium text-slate-900">{count}</p>
                      <p className="text-xs text-slate-500">{CATEGORY_LABELS[cat] || cat}</p>
                    </div>
                  </button>
                );
              })}
            </div>
            {activeFilter && (
              <button
                onClick={() => setActiveFilter(null)}
                className="mt-3 text-xs text-indigo-600 hover:text-indigo-700"
              >
                Clear filter — show all findings
              </button>
            )}
          </div>

          {/* Findings list */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">
              Findings ({filteredFindings.length})
              {activeFilter && (
                <span className="ml-2 text-xs font-normal text-slate-500">
                  filtered by {CATEGORY_LABELS[activeFilter] || activeFilter}
                </span>
              )}
            </h3>
            {filteredFindings.length === 0 ? (
              <div className="text-center py-8">
                <CheckCircle2 className="h-8 w-8 text-green-500 mx-auto mb-2" />
                <p className="text-sm text-slate-600">No issues found in this category</p>
              </div>
            ) : (
              <div className="space-y-2">
                {filteredFindings.map((f, i) => (
                  <FindingCard key={i} finding={f} index={i} />
                ))}
              </div>
            )}
          </div>

          {/* Generate Fix Prompt */}
          {review.findings.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                  <Wand2 className="h-4 w-4 text-purple-600" />
                  Agent Fix Prompt
                </h3>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowPrompt(!showPrompt)}
                    className="text-xs text-indigo-600 hover:text-indigo-700 font-medium"
                  >
                    {showPrompt ? "Hide Prompt" : "Show Prompt"}
                  </button>
                  <button
                    onClick={() => {
                      const prompt = generateFixPrompt(review);
                      navigator.clipboard.writeText(prompt);
                      setPromptCopied(true);
                      setTimeout(() => setPromptCopied(false), 2000);
                    }}
                    className="flex items-center gap-1.5 bg-purple-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-purple-700 transition-colors"
                  >
                    {promptCopied ? (
                      <><Check className="h-4 w-4" /> Copied!</>
                    ) : (
                      <><Copy className="h-4 w-4" /> Copy Fix Prompt for Agent</>
                    )}
                  </button>
                </div>
              </div>
              <p className="text-xs text-slate-500 mb-3">
                Copy this structured prompt and send it to any AI agent (Devin, Cursor, etc.) to automatically fix all issues found in this review.
              </p>
              {showPrompt && (
                <div className="rounded-lg bg-slate-900 p-4 overflow-x-auto max-h-96 overflow-y-auto">
                  <pre className="text-xs text-slate-200 font-mono whitespace-pre-wrap">{generateFixPrompt(review)}</pre>
                </div>
              )}
            </div>
          )}

          {/* Strengths & Recommendations */}
          <div className="grid grid-cols-2 gap-6">
            {review.strengths.length > 0 && (
              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <h3 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
                  <ThumbsUp className="h-4 w-4 text-green-600" />
                  Strengths
                </h3>
                <ul className="space-y-2">
                  {review.strengths.map((s, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                      <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {review.recommendations.length > 0 && (
              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <h3 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
                  <Lightbulb className="h-4 w-4 text-amber-500" />
                  Recommendations
                </h3>
                <ul className="space-y-2">
                  {review.recommendations.map((r, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                      <Lightbulb className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
                      {r}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
