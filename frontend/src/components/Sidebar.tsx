import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  FolderKanban,
  GitBranch,
  BarChart3,
  FileText,
  Settings,
  MessageSquare,
  ClipboardList,
  Hammer,
  Search,
  Rocket,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/projects", label: "Projects", icon: FolderKanban },
  { href: "/orchestration", label: "Orchestration", icon: GitBranch },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/docs", label: "Docs Center", icon: FileText },
  { href: "/settings", label: "Settings", icon: Settings },
];

const stageItems = [
  { href: "/stages/ask", label: "Ask Mode", icon: MessageSquare },
  { href: "/stages/plan", label: "Plan Mode", icon: ClipboardList },
  { href: "/stages/build", label: "Build Phase", icon: Hammer },
  { href: "/stages/review", label: "Review", icon: Search },
  { href: "/stages/deploy", label: "Deployment", icon: Rocket },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-56 bg-slate-900 text-slate-300 flex flex-col">
      <div className="px-4 py-5 border-b border-slate-700">
        <p className="text-xs uppercase tracking-wider text-slate-500">Zinnia</p>
        <h1 className="text-base font-bold text-white leading-tight">
          Engineering Delivery
          <br />
          Control Tower
        </h1>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <p className="px-2 mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Navigation
        </p>
        <ul className="space-y-0.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = location.pathname === item.href;
            return (
              <li key={item.href}>
                <Link
                  to={item.href}
                  className={`flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors ${
                    active
                      ? "bg-slate-800 text-white font-medium"
                      : "hover:bg-slate-800/60 hover:text-white"
                  }`}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>

        <p className="px-2 mt-6 mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Workflow Stages
        </p>
        <ul className="space-y-0.5">
          {stageItems.map((item) => {
            const Icon = item.icon;
            const active = location.pathname === item.href;
            return (
              <li key={item.href}>
                <Link
                  to={item.href}
                  className={`flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors ${
                    active
                      ? "bg-slate-800 text-white font-medium"
                      : "hover:bg-slate-800/60 hover:text-white"
                  }`}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="border-t border-slate-700 px-4 py-3">
        <p className="text-xs text-slate-500">Zinnia Eng</p>
        <p className="text-xs text-slate-600">Internal Platform</p>
      </div>
    </aside>
  );
}
