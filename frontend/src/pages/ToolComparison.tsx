/**
 * ZECT architecture flows (Labs). Capability diagrams only — no third-party product names.
 */
import { useEffect, useId, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Workflow, ArrowRight, Map } from "lucide-react";
import { explainIdFromMermaidLabel } from "@/lib/archExplain";

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
    Labs[Skills Knowledge Playbooks Schedules Memory]
    Sec[Security incidents]
    Int[Jira Slack email drafts]
  end
  U --> UI
  U --> Voice
  Voice --> Run
  UI --> Run
  Run --> Gates
  Gates --> WS
  Gates --> Labs
  Gates --> Sec
  Gates --> Int`;

const MENTRIX_FLOW = `flowchart LR
  A[1. Open Mentrix] --> B[2. Set goal + mode]
  B --> C[3. Gates check permissions]
  C --> D[4. Adapters run tools]
  D --> E[5. Timeline + artifacts]
  E --> F[6. Approve outbound / PR]
  F --> G[7. Audit recorded]`;

const LABS_FLOW = `flowchart LR
  K[Knowledge Base] --> Ctx[Mentrix context]
  M[Memory] --> Ctx
  S[Skills] --> Proj[New project scaffold]
  P[Playbooks] --> Run[Mentrix steps]
  Sch[Scheduled Tasks] --> Run
  Ctx --> Run`;

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
    title: "10x Labs productivity loop",
    steps: [
      { label: "Store conventions in Knowledge Base", to: "/knowledge-base" },
      { label: "Register a Skill or Playbook", to: "/skills-engine" },
      { label: "Schedule Mentrix or playbook runs", to: "/scheduled-tasks" },
      { label: "Recall Memory + Permissions gates", to: "/memory" },
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
];

const ARCH_EXPLAIN = [
  {
    id: "client",
    title: "ZECT client",
    body: "React UI + Mentrix Voice. ZECT owns UX, permissions, and audit. OpenHands is coding runtime only — not a second agent.",
    to: "/mentrix-home",
  },
  {
    id: "lattice",
    title: "Lattice = Graphify ingest",
    body: "Graphify is Lattice ingest (symbols, imports, calls). Header STALE means re-index. Not a second knowledge base.",
    to: "/lattice",
  },
  {
    id: "control",
    title: "Ask → Plan → Agent",
    body: "WorkItems and Mentrix runs follow Ask, then Plan, then Agent. Gates, audit, and emergency stop sit on the control plane.",
    to: "/work-items",
  },
  {
    id: "docs",
    title: "Canonical architecture",
    body: "Click a card for a short explain (CSS + mermaid — no 3D engine). Full write-up lives in ZECT_CANONICAL_ARCHITECTURE.md.",
    to: "/docs",
  },
];

function MermaidDiagram({
  body,
  title,
  onNodeExplain,
}: {
  body: string;
  title: string;
  onNodeExplain?: (id: string) => void;
}) {
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

  useEffect(() => {
    const el = ref.current;
    if (!el || !onNodeExplain) return;
    const onClick = (ev: MouseEvent) => {
      const node = (ev.target as Element | null)?.closest?.(".node");
      if (!node || !el.contains(node)) return;
      const mapped = explainIdFromMermaidLabel(node.textContent || "");
      if (mapped) onNodeExplain(mapped);
    };
    el.addEventListener("click", onClick);
    return () => el.removeEventListener("click", onClick);
  }, [body, onNodeExplain]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
      <div className="border-b border-slate-100 px-4 py-2 text-sm font-semibold text-slate-800">{title}</div>
      <div
        ref={ref}
        className="overflow-x-auto p-4 bg-slate-50 min-h-[160px] cursor-pointer"
        data-testid="architecture-mermaid"
      />
    </div>
  );
}

export default function ToolComparison() {
  const [explainId, setExplainId] = useState<string | null>(null);
  const selected = ARCH_EXPLAIN.find((c) => c.id === explainId) || null;

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6" data-testid="architecture-guide">
      <header className="space-y-2">
        <div className="flex items-center gap-2 text-indigo-700">
          <Map className="h-6 w-6" />
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Architecture</h1>
        </div>
        <p className="max-w-3xl text-sm text-slate-600">
          How ZECT Mentrix fits together — Client → control plane → Workspace and Labs. Day-to-day
          work happens in Companion, Agent Workspace, and Developer Workspace.
        </p>
      </header>

      <section className="rounded-xl border border-indigo-100 bg-indigo-50/60 p-4 text-sm text-slate-700">
        <p className="font-semibold text-indigo-900 mb-1 inline-flex items-center gap-2">
          <Workflow className="h-4 w-4" /> How to use this page
        </p>
        <ol className="list-decimal pl-5 space-y-1">
          <li>Read the system diagram to see Client → Mentrix → adapters.</li>
          <li>Use the Labs loop diagram for Knowledge → Skills → Playbooks → Schedules.</li>
          <li>Pick a path below and open the real ZECT screen.</li>
        </ol>
      </section>

      <MermaidDiagram
        title="System architecture — where your clicks go"
        body={SYSTEM_FLOW}
        onNodeExplain={setExplainId}
      />

      <section className="rounded-xl border border-slate-200 bg-white p-4 text-sm" data-testid="architecture-legend">
        <h2 className="text-sm font-semibold text-slate-900 mb-2">Implemented vs blocked</h2>
        <ul className="space-y-1 text-slate-700">
          <li>
            <span className="font-medium text-emerald-800">Implemented:</span> Present generate (Presenton must be READY), clone TTS (Voicebox), Lattice ingest / Graphify.
          </li>
          <li>
            <span className="font-medium text-amber-800">Blocked:</span> Presenton down = BLOCKED_EXTERNAL. Voicebox offline = clone narrate disabled. Lattice STALE = re-index.
          </li>
        </ul>
      </section>

      <section className="space-y-3" data-testid="architecture-explain">
        <h2 className="text-lg font-semibold text-slate-900">Click a layer to explain</h2>
        <p className="text-sm text-slate-600">
          Short CSS animation only — not a 3D engine. Companion “architecture” opens this page and{" "}
          <Link to="/lattice" className="text-indigo-700 underline">
            Lattice
          </Link>{" "}
          (Graphify ingest).
        </p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {ARCH_EXPLAIN.map((card) => (
            <button
              key={card.id}
              type="button"
              data-testid={`architecture-card-${card.id}`}
              onClick={() => setExplainId(card.id === explainId ? null : card.id)}
              className={`rounded-xl border p-3 text-left transition-all duration-300 ${
                explainId === card.id
                  ? "border-indigo-400 bg-indigo-50 scale-[1.02] shadow-md"
                  : "border-slate-200 bg-white hover:border-indigo-200"
              }`}
            >
              <p className="text-sm font-semibold text-slate-900">{card.title}</p>
            </button>
          ))}
        </div>
        <div
          className={`overflow-hidden transition-all duration-300 ${
            selected ? "max-h-40 opacity-100" : "max-h-0 opacity-0"
          }`}
          data-testid="architecture-explain-panel"
        >
          {selected ? (
            <div className="rounded-xl border border-indigo-200 bg-white p-4 text-sm text-slate-700">
              <p>{selected.body}</p>
              <Link to={selected.to} className="mt-2 inline-flex items-center gap-1 text-indigo-700">
                Open {selected.title} <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          ) : null}
        </div>
      </section>

      <MermaidDiagram title="Mentrix run — step order" body={MENTRIX_FLOW} onNodeExplain={setExplainId} />
      <MermaidDiagram title="Labs productivity loop" body={LABS_FLOW} onNodeExplain={setExplainId} />
      <MermaidDiagram title="Security incident response" body={IR_FLOW} onNodeExplain={setExplainId} />

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
  );
}
