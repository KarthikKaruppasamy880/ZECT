import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import {
  Bot,
  ClipboardList,
  Hammer,
  MessageSquare,
  Rocket,
  Shield,
  Sparkles,
} from "lucide-react";
import { isAgentModeEnabled } from "@/lib/featureFlags";

type Step = {
  to: string;
  label: string;
  short: string;
  icon: typeof MessageSquare;
  primary?: boolean;
  advanced?: boolean;
};

const BASE_STEPS: Step[] = [
  { to: "/ask", label: "Ask", short: "Ask", icon: MessageSquare },
  { to: "/plan", label: "Plan", short: "Plan", icon: ClipboardList },
  { to: "/build", label: "Build", short: "Build", icon: Hammer },
  { to: "/review", label: "Snippet Review", short: "Review", icon: Shield },
  { to: "/deploy", label: "Deploy", short: "Deploy", icon: Rocket },
  { to: "/mentrix", label: "Mentrix Delivery", short: "Mentrix", icon: Sparkles, primary: true },
];

const AGENT_MODE_STEP: Step = {
  to: "/agent-mode",
  label: "Agent Mode",
  short: "Agent",
  icon: Bot,
  advanced: true,
};

/**
 * Shared chrome for Agent Run phase pages. Keeps existing URLs; Mentrix Delivery
 * is the primary spine. Agent Mode appears only when the power-user flag is on.
 */
export default function AgentWorkspaceShell() {
  const location = useLocation();
  const [agentModeOn, setAgentModeOn] = useState(() => isAgentModeEnabled());

  useEffect(() => {
    const sync = () => setAgentModeOn(isAgentModeEnabled());
    window.addEventListener("zect-feature-flags", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("zect-feature-flags", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  const steps = agentModeOn ? [...BASE_STEPS, AGENT_MODE_STEP] : BASE_STEPS;

  return (
    <div className="flex flex-col gap-4 lg:flex-row" data-testid="agent-workspace">
      <aside
        className="lg:w-44 shrink-0 rounded-lg border border-slate-200 bg-white p-3 shadow-sm"
        data-testid="agent-workspace-rail"
      >
        <div className="mb-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Agent Workspace
          </p>
          <p className="mt-1 text-[11px] leading-snug text-slate-500">
            Mentrix Delivery is the primary run path. Tools stay available as steps.
          </p>
        </div>
        <nav className="flex flex-row flex-wrap gap-1.5 lg:flex-col lg:gap-1">
          {steps.map((step) => {
            const Icon = step.icon;
            return (
              <NavLink
                key={step.to}
                to={step.to}
                data-testid={`agent-workspace-step-${step.short.toLowerCase()}`}
                className={({ isActive }) => {
                  const active = isActive || location.pathname === step.to;
                  if (step.primary) {
                    return [
                      "flex items-center gap-2 rounded-md px-2.5 py-2 text-sm transition-colors",
                      active
                        ? "bg-teal-700 text-white font-semibold shadow-sm"
                        : "bg-teal-50 text-teal-900 font-medium hover:bg-teal-100 border border-teal-200",
                    ].join(" ");
                  }
                  if (step.advanced) {
                    return [
                      "flex items-center gap-2 rounded-md px-2.5 py-2 text-sm transition-colors border border-dashed",
                      active
                        ? "border-amber-400 bg-amber-50 text-amber-950 font-medium"
                        : "border-slate-300 text-slate-600 hover:bg-slate-50",
                    ].join(" ");
                  }
                  return [
                    "flex items-center gap-2 rounded-md px-2.5 py-2 text-sm transition-colors",
                    active
                      ? "bg-slate-900 text-white font-medium"
                      : "text-slate-700 hover:bg-slate-100",
                  ].join(" ");
                }}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span className="truncate">{step.label}</span>
                {step.advanced && (
                  <span className="ml-auto hidden text-[10px] uppercase tracking-wide opacity-70 lg:inline">
                    Adv
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>
        {!agentModeOn && (
          <p className="mt-3 hidden text-[11px] text-slate-500 lg:block">
            Need the legacy orchestrator? Enable{" "}
            <Link to="/settings" className="text-teal-700 underline">
              Agent Mode
            </Link>{" "}
            under Advanced in Settings.
          </p>
        )}
      </aside>
      <div className="min-w-0 flex-1">
        <Outlet />
      </div>
    </div>
  );
}
