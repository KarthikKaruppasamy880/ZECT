import { useEffect } from "react";
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
  Microscope,
  Sparkles,
  BookOpen,
  ShieldCheck,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/projects", label: "Projects", icon: FolderKanban },
  { href: "/orchestration", label: "Orchestration", icon: GitBranch },
  { href: "/repo-analysis", label: "Repo Analysis", icon: Microscope },
  { href: "/blueprint", label: "Blueprint", icon: Sparkles },
  { href: "/doc-generator", label: "Doc Generator", icon: BookOpen },
  { href: "/code-review", label: "Code Review", icon: ShieldCheck },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/docs", label: "Docs Center", icon: FileText },
  { href: "/settings", label: "Settings", icon: Settings },
];

const stageItems = [
  { href: "/ask", label: "Ask Mode", icon: MessageSquare },
  { href: "/plan", label: "Plan Mode", icon: ClipboardList },
  { href: "/stages/build", label: "Build Phase", icon: Hammer },
  { href: "/stages/review", label: "Review", icon: Search },
  { href: "/stages/deploy", label: "Deployment", icon: Rocket },
];

interface SidebarProps {
  onLogout?: () => void;
  collapsed: boolean;
  onToggle: () => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
}

export default function Sidebar({
  onLogout,
  collapsed,
  onToggle,
  mobileOpen,
  onMobileClose,
}: SidebarProps) {
  const location = useLocation();

  // Close mobile menu on route change
  useEffect(() => {
    onMobileClose();
  }, [location.pathname]);

  const sidebarContent = (
    <>
      {/* Header */}
      <div className={`border-b border-slate-700 ${collapsed ? "px-2 py-4" : "px-4 py-5"}`}>
        {collapsed ? (
          <div className="flex flex-col items-center">
            <span className="text-lg font-bold text-white">Z</span>
          </div>
        ) : (
          <>
            <p className="text-xs uppercase tracking-wider text-slate-500">Zinnia</p>
            <h1 className="text-base font-bold text-white leading-tight">
              Engineering Delivery
              <br />
              Control Tower
            </h1>
          </>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-2 py-4">
        {!collapsed && (
          <p className="px-2 mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Navigation
          </p>
        )}
        <ul className="space-y-0.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = location.pathname === item.href;
            return (
              <li key={item.href}>
                <Link
                  to={item.href}
                  title={collapsed ? item.label : undefined}
                  className={`flex items-center ${collapsed ? "justify-center" : ""} gap-2.5 rounded-md ${collapsed ? "px-2 py-2.5" : "px-2.5 py-2"} text-sm transition-colors ${
                    active
                      ? "bg-slate-800 text-white font-medium"
                      : "hover:bg-slate-800/60 hover:text-white"
                  }`}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {!collapsed && <span>{item.label}</span>}
                </Link>
              </li>
            );
          })}
        </ul>

        {!collapsed ? (
          <p className="px-2 mt-6 mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Workflow Stages
          </p>
        ) : (
          <div className="my-4 border-t border-slate-700" />
        )}
        <ul className="space-y-0.5">
          {stageItems.map((item) => {
            const Icon = item.icon;
            const active = location.pathname === item.href;
            return (
              <li key={item.href}>
                <Link
                  to={item.href}
                  title={collapsed ? item.label : undefined}
                  className={`flex items-center ${collapsed ? "justify-center" : ""} gap-2.5 rounded-md ${collapsed ? "px-2 py-2.5" : "px-2.5 py-2"} text-sm transition-colors ${
                    active
                      ? "bg-slate-800 text-white font-medium"
                      : "hover:bg-slate-800/60 hover:text-white"
                  }`}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {!collapsed && <span>{item.label}</span>}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className={`border-t border-slate-700 ${collapsed ? "px-2" : "px-4"} py-3`}>
        {!collapsed && (
          <>
            <p className="text-xs text-slate-500">Zinnia Eng</p>
            <p className="text-xs text-slate-600">Internal Platform</p>
          </>
        )}
        {onLogout && (
          <button
            onClick={onLogout}
            title={collapsed ? "Sign Out" : undefined}
            className={`mt-2 flex items-center ${collapsed ? "justify-center w-full" : ""} gap-2 text-xs text-slate-500 hover:text-red-400 transition-colors`}
          >
            <LogOut className="h-3.5 w-3.5" />
            {!collapsed && "Sign Out"}
          </button>
        )}
      </div>

      {/* Collapse Toggle (desktop only) */}
      <div className="hidden md:block border-t border-slate-700 p-2">
        <button
          onClick={onToggle}
          className="w-full flex items-center justify-center p-2 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          title={collapsed ? "Expand sidebar (Ctrl+B)" : "Collapse sidebar (Ctrl+B)"}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile hamburger button */}
      <button
        onClick={() => (mobileOpen ? onMobileClose() : onMobileClose() || onToggle())}
        className="md:hidden fixed top-4 left-4 z-50 p-2 bg-slate-900 text-white rounded-lg shadow-lg"
        aria-label="Toggle navigation"
      >
        {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="md:hidden fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
          onClick={onMobileClose}
        />
      )}

      {/* Mobile sidebar (overlay) */}
      <aside
        className={`md:hidden fixed left-0 top-0 z-50 h-screen w-64 bg-slate-900 text-slate-300 flex flex-col transform transition-transform duration-200 ease-in-out ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {sidebarContent}
      </aside>

      {/* Desktop sidebar */}
      <aside
        className={`hidden md:flex fixed left-0 top-0 z-40 h-screen bg-slate-900 text-slate-300 flex-col transition-all duration-200 ease-in-out ${
          collapsed ? "w-16" : "w-56"
        }`}
      >
        {sidebarContent}
      </aside>
    </>
  );
}
