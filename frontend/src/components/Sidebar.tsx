import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  FolderKanban,
  GitBranch,
  BarChart3,
  FileText,
  Settings,
  Sparkles,
  BookOpen,
  ShieldCheck,
  LogOut,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Menu,
  X,
  Coins,
  ScrollText,
  Plug,
  Scale,
  Activity,
  Brain,
  ShieldAlert,
  Wrench,
  BookMarked,
  Calendar,
  KeyRound,
  HardDrive,
  PanelLeft,
  Bot,
  Rocket,
  Network,
  FlaskConical,
  Box,
  Presentation,
} from "lucide-react";
import { isAgentModeEnabled } from "@/lib/featureFlags";

type NavItem = { href: string; label: string; icon: typeof LayoutDashboard };

/** P2 target navigation — routes kept; internals moved into composite sections. */
const mentrixItems: NavItem[] = [
  { href: "/mentrix-home", label: "Mentrix Companion", icon: Sparkles },
  { href: "/present", label: "Present", icon: Presentation },
  { href: "/workspace", label: "Developer", icon: PanelLeft },
  { href: "/ask", label: "Agent Workspace", icon: Bot },
];

const workItems: NavItem[] = [
  { href: "/projects", label: "Projects", icon: FolderKanban },
  { href: "/work-items", label: "Work Items", icon: ScrollText },
  { href: "/fabric", label: "Processes", icon: Network },
];

const intelligenceItems: NavItem[] = [
  { href: "/project-intelligence", label: "Project Intelligence", icon: Brain },
  { href: "/knowledge-base", label: "Knowledge Base", icon: BookMarked },
  { href: "/learning", label: "ZECT Learning", icon: BookOpen },
  { href: "/skills-engine", label: "Skills Engine", icon: Wrench },
  { href: "/playbooks", label: "Playbooks", icon: BookOpen },
  { href: "/lattice", label: "Lattice", icon: Network },
  { href: "/blueprint", label: "Blueprint", icon: Sparkles },
];

const deliveryItemsBase: NavItem[] = [
  { href: "/mentrix", label: "Runs", icon: Rocket },
  { href: "/code-review", label: "Quality", icon: ShieldCheck },
  { href: "/git-ops", label: "Git & CI", icon: GitBranch },
  { href: "/ci-monitor", label: "CI Monitor", icon: Activity },
  { href: "/sandbox", label: "Sandbox", icon: Box },
];

const agentModeItem: NavItem = { href: "/agent-mode", label: "Agent Mode (Advanced)", icon: Bot };

const securityItems: NavItem[] = [
  { href: "/security-incidents", label: "Security", icon: ShieldAlert },
  { href: "/mentrix-home?incident=1", label: "Incident Runbook", icon: ShieldAlert },
];

const operationsItems: NavItem[] = [
  { href: "/system-health", label: "System Health", icon: Activity },
  { href: "/integrations", label: "Integrations", icon: Plug },
  { href: "/scheduled-tasks", label: "Scheduled Tasks", icon: Calendar },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
];

const settingsOwnedItems: NavItem[] = [
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/permissions", label: "Permissions", icon: ShieldAlert },
  { href: "/memory", label: "Memory System", icon: Brain },
  { href: "/secrets", label: "Secrets", icon: KeyRound },
  { href: "/token-controls", label: "Token Controls", icon: Coins },
  { href: "/rules", label: "Rules", icon: Scale },
  { href: "/audit-trail", label: "Audit Trail", icon: ScrollText },
  { href: "/tool-comparison", label: "Architecture", icon: FileText },
  { href: "/security-incidents", label: "Security Incidents", icon: ShieldAlert },
  { href: "/docs", label: "Docs", icon: FileText },
  { href: "/repo-workspace", label: "Repo Workspace", icon: HardDrive },
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
];

const sections: { title: string; items: NavItem[] }[] = [
  { title: "Mentrix", items: mentrixItems },
  { title: "Work", items: workItems },
  { title: "Intelligence", items: intelligenceItems },
  { title: "Delivery", items: deliveryItemsBase },
  { title: "Security", items: securityItems },
  { title: "Operations", items: operationsItems },
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
  const [agentModeOn, setAgentModeOn] = useState(() => isAgentModeEnabled());
  const [settingsMoreOpen, setSettingsMoreOpen] = useState(() =>
    settingsOwnedItems.some(
      (item) => item.href !== "/" && location.pathname === item.href,
    ),
  );

  useEffect(() => {
    onMobileClose();
  }, [location.pathname]);

  useEffect(() => {
    const sync = () => setAgentModeOn(isAgentModeEnabled());
    window.addEventListener("zect-feature-flags", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("zect-feature-flags", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  useEffect(() => {
    // Do not treat Dashboard "/" as a reason to force-open More settings
    if (
      settingsOwnedItems.some(
        (item) => item.href !== "/" && location.pathname === item.href,
      )
    ) {
      setSettingsMoreOpen(true);
    }
  }, [location.pathname]);

  const navSections = sections.map((section) =>
    section.title === "Delivery"
      ? {
          ...section,
          items: agentModeOn ? [...deliveryItemsBase, agentModeItem] : deliveryItemsBase,
        }
      : section,
  );

  const renderNavLink = (item: NavItem) => {
    const Icon = item.icon;
    const itemUrl = new URL(item.href, "http://local");
    const pathMatch = location.pathname === itemUrl.pathname;
    const voiceDeepLink = itemUrl.searchParams.get("voice");
    const incidentDeepLink = itemUrl.searchParams.get("incident");
    const search = new URLSearchParams(location.search);
    const active = voiceDeepLink
      ? pathMatch && search.get("voice") === voiceDeepLink
      : incidentDeepLink
        ? pathMatch && search.get("incident") === incidentDeepLink
        : pathMatch &&
          !(
            itemUrl.pathname === "/mentrix-home" &&
            (search.get("voice") || search.get("incident"))
          );
    return (
      <li key={item.href}>
        <Link
          to={item.href}
          title={collapsed ? item.label : undefined}
          aria-label={item.label}
          aria-current={active ? "page" : undefined}
          className={`flex items-center ${collapsed ? "justify-center" : ""} gap-2.5 rounded-md ${
            collapsed ? "px-2 py-2.5" : "px-2.5 py-2"
          } text-sm transition-colors ${
            active
              ? "bg-slate-800 text-white font-medium"
              : "hover:bg-slate-800/60 hover:text-white"
          }`}
        >
          <Icon className="h-4 w-4 shrink-0" aria-hidden />
          {!collapsed && <span>{item.label}</span>}
        </Link>
      </li>
    );
  };

  const renderSection = (title: string, items: NavItem[], isFirst: boolean) => (
    <div key={title}>
      {!collapsed ? (
        <h2
          className={`px-2 mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500 ${
            isFirst ? "" : "mt-6"
          }`}
        >
          {title}
          {title === "Operations" && (
            <FlaskConical className="inline h-3 w-3 ml-1 opacity-60" aria-hidden />
          )}
        </h2>
      ) : (
        !isFirst && <div className="my-4 border-t border-slate-700" role="separator" />
      )}
      <ul className="space-y-0.5">
        {items.map((item) => renderNavLink(item))}
        {title === "Operations" && (
          <>
            {!collapsed && (
              <li>
                <button
                  type="button"
                  data-testid="sidebar-labs-more"
                  aria-expanded={settingsMoreOpen}
                  onClick={() => setSettingsMoreOpen((o) => !o)}
                  className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-sm text-slate-400 hover:bg-slate-800/60 hover:text-white"
                >
                  <ChevronDown
                    className={`h-4 w-4 shrink-0 transition-transform ${settingsMoreOpen ? "" : "-rotate-90"}`}
                    aria-hidden
                  />
                  <span>More settings</span>
                </button>
              </li>
            )}
            {(settingsMoreOpen || collapsed) && settingsOwnedItems.map((item) => renderNavLink(item))}
          </>
        )}
      </ul>
    </div>
  );

  const sidebarContent = (
    <>
      <div className={`border-b border-slate-700 ${collapsed ? "px-2 py-3" : "px-4 py-4"}`}>
        <div className="flex items-center justify-between">
          {collapsed ? (
            <div className="flex flex-col items-center w-full">
              <span className="text-lg font-bold text-white">Z</span>
            </div>
          ) : (
            <div className="flex-1 min-w-0">
              <p className="text-xs uppercase tracking-wider text-slate-500">ZECT</p>
              <h1 className="text-sm font-bold text-white leading-tight">
                Mentrix Delivery
                <br />
                Control Tower
              </h1>
              <p className="text-[10px] text-slate-400 mt-1 leading-snug" data-testid="sidebar-spine-hint">
                Mentrix · Work · Intelligence · Delivery · Security · Operations
              </p>
            </div>
          )}
          <button
            type="button"
            onClick={onToggle}
            data-testid="sidebar-toggle"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-expanded={!collapsed}
            className="hidden md:flex items-center justify-center h-7 w-7 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors flex-shrink-0"
            title={collapsed ? "Expand sidebar (Ctrl+B)" : "Collapse sidebar (Ctrl+B)"}
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-4" aria-label="Primary">
        {navSections.map((section, idx) => renderSection(section.title, section.items, idx === 0))}
      </nav>

      <div className={`border-t border-slate-700 ${collapsed ? "px-2" : "px-3"} py-3 mt-auto`}>
        {!collapsed && (
          <p className="mb-2 text-[10px] text-slate-600 px-1">Hey Mentrix · desktop wake</p>
        )}
        <Link
          to="/settings"
          title={collapsed ? "Settings" : undefined}
          aria-label="Settings"
          data-testid="sidebar-user-settings"
          className={`flex items-center ${
            collapsed ? "justify-center" : "gap-2.5"
          } rounded-lg px-2 py-2 text-slate-300 hover:bg-slate-800 hover:text-white transition-colors ${
            location.pathname === "/settings" ? "bg-slate-800 text-white" : ""
          }`}
        >
          <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-teal-800/80 text-[11px] font-semibold text-teal-100">
            {(typeof localStorage !== "undefined"
              ? (localStorage.getItem("zect_username") || "U").trim().charAt(0)
              : "U"
            ).toUpperCase()}
          </div>
          {!collapsed && (
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-medium text-slate-100">
                {typeof localStorage !== "undefined"
                  ? localStorage.getItem("zect_username") || "Account"
                  : "Account"}
              </p>
              <p className="truncate text-[10px] text-slate-500">Settings · Governance · Voice</p>
            </div>
          )}
          {!collapsed && <Settings className="h-3.5 w-3.5 flex-shrink-0 text-slate-500" />}
        </Link>
        {onLogout && (
          <button
            type="button"
            onClick={onLogout}
            aria-label="Sign out"
            title={collapsed ? "Sign Out" : undefined}
            className={`mt-1 flex w-full items-center ${
              collapsed ? "justify-center" : "gap-2 px-2"
            } rounded-md py-1.5 text-xs text-slate-500 hover:text-red-400 transition-colors`}
          >
            <LogOut className="h-3.5 w-3.5" />
            {!collapsed && "Sign Out"}
          </button>
        )}
      </div>

      <div className="hidden md:block border-t border-slate-700 p-2">
        <button
          type="button"
          onClick={onToggle}
          data-testid="sidebar-toggle-footer"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-expanded={!collapsed}
          className="w-full flex items-center justify-center gap-1.5 p-2 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors text-xs"
          title={collapsed ? "Expand sidebar (Ctrl+B)" : "Collapse sidebar (Ctrl+B)"}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <>
              <ChevronLeft className="h-4 w-4" />
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>
    </>
  );

  return (
    <>
      <button
        type="button"
        onClick={onToggle}
        className="md:hidden fixed top-3 left-3 z-50 p-2.5 bg-slate-900 text-white rounded-xl shadow-lg border border-slate-700"
        aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
        aria-expanded={mobileOpen}
        data-testid="sidebar-mobile-toggle"
      >
        {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {mobileOpen && (
        <div
          className="md:hidden fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
          onClick={onMobileClose}
          data-testid="sidebar-mobile-backdrop"
        />
      )}

      <aside
        className={`md:hidden fixed left-0 top-0 z-50 h-screen w-64 bg-slate-900 text-slate-300 flex flex-col transform transition-transform duration-200 ease-in-out ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        aria-hidden={!mobileOpen}
        aria-label="Mobile navigation"
      >
        {sidebarContent}
      </aside>

      <aside
        className={`hidden md:flex fixed left-0 top-0 z-40 h-screen bg-slate-900 text-slate-300 flex-col transition-all duration-200 ease-in-out ${
          collapsed ? "w-16" : "w-56"
        }`}
        data-testid="app-sidebar"
        aria-label="Primary navigation"
      >
        {sidebarContent}
      </aside>
    </>
  );
}
