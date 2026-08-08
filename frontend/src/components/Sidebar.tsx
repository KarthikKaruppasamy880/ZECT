import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  FolderKanban,
  GitBranch,
  BarChart3,
  FileText,
  Settings,
  Microscope,
  Sparkles,
  BookOpen,
  ShieldCheck,
  GitCompareArrows,
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
  Download,
  History,
  Activity,
  Brain,
  ShieldAlert,
  ArrowRightLeft,
  Wrench,
  BookMarked,
  Calendar,
  KeyRound,
  Code2,
  MessageCircle,
  HardDrive,
  PanelLeft,
  Bot,
  Rocket,
  Network,
  FlaskConical,
  Box,
  AlertTriangle,
  StickyNote,
} from "lucide-react";
import { isAgentModeEnabled } from "@/lib/featureFlags";

type NavItem = { href: string; label: string; icon: typeof LayoutDashboard };

const workflowItems: NavItem[] = [
  { href: "/mentrix-home", label: "Mentrix Companion", icon: Sparkles },
  { href: "/mentrix-home?incident=1", label: "Incident Runbook", icon: AlertTriangle },
  { href: "/ask", label: "Agent Workspace", icon: Bot },
  { href: "/mentrix", label: "Mentrix Delivery", icon: Rocket },
];

const workspaceItems: NavItem[] = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/projects", label: "Projects", icon: FolderKanban },
  { href: "/repo-workspace", label: "Repo Workspace", icon: HardDrive },
  { href: "/workspace", label: "Developer Workspace", icon: PanelLeft },
];

const understandItems: NavItem[] = [
  { href: "/lattice", label: "Lattice Graph", icon: Network },
  { href: "/repo-analysis", label: "Repo Analysis", icon: Microscope },
  { href: "/blueprint", label: "Blueprint", icon: Sparkles },
  { href: "/doc-generator", label: "Doc Generator", icon: BookOpen },
  { href: "/code-index", label: "Code Index", icon: Code2 },
  { href: "/docs", label: "Docs Center", icon: FileText },
];

/** Ask/Plan/Build/Review/Deploy live in the Agent Workspace rail — not duplicated here. */
const deliverItemsBase: NavItem[] = [
  { href: "/orchestration", label: "Orchestration", icon: GitBranch },
];

const agentModeItem: NavItem = { href: "/agent-mode", label: "Agent Mode (Advanced)", icon: Bot };

const qualityItems: NavItem[] = [
  { href: "/code-review", label: "Mentrix Ultra Review", icon: ShieldCheck },
  { href: "/rules", label: "Rules Engine", icon: Scale },
  { href: "/sandbox", label: "Sandbox Gate", icon: Box },
  { href: "/ci-monitor", label: "CI Monitor", icon: Activity },
  { href: "/git-ops", label: "Git Operations", icon: GitBranch },
];

const enterpriseItems: NavItem[] = [
  { href: "/integrations", label: "Integrations", icon: Plug },
  { href: "/audit-trail", label: "Audit Trail", icon: ScrollText },
  { href: "/export", label: "Export/Share", icon: Download },
  { href: "/output-history", label: "Output History", icon: History },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/token-controls", label: "Token Controls", icon: Coins },
  { href: "/secrets", label: "Secrets Manager", icon: KeyRound },
];

/** Primary Labs — productivity spine (Skills / Playbooks / Knowledge / Schedules / Memory / Permissions). */
const labsItems: NavItem[] = [
  { href: "/skills-engine", label: "Skills Engine", icon: Wrench },
  { href: "/playbooks", label: "Playbooks", icon: BookOpen },
  { href: "/knowledge-base", label: "Knowledge Base", icon: BookMarked },
  { href: "/scheduled-tasks", label: "Scheduled Tasks", icon: Calendar },
  { href: "/file-organize", label: "File Organize", icon: HardDrive },
  { href: "/memory", label: "Memory System", icon: Brain },
  { href: "/permissions", label: "Permissions", icon: ShieldAlert },
];

/** Advanced Labs — still first-class routes; collapsed under More Labs. */
const labsAdvancedItems: NavItem[] = [
  { href: "/security-incidents", label: "Security Incidents", icon: ShieldCheck },
  { href: "/mentrix-notes", label: "Mentrix Notes", icon: StickyNote },
  { href: "/transfer", label: "Transfer & Onboard", icon: ArrowRightLeft },
  { href: "/conversations", label: "Conversations", icon: MessageCircle },
  { href: "/tool-comparison", label: "Architecture", icon: GitCompareArrows },
];

const sections: { title: string; items: NavItem[] }[] = [
  { title: "Workflow", items: workflowItems },
  { title: "Workspace", items: workspaceItems },
  { title: "Understand", items: understandItems },
  { title: "Deliver", items: deliverItemsBase },
  { title: "Quality", items: qualityItems },
  { title: "Enterprise", items: enterpriseItems },
  { title: "Labs", items: labsItems },
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
  const [labsMoreOpen, setLabsMoreOpen] = useState(() =>
    labsAdvancedItems.some((item) => location.pathname === item.href),
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
    if (labsAdvancedItems.some((item) => location.pathname === item.href)) {
      setLabsMoreOpen(true);
    }
  }, [location.pathname]);

  const navSections = sections.map((section) =>
    section.title === "Deliver"
      ? {
          ...section,
          items: agentModeOn ? [...deliverItemsBase, agentModeItem] : deliverItemsBase,
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
          className={`flex items-center ${collapsed ? "justify-center" : ""} gap-2.5 rounded-md ${
            collapsed ? "px-2 py-2.5" : "px-2.5 py-2"
          } text-sm transition-colors ${
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
  };

  const renderSection = (title: string, items: NavItem[], isFirst: boolean) => (
    <div key={title}>
      {!collapsed ? (
        <p
          className={`px-2 mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500 ${
            isFirst ? "" : "mt-6"
          }`}
        >
          {title}
          {title === "Labs" && (
            <FlaskConical className="inline h-3 w-3 ml-1 opacity-60" />
          )}
        </p>
      ) : (
        !isFirst && <div className="my-4 border-t border-slate-700" />
      )}
      <ul className="space-y-0.5">
        {items.map((item) => renderNavLink(item))}
        {title === "Labs" && (
          <>
            {!collapsed && (
              <li>
                <button
                  type="button"
                  data-testid="sidebar-labs-more"
                  onClick={() => setLabsMoreOpen((o) => !o)}
                  className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-sm text-slate-400 hover:bg-slate-800/60 hover:text-white"
                >
                  <ChevronDown
                    className={`h-4 w-4 shrink-0 transition-transform ${labsMoreOpen ? "" : "-rotate-90"}`}
                  />
                  <span>More Labs</span>
                </button>
              </li>
            )}
            {(labsMoreOpen || collapsed) && labsAdvancedItems.map((item) => renderNavLink(item))}
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
                Ship: Mentrix Delivery · Prep: Agent Workspace · Edit: Developer Workspace
              </p>
            </div>
          )}
          <button
            onClick={onToggle}
            className="hidden md:flex items-center justify-center h-7 w-7 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors flex-shrink-0"
            title={collapsed ? "Expand sidebar (Ctrl+B)" : "Collapse sidebar (Ctrl+B)"}
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-4">
        {navSections.map((section, idx) => renderSection(section.title, section.items, idx === 0))}
      </nav>

      <div className={`border-t border-slate-700 ${collapsed ? "px-2" : "px-3"} py-3 mt-auto`}>
        {!collapsed && (
          <p className="mb-2 text-[10px] text-slate-600 px-1">Hey Mentrix · desktop wake</p>
        )}
        <Link
          to="/settings"
          title={collapsed ? "Settings" : undefined}
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
              <p className="truncate text-[10px] text-slate-500">Settings · Voice · Keys</p>
            </div>
          )}
          {!collapsed && <Settings className="h-3.5 w-3.5 flex-shrink-0 text-slate-500" />}
        </Link>
        {onLogout && (
          <button
            onClick={onLogout}
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
          onClick={onToggle}
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
        onClick={onToggle}
        className="md:hidden fixed top-3 left-3 z-50 p-2.5 bg-slate-900 text-white rounded-xl shadow-lg border border-slate-700"
        aria-label="Toggle navigation"
      >
        {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {mobileOpen && (
        <div
          className="md:hidden fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
          onClick={onMobileClose}
        />
      )}

      <aside
        className={`md:hidden fixed left-0 top-0 z-50 h-screen w-64 bg-slate-900 text-slate-300 flex flex-col transform transition-transform duration-200 ease-in-out ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {sidebarContent}
      </aside>

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
