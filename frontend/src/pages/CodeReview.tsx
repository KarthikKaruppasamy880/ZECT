import { useState } from "react";
import { reviewPR, reviewSnippet, reviewPRInline, postPRComment, getPRComments, reviewRepo, reviewAutoFixLoop, reviewEvaluateRules, configureWebhook, getWebhookConfig } from "@/lib/api";
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
  GitBranch,
  Globe,
  Settings,
  RotateCcw,
  FolderSearch,
  ToggleLeft,
  ToggleRight,
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
  const [mode, setMode] = useState<"pr" | "snippet" | "repo" | "autofix" | "webhook">("pr");
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
  // Full repo scan state
  const [repoBranch, setRepoBranch] = useState("");
  const [filePatterns, setFilePatterns] = useState("");
  const [repoScanResult, setRepoScanResult] = useState<any>(null);
  // Auto-fix loop state
  const [maxIterations, setMaxIterations] = useState(3);
  const [autoComment, setAutoComment] = useState(true);
  const [autoFixResult, setAutoFixResult] = useState<any>(null);
  const [useRulesEngine, setUseRulesEngine] = useState(false);
  const [rulesResult, setRulesResult] = useState<any>(null);
  // Webhook config state
  const [webhookEnabled, setWebhookEnabled] = useState(false);
  const [webhookAutoReview, setWebhookAutoReview] = useState(true);
  const [webhookAutoComment, setWebhookAutoComment] = useState(true);
  const [webhookSecret, setWebhookSecret] = useState("");
  const [webhookSaved, setWebhookSaved] = useState(false);
  const [webhookLoading, setWebhookLoading] = useState(false);

  const runReview = async () => {
    setError(null);
    setLoading(true);
    setReview(null);
    setActiveFilter(null);
    setRepoScanResult(null);
    setAutoFixResult(null);
    setRulesResult(null);
    try {
      if (mode === "pr") {
        if (!owner || !repo || !prNumber) {
          setError("Please fill in owner, repo, and PR number.");
          return;
        }
        if (useRulesEngine) {
          const result = await reviewEvaluateRules(owner, repo, Number(prNumber));
          setRulesResult(result);
          if (result.review) setReview(result.review);
        } else {
          const result = await reviewPR(owner, repo, Number(prNumber));
          setReview(result);
        }
      } else if (mode === "snippet") {
        if (!snippetCode.trim()) {
          setError("Please paste some code to review.");
          return;
        }
        const result = await reviewSnippet(snippetCode, snippetLang || undefined);
        setReview(result);
      } else if (mode === "repo") {
        if (!owner || !repo) {
          setError("Please fill in owner and repo.");
          return;
        }
        const patterns = filePatterns.trim() ? filePatterns.split(",").map((p) => p.trim()) : undefined;
        const result = await reviewRepo(owner, repo, repoBranch || undefined, patterns);
        setReview(result);
        setRepoScanResult(result);
      } else if (mode === "autofix") {
        if (!owner || !repo || !prNumber) {
          setError("Please fill in owner, repo, and PR number.");
          return;
        }
        const result = await reviewAutoFixLoop(owner, repo, Number(prNumber), maxIterations, autoComment);
        setAutoFixResult(result);
        // Set last iteration's review if available
        const lastIter = result.iterations?.[result.iterations.length - 1];
        if (lastIter?.findings) {
          setReview({
            summary: `Auto-fix loop completed: ${result.total_iterations} iteration(s)`,
            quality_score: lastIter.quality_score || 0,
            total_issues: lastIter.total_issues || 0,
            categories: {},
            findings: lastIter.findings || [],
            strengths: [],
            recommendations: [],
            tokens_used: result.total_tokens_used || 0,
            model: "gpt-4o-mini",
          });
        }
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Review failed");
    } finally {
      setLoading(false);
    }
  };

  const saveWebhookConfig = async () => {
    if (!owner || !repo) {
      setError("Please fill in owner and repo.");
      return;
    }
    setWebhookLoading(true);
    setError(null);
    setWebhookSaved(false);
    try {
      await configureWebhook(owner, repo, webhookEnabled, webhookAutoReview, webhookAutoComment, webhookSecret);
      setWebhookSaved(true);
      setTimeout(() => setWebhookSaved(false), 3000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save webhook config");
    } finally {
      setWebhookLoading(false);
    }
  };

  const loadWebhookConfig = async () => {
    if (!owner || !repo) return;
    try {
      const config = await getWebhookConfig(owner, repo);
      setWebhookEnabled(config.enabled || false);
      setWebhookAutoReview(config.auto_review !== false);
      setWebhookAutoComment(config.auto_comment !== false);
      setWebhookSecret(config.webhook_secret || "");
    } catch { /* ignore */ }
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
        <div className="flex gap-1 mb-5 bg-slate-100 rounded-lg p-1 w-fit flex-wrap">
          <button
            onClick={() => setMode("pr")}
            className={`flex items-center gap-1.5 px-4 py-1.5 rounded text-sm font-medium transition-colors ${
              mode === "pr" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            <GitBranch className="h-3.5 w-3.5" />
            PR Review
          </button>
          <button
            onClick={() => setMode("snippet")}
            className={`flex items-center gap-1.5 px-4 py-1.5 rounded text-sm font-medium transition-colors ${
              mode === "snippet" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            <Code2 className="h-3.5 w-3.5" />
            Snippet
          </button>
          <button
            onClick={() => setMode("repo")}
            className={`flex items-center gap-1.5 px-4 py-1.5 rounded text-sm font-medium transition-colors ${
              mode === "repo" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            <FolderSearch className="h-3.5 w-3.5" />
            Full Repo Scan
          </button>
          <button
            onClick={() => setMode("autofix")}
            className={`flex items-center gap-1.5 px-4 py-1.5 rounded text-sm font-medium transition-colors ${
              mode === "autofix" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Auto-Fix Loop
          </button>
          <button
            onClick={() => { setMode("webhook"); loadWebhookConfig(); }}
            className={`flex items-center gap-1.5 px-4 py-1.5 rounded text-sm font-medium transition-colors ${
              mode === "webhook" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            <Globe className="h-3.5 w-3.5" />
            Webhook
          </button>
        </div>

        {/* --- PR Review Mode --- */}
        {mode === "pr" && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Repository Owner</label>
                <input type="text" value={owner} onChange={(e) => setOwner(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="KarthikKaruppasamy880" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Repository Name</label>
                <input type="text" value={repo} onChange={(e) => setRepo(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="ZECT" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">PR Number</label>
                <input type="text" value={prNumber} onChange={(e) => setPrNumber(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="10" />
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
              <input type="checkbox" checked={useRulesEngine} onChange={(e) => setUseRulesEngine(e.target.checked)} className="rounded border-slate-300" />
              <Shield className="h-3.5 w-3.5 text-indigo-500" />
              Also evaluate Rules Engine rules
            </label>
          </div>
        )}

        {/* --- Snippet Mode --- */}
        {mode === "snippet" && (
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Language</label>
              <select value={snippetLang} onChange={(e) => setSnippetLang(e.target.value)}
                className="border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
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
              <textarea value={snippetCode} onChange={(e) => setSnippetCode(e.target.value)} rows={10}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="Paste your code here..." />
            </div>
          </div>
        )}

        {/* --- Full Repo Scan Mode --- */}
        {mode === "repo" && (
          <div className="space-y-4">
            <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3 flex items-start gap-2">
              <FolderSearch className="h-4 w-4 text-indigo-600 mt-0.5 shrink-0" />
              <p className="text-xs text-indigo-700">
                Scans ALL source files in the repository — not just PR changes. Ideal for new repos, legacy code audits, and full security reviews.
              </p>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Repository Owner</label>
                <input type="text" value={owner} onChange={(e) => setOwner(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="KarthikKaruppasamy880" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Repository Name</label>
                <input type="text" value={repo} onChange={(e) => setRepo(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="ZECT" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Branch (optional)</label>
                <input type="text" value={repoBranch} onChange={(e) => setRepoBranch(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="main" />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">File Patterns (optional, comma-separated)</label>
              <input type="text" value={filePatterns} onChange={(e) => setFilePatterns(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="*.py, src/**/*.ts, backend/**" />
            </div>
          </div>
        )}

        {/* --- Auto-Fix Loop Mode --- */}
        {mode === "autofix" && (
          <div className="space-y-4">
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-2">
              <RotateCcw className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
              <p className="text-xs text-amber-700">
                Automatically reviews a PR, generates fix suggestions, and posts them as inline comments. Repeats up to max iterations until quality improves.
              </p>
            </div>
            <div className="grid grid-cols-4 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Repository Owner</label>
                <input type="text" value={owner} onChange={(e) => setOwner(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="KarthikKaruppasamy880" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Repository Name</label>
                <input type="text" value={repo} onChange={(e) => setRepo(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="ZECT" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">PR Number</label>
                <input type="text" value={prNumber} onChange={(e) => setPrNumber(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="10" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Max Iterations</label>
                <input type="number" min={1} max={10} value={maxIterations} onChange={(e) => setMaxIterations(Number(e.target.value))}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
              <input type="checkbox" checked={autoComment} onChange={(e) => setAutoComment(e.target.checked)} className="rounded border-slate-300" />
              Auto-post fix suggestions as PR comments
            </label>
          </div>
        )}

        {/* --- Webhook Config Mode --- */}
        {mode === "webhook" && (
          <div className="space-y-4">
            <div className="bg-green-50 border border-green-200 rounded-lg p-3 flex items-start gap-2">
              <Globe className="h-4 w-4 text-green-600 mt-0.5 shrink-0" />
              <div className="text-xs text-green-700">
                <p className="font-medium mb-1">Auto-trigger code review on new PRs</p>
                <p>Configure a GitHub webhook to automatically run ZECT Code Review when PRs are opened or updated. Use Rules Engine to control when auto-review runs.</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Repository Owner</label>
                <input type="text" value={owner} onChange={(e) => setOwner(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="KarthikKaruppasamy880" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Repository Name</label>
                <input type="text" value={repo} onChange={(e) => setRepo(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="ZECT" />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <button onClick={() => setWebhookEnabled(!webhookEnabled)}
                className={`flex items-center justify-center gap-2 p-3 rounded-lg border text-sm font-medium transition-colors ${webhookEnabled ? "border-green-300 bg-green-50 text-green-700" : "border-slate-200 text-slate-500"}`}>
                {webhookEnabled ? <ToggleRight className="h-4 w-4" /> : <ToggleLeft className="h-4 w-4" />}
                {webhookEnabled ? "Enabled" : "Disabled"}
              </button>
              <button onClick={() => setWebhookAutoReview(!webhookAutoReview)}
                className={`flex items-center justify-center gap-2 p-3 rounded-lg border text-sm font-medium transition-colors ${webhookAutoReview ? "border-indigo-300 bg-indigo-50 text-indigo-700" : "border-slate-200 text-slate-500"}`}>
                <Sparkles className="h-4 w-4" />
                {webhookAutoReview ? "Auto-Review On" : "Auto-Review Off"}
              </button>
              <button onClick={() => setWebhookAutoComment(!webhookAutoComment)}
                className={`flex items-center justify-center gap-2 p-3 rounded-lg border text-sm font-medium transition-colors ${webhookAutoComment ? "border-purple-300 bg-purple-50 text-purple-700" : "border-slate-200 text-slate-500"}`}>
                <FileCode className="h-4 w-4" />
                {webhookAutoComment ? "Auto-Comment On" : "Auto-Comment Off"}
              </button>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Webhook Secret (optional)</label>
              <input type="password" value={webhookSecret} onChange={(e) => setWebhookSecret(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="your-webhook-secret" />
            </div>
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
              <p className="text-xs font-medium text-slate-700 mb-2">GitHub Webhook Setup</p>
              <p className="text-xs text-slate-500 mb-2">Point your GitHub webhook to this URL:</p>
              <code className="block bg-slate-900 text-green-400 text-xs p-2 rounded font-mono">{`POST ${window.location.origin}/api/review/webhook/github`}</code>
              <p className="text-xs text-slate-500 mt-2">Events: <strong>Pull requests</strong> (opened, synchronize, reopened)</p>
              <p className="text-xs text-slate-500 mt-1">Content type: <strong>application/json</strong></p>
            </div>
          </div>
        )}

        <div className="mt-5 flex items-center gap-3">
          {mode === "webhook" ? (
            <button
              onClick={saveWebhookConfig}
              disabled={webhookLoading}
              className="flex items-center gap-2 bg-green-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-green-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {webhookLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Settings className="h-4 w-4" />}
              Save Webhook Config
            </button>
          ) : (
          <>
          <button
            onClick={runReview}
            disabled={loading}
            className="flex items-center gap-2 bg-indigo-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                {mode === "repo" ? "Scanning Repo..." : mode === "autofix" ? "Running Auto-Fix..." : "Analysing..."}
              </>
            ) : (
              <>
                {mode === "repo" ? <FolderSearch className="h-4 w-4" /> : mode === "autofix" ? <RotateCcw className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
                {mode === "repo" ? "Scan Full Repository" : mode === "autofix" ? "Run Auto-Fix Loop" : "Run ZECT Review"}
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
          </>
          )}
          {error && <p className="text-sm text-red-600">{error}</p>}
          {inlineSuccess && <p className="text-sm text-green-600">{inlineSuccess}</p>}
          {webhookSaved && <p className="text-sm text-green-600">Webhook configuration saved!</p>}
        </div>
      </div>

      {/* Auto-Fix Results Panel */}
      {autoFixResult && !loading && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
          <h3 className="text-sm font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <RotateCcw className="h-4 w-4 text-amber-600" />
            Auto-Fix Loop Results
          </h3>
          <div className="grid grid-cols-4 gap-4 mb-4">
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-slate-900">{autoFixResult.total_iterations}</p>
              <p className="text-xs text-slate-500">Iterations</p>
            </div>
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-slate-900">{autoFixResult.final_quality_score}</p>
              <p className="text-xs text-slate-500">Final Score</p>
            </div>
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-slate-900">{autoFixResult.total_fixes_posted}</p>
              <p className="text-xs text-slate-500">Fixes Posted</p>
            </div>
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-slate-900">{autoFixResult.total_tokens_used?.toLocaleString()}</p>
              <p className="text-xs text-slate-500">Tokens Used</p>
            </div>
          </div>
          <div className="space-y-2">
            {autoFixResult.iterations?.map((iter: any, i: number) => (
              <div key={i} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                <span className="text-xs font-mono text-slate-400 w-6">#{iter.iteration}</span>
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${iter.action === "clean" ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}`}>
                  {iter.action === "clean" ? "Clean" : "Review & Fix"}
                </span>
                <span className="text-sm text-slate-700 flex-1">{iter.message || `${iter.total_issues} issues, score ${iter.quality_score}/100`}</span>
                {iter.fixes_posted > 0 && <span className="text-xs text-indigo-600">{iter.fixes_posted} fixes posted</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Rules Engine Results Panel */}
      {rulesResult && !loading && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
          <h3 className="text-sm font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <Shield className="h-4 w-4 text-indigo-600" />
            Rules Engine Evaluation
          </h3>
          {rulesResult.is_blocked && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 flex items-start gap-2">
              <XCircle className="h-4 w-4 text-red-600 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-medium text-red-800">PR Blocked by Rules</p>
                <p className="text-xs text-red-600">{rulesResult.blocked_by_rules?.join(", ")}</p>
              </div>
            </div>
          )}
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-slate-900">{rulesResult.total_rule_matches}</p>
              <p className="text-xs text-slate-500">Rule Matches</p>
            </div>
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-slate-900">{rulesResult.merged_total_issues}</p>
              <p className="text-xs text-slate-500">Total Issues (AI + Rules)</p>
            </div>
            <div className={`rounded-lg p-3 text-center ${rulesResult.is_blocked ? "bg-red-50" : "bg-green-50"}`}>
              <p className={`text-2xl font-bold ${rulesResult.is_blocked ? "text-red-700" : "text-green-700"}`}>
                {rulesResult.is_blocked ? "BLOCKED" : "PASS"}
              </p>
              <p className="text-xs text-slate-500">Gate Status</p>
            </div>
          </div>
          {rulesResult.rule_findings?.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-slate-600 uppercase tracking-wide">Rule Findings</p>
              {rulesResult.rule_findings.map((rf: any, i: number) => (
                <div key={i} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                  <SeverityBadge severity={rf.severity} />
                  <span className="text-sm text-slate-700 flex-1">{rf.title}</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${rf.rule_action === "block" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}`}>
                    {rf.rule_action}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Repo Scan Info Banner */}
      {repoScanResult && !loading && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4 mb-6 flex items-center gap-4">
          <FolderSearch className="h-5 w-5 text-indigo-600 shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-indigo-900">Full Repository Scan Complete</p>
            <p className="text-xs text-indigo-700">
              {repoScanResult.files_scanned} files scanned &middot; {repoScanResult.total_lines?.toLocaleString()} lines &middot; Branch: {repoScanResult.branch}
            </p>
          </div>
        </div>
      )}

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
                Copy this structured prompt and send it to any AI agent to automatically fix all issues found in this review.
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
