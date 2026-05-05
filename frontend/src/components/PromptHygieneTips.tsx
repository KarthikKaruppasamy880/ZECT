import { useState } from "react";
import { Lightbulb, X, ChevronDown, ChevronUp } from "lucide-react";

interface Tip {
  id: string;
  title: string;
  description: string;
  example?: string;
}

const tipsByMode: Record<string, Tip[]> = {
  ask: [
    { id: "ask-1", title: "Be specific", description: "Include tech stack, constraints, and expected outcome.", example: "How should I structure auth in a React + FastAPI app using JWT with refresh tokens?" },
    { id: "ask-2", title: "Provide context", description: "Attach relevant files or paste code snippets for accurate answers.", example: "Here's my current auth.ts — how can I add rate limiting?" },
    { id: "ask-3", title: "One question at a time", description: "Split complex questions into focused parts for better answers." },
    { id: "ask-4", title: "State the goal", description: "Describe what you're trying to achieve, not just the problem." },
  ],
  plan: [
    { id: "plan-1", title: "Define scope clearly", description: "Include goals, team size, timeline, and tech stack preferences.", example: "Plan a microservices migration for our monolith (3 devs, 8 weeks, Node.js to Go)" },
    { id: "plan-2", title: "List constraints", description: "Budget, deadlines, existing infrastructure, and team skills.", example: "Budget: $5K/month cloud, must support 10K concurrent users" },
    { id: "plan-3", title: "Attach repo analysis", description: "Use the Repo Analysis page first, then attach the output for context-aware planning." },
    { id: "plan-4", title: "Specify deliverables", description: "What outputs do you expect? Architecture diagram, API spec, timeline?" },
  ],
  build: [
    { id: "build-1", title: "Describe the feature", description: "Be specific about inputs, outputs, error handling, and edge cases.", example: "Create a REST endpoint POST /api/claims that validates JSON body, checks fraud rules, and returns claim ID" },
    { id: "build-2", title: "Specify tech stack", description: "Include language, framework, and library versions.", example: "TypeScript, React 18, TanStack Query v5, Tailwind CSS" },
    { id: "build-3", title: "Set the file path", description: "Tell the AI where the code should live in your project structure.", example: "src/api/routes/claims.ts" },
    { id: "build-4", title: "Use templates", description: "Start with a Quick Template and customize — faster than writing from scratch." },
  ],
  review: [
    { id: "review-1", title: "Paste full files", description: "Include complete files rather than fragments for accurate security analysis." },
    { id: "review-2", title: "Specify review focus", description: "Tell the reviewer what to focus on: security, performance, patterns, or all.", example: "Focus on SQL injection, XSS, and authentication bypass" },
    { id: "review-3", title: "Include test coverage", description: "Attach test files so the reviewer can assess coverage gaps." },
  ],
};

interface PromptHygieneTipsProps {
  mode: "ask" | "plan" | "build" | "review";
  className?: string;
}

export default function PromptHygieneTips({ mode, className = "" }: PromptHygieneTipsProps) {
  const [dismissed, setDismissed] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const tips = tipsByMode[mode] || [];
  if (tips.length === 0 || dismissed) return null;

  return (
    <div className={`bg-amber-50 border border-amber-200 rounded-xl ${className}`}>
      <div className="flex items-center justify-between px-4 py-2.5">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 text-sm font-medium text-amber-800 hover:text-amber-900 transition"
        >
          <Lightbulb className="h-4 w-4 text-amber-500" />
          Prompt Tips
          {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </button>
        <button
          onClick={() => setDismissed(true)}
          className="text-amber-400 hover:text-amber-600 transition"
          title="Dismiss tips"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      {expanded && (
        <div className="px-4 pb-3 space-y-2">
          {tips.map((tip) => (
            <div key={tip.id} className="text-xs">
              <span className="font-semibold text-amber-800">{tip.title}:</span>{" "}
              <span className="text-amber-700">{tip.description}</span>
              {tip.example && (
                <p className="mt-0.5 text-amber-600 italic pl-3 border-l-2 border-amber-300">
                  {tip.example}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
