/**
 * Architecture flows + capability comparison (planning surface).
 * Product names appear only here — not in core Mentrix APIs.
 */
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  GitCompareArrows,
  Check,
  Minus,
  X,
  Workflow,
  ArrowRight,
  Map,
} from "lucide-react";

type Cell = "yes" | "partial" | "no" | string;
type Tab = "architecture" | "comparison";

type Row = {
  capability: string;
  category: string;
  cursor: Cell;
  devin: Cell;
  claudeCode: Cell;
  minion: Cell;
  zect: Cell;
};

const ROWS: Row[] = [
  { category: "Core IDE", capability: "Inline AI edit in editor", cursor: "yes", devin: "partial", claudeCode: "partial", minion: "partial", zect: "yes" },
  { category: "Core IDE", capability: "Multi-file agent workspace", cursor: "yes", devin: "yes", claudeCode: "yes", minion: "partial", zect: "yes" },
  { category: "Core IDE", capability: "PR review + approve-before-post", cursor: "partial", devin: "partial", claudeCode: "partial", minion: "no", zect: "yes" },
  { category: "Runtime", capability: "Isolated coding-engine worktrees", cursor: "partial", devin: "yes", claudeCode: "partial", minion: "no", zect: "yes" },
  { category: "Runtime", capability: "Browser automation with verify", cursor: "partial", devin: "yes", claudeCode: "partial", minion: "partial", zect: "yes" },
  { category: "Runtime", capability: "Desktop / Computer Mode last-resort", cursor: "no", devin: "partial", claudeCode: "no", minion: "yes", zect: "yes" },
  { category: "Voice", capability: "Realtime voice HUD + clone", cursor: "no", devin: "no", claudeCode: "no", minion: "partial", zect: "yes" },
  { category: "Ops", capability: "Jira / Slack draft-before-send", cursor: "no", devin: "partial", claudeCode: "no", minion: "partial", zect: "yes" },
  { category: "Ops", capability: "Security Detection Provider + IR draft", cursor: "no", devin: "no", claudeCode: "no", minion: "no", zect: "yes" },
  { category: "Memory", capability: "Typed memory + retention/export", cursor: "partial", devin: "partial", claudeCode: "partial", minion: "partial", zect: "yes" },
  { category: "Memory", capability: "Skills with approval / capability gates", cursor: "partial", devin: "partial", claudeCode: "yes", minion: "partial", zect: "yes" },
  { category: "Governance", capability: "Capability grants + emergency stop", cursor: "partial", devin: "partial", claudeCode: "partial", minion: "no", zect: "yes" },
  { category: "Governance", capability: "Secret refs + audit hash chain", cursor: "partial", devin: "no", claudeCode: "partial", minion: "no", zect: "yes" },
  { category: "Release", capability: "Self-host desktop + support bundle", cursor: "no", devin: "no", claudeCode: "partial", minion: "partial", zect: "yes" },
  { category: "Release", capability: "Org branding (adapters, no vendor UI)", cursor: "no", devin: "no", claudeCode: "no", minion: "no", zect: "yes" },
];

const TOOLS = [
  { key: "cursor" as const, label: "Cursor" },
  { key: "devin" as const, label: "Devin" },
  { key: "claudeCode" as const, label: "Claude Code" },
  { key: "minion" as const, label: "Minion Bot" },
  { key: "zect" as const, label: "ZECT" },
];

const SYSTEM_FLOW = `flowchart TB
  subgraph You["You"]
    U[User goal]
  end
  subgraph Client["ZECT client"]
    UI[React UI]
    Voice[Mentrix Voice]
  end
  subgraph Core["Mentrix control plane"]
    Run[Agent run Ask/Plan/Build/Review/Deploy]
    Gates[Permissions + audit + emergency stop]
  end
  subgraph Work["Work surfaces"]
    WS[Workspace / coding engine]
    Mem[Memory / skills / schedules]
    Sec[Security incidents]
    Int[Jira Slack email drafts]
  end
  U --> UI
  U --> Voice
  Voice --> Run
  UI --> Run
  Run --> Gates
  Gates --> WS
  Gates --> Mem
  Gates --> Sec
  Gates --> Int`;

const MENTRIX_FLOW = `flowchart LR
  A[1. Open Mentrix] --> B[2. Set goal + mode]
  B --> C[3. Gates check permissions]
  C --> D[4. Adapters run tools]
  D --> E[5. Timeline + artifacts]
  E --> F[6. Approve outbound / PR]
  F --> G[7. Audit recorded]`;

const IR_FLOW = `flowchart LR
  S[Scan / ingest] --> F[Findings]
  F --> D[Draft incident]
  D --> A[You approve]
  A --> J[Jira + Slack]
  D -.-> X[Containment off by default]`;

const USER_PATHS = [
  {
    title: "Ship code with Mentrix",
    steps: [
      { label: "Open Mentrix Companion or Agent Workspace", to: "/mentrix-home" },
      { label: "Choose Ask → Plan → Build → Review → Deploy", to: "/mentrix" },
      { label: "Inspect diffs in Developer Workspace", to: "/workspace" },
      { label: "Approve PR / outbound actions before send", to: "/review" },
    ],
  },
  {
    title: "Personal ops (Slack / email / Jira)",
    steps: [
      { label: "Ask Mentrix to draft a reply or ticket", to: "/mentrix" },
      { label: "Review draft (never auto-send)", to: "/integrations" },
      { label: "Approve → provider API send", to: "/integrations" },
    ],
  },
  {
    title: "Security incident response",
    steps: [
      { label: "Open Security Incidents", to: "/security-incidents" },
      { label: "Run scan or wait for signed ingest", to: "/security-incidents" },
      { label: "Draft incident → approve → Jira/Slack", to: "/security-incidents" },
    ],
  },
  {
    title: "Memory, skills, automation",
    steps: [
      { label: "Store typed knowledge in Memory", to: "/memory" },
      { label: "Register gated skills", to: "/skills-engine" },
      { label: "Schedule or watch conditions", to: "/scheduled-tasks" },
    ],
  },
];

function MermaidDiagram({ body, title }: { body: string; title: string }) {
  const id = useId().replace(/:/g, "");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: "neutral",
          securityLevel: "loose",
          flowchart: { curve: "basis", htmlLabels: true },
        });
        const { svg } = await mermaid.render(`arch-${id}-${Date.now()}`, body);
        if (!cancelled && ref.current) ref.current.innerHTML = svg;
      } catch (e) {
        if (!cancelled && ref.current) {
          ref.current.innerHTML = `<pre class="text-xs text-red-700 whitespace-pre-wrap p-3">${String(e)}</pre>`;
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [body, id]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
      <div className="border-b border-slate-100 px-4 py-2 text-sm font-semibold text-slate-800">{title}</div>
      <div ref={ref} className="overflow-x-auto p-4 bg-slate-50 min-h-[160px]" />
    </div>
  );
}

function CellView({ value }: { value: Cell }) {
  if (value === "yes") {
    return (
      <span className="inline-flex items-center gap-1 font-medium text-emerald-700">
        <Check className="h-4 w-4" /> Yes
      </span>
    );
  }
  if (value === "partial") {
    return (
      <span className="inline-flex items-center gap-1 font-medium text-amber-700">
        <Minus className="h-4 w-4" /> Partial
      </span>
    );
  }
  if (value === "no") {
    return (
      <span className="inline-flex items-center gap-1 font-medium text-slate-500">
        <X className="h-4 w-4" /> No
      </span>
    );
  }
  return <span className="text-sm text-slate-700">{value}</span>;
}

export default function ToolComparison() {
  const [tab, setTab] = useState<Tab>("architecture");
  const [category, setCategory] = useState<string>("all");
  const cats = useMemo(() => ["all", ...Array.from(new Set(ROWS.map((r) => r.category)))], []);
  const rows = useMemo(
    () => (category === "all" ? ROWS : ROWS.filter((r) => r.category === category)),
    [category],
  );
  const scores = useMemo(() => {
    const score = (k: keyof Row) =>
      ROWS.reduce((acc, r) => {
        const v = r[k];
        if (v === "yes") return acc + 2;
        if (v === "partial") return acc + 1;
        return acc;
      }, 0);
    return TOOLS.map((t) => ({ ...t, score: score(t.key) })).sort((a, b) => b.score - a.score);
  }, []);

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6" data-testid="architecture-guide">
      <header className="space-y-2">
        <div className="flex items-center gap-2 text-indigo-700">
          <Map className="h-6 w-6" />
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            Architecture & tool map
          </h1>
        </div>
        <p className="max-w-3xl text-sm text-slate-600">
          This Labs page explains <strong className="font-semibold text-slate-800">how ZECT fits together</strong>,{" "}
          <strong className="font-semibold text-slate-800">how you walk the flows</strong>, and{" "}
          <strong className="font-semibold text-slate-800">why the comparison exists</strong> (planning only —
          Mentrix work happens on Companion / Workspace, not here).
        </p>
      </header>

      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-3">
        <button
          type="button"
          onClick={() => setTab("architecture")}
          className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium ${
            tab === "architecture"
              ? "bg-indigo-600 text-white"
              : "bg-white text-slate-700 border border-slate-200 hover:bg-slate-50"
          }`}
        >
          <Workflow className="h-4 w-4" /> Architecture & how to follow
        </button>
        <button
          type="button"
          onClick={() => setTab("comparison")}
          className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium ${
            tab === "comparison"
              ? "bg-indigo-600 text-white"
              : "bg-white text-slate-700 border border-slate-200 hover:bg-slate-50"
          }`}
        >
          <GitCompareArrows className="h-4 w-4" /> Comparison matrix
        </button>
      </div>

      {tab === "architecture" && (
        <div className="space-y-6">
          <section className="rounded-xl border border-indigo-100 bg-indigo-50/60 p-4 text-sm text-slate-700">
            <p className="font-semibold text-indigo-900 mb-1">How to use this page</p>
            <ol className="list-decimal pl-5 space-y-1">
              <li>Read the system diagram to see Client → Mentrix → adapters.</li>
              <li>Pick a path below and click each step — it opens the real ZECT screen.</li>
              <li>Use the Comparison tab only when you need a capability gap check vs other products.</li>
            </ol>
          </section>

          <MermaidDiagram title="System architecture — where your clicks go" body={SYSTEM_FLOW} />
          <MermaidDiagram title="Mentrix run — step order" body={MENTRIX_FLOW} />
          <MermaidDiagram title="Security incident response" body={IR_FLOW} />

          <section className="space-y-4">
            <h2 className="text-lg font-semibold text-slate-900">Follow these paths in the product</h2>
            <div className="grid gap-4 md:grid-cols-2">
              {USER_PATHS.map((path) => (
                <div key={path.title} className="rounded-xl border border-slate-200 bg-white p-4">
                  <h3 className="text-sm font-semibold text-slate-900 mb-3">{path.title}</h3>
                  <ol className="space-y-2">
                    {path.steps.map((step, i) => (
                      <li key={step.label}>
                        <Link
                          to={step.to}
                          className="group flex items-start gap-2 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-sm text-slate-800 hover:border-indigo-200 hover:bg-indigo-50"
                        >
                          <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-[11px] font-bold text-white">
                            {i + 1}
                          </span>
                          <span className="flex-1">{step.label}</span>
                          <ArrowRight className="h-4 w-4 shrink-0 text-slate-400 group-hover:text-indigo-600" />
                        </Link>
                      </li>
                    ))}
                  </ol>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}

      {tab === "comparison" && (
        <div className="space-y-5">
          <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
            <p className="font-semibold mb-1">Why this matrix is in ZECT</p>
            <p>
              It is a <strong>planning / coverage checklist</strong> for stakeholders — not a Mentrix
              runtime tool. It answers “what does ZECT cover that Cursor / Devin / Claude Code / Minion
              do not?” Scores are directional (Yes=2, Partial=1). Day-to-day work stays in Mentrix,
              Workspace, and Security Incidents.
            </p>
          </section>

          <div className="grid gap-3 sm:grid-cols-5">
            {scores.map((t) => (
              <div
                key={t.key}
                className={`rounded-xl border px-3 py-3 ${
                  t.key === "zect"
                    ? "border-indigo-300 bg-indigo-50"
                    : "border-slate-200 bg-white"
                }`}
              >
                <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{t.label}</div>
                <div className="mt-1 text-2xl font-semibold text-slate-900">{t.score}</div>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            {cats.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setCategory(c)}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
                  category === c
                    ? "bg-indigo-600 text-white"
                    : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                }`}
              >
                {c}
              </button>
            ))}
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-100 text-slate-700">
                <tr>
                  <th className="px-3 py-3 font-semibold">Capability</th>
                  {TOOLS.map((t) => (
                    <th key={t.key} className="px-3 py-3 font-semibold">
                      {t.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.capability} className="border-t border-slate-100 hover:bg-slate-50/80">
                    <td className="px-3 py-3 align-top">
                      <div className="font-medium text-slate-900">{r.capability}</div>
                      <div className="text-xs text-slate-500">{r.category}</div>
                    </td>
                    {TOOLS.map((t) => (
                      <td key={t.key} className="px-3 py-3 align-top whitespace-nowrap">
                        <CellView value={r[t.key]} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
