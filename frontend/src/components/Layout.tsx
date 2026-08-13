import { useState, useEffect, useCallback } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";
import ProjectRepoSelector from "./ProjectRepoSelector";
import CollaborationPanel from "./CollaborationPanel";
import MentrixWakeBridge from "./MentrixWakeBridge";
import MentrixPersistentDock from "./MentrixPersistentDock";
import { MentrixSessionProvider } from "@/mentrix/MentrixSessionContext";

interface LayoutProps {
  onLogout?: () => void;
}

export default function Layout({ onLogout }: LayoutProps) {
  const location = useLocation();
  const mentrixHud = location.pathname === "/mentrix-home";
  // User owns desktop collapse/expand; Companion HUD must not force-collapse.
  const [collapsed, setCollapsed] = useState(() => {
    return localStorage.getItem("sidebar-collapsed") === "true";
  });
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleToggle = useCallback(() => {
    if (window.innerWidth < 768) {
      setMobileOpen((prev) => !prev);
    } else {
      setCollapsed((prev) => {
        const next = !prev;
        localStorage.setItem("sidebar-collapsed", String(next));
        return next;
      });
    }
  }, []);

  const handleMobileClose = useCallback(() => {
    setMobileOpen(false);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "b") {
        e.preventDefault();
        handleToggle();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleToggle]);

  return (
    <MentrixSessionProvider>
      <div className={`min-h-screen ${mentrixHud ? "bg-slate-950" : "bg-slate-50"}`}>
        <Sidebar
          onLogout={onLogout}
          collapsed={collapsed}
          onToggle={handleToggle}
          mobileOpen={mobileOpen}
          onMobileClose={handleMobileClose}
        />
        <div
          className={`transition-all duration-200 ease-in-out ${
            collapsed ? "md:ml-16" : "md:ml-56"
          }`}
        >
          {!mentrixHud && (
            <div className="hidden md:flex items-center justify-between px-6 py-2 border-b border-slate-200 bg-white">
              <ProjectRepoSelector />
              <div className="flex items-center gap-3">
                <MentrixWakeBridge />
                <CollaborationPanel
                  room="zect-global"
                  user={
                    (typeof localStorage !== "undefined" &&
                      localStorage.getItem("zect_username")) ||
                    "operator"
                  }
                />
                <div className="text-xs text-slate-400">ZECT v2.0</div>
              </div>
            </div>
          )}
          {mentrixHud && (
            <div className="hidden md:flex justify-end px-3 py-1">
              <MentrixWakeBridge />
            </div>
          )}
          <main className={mentrixHud ? "p-0" : "p-4 md:p-6 pt-16 md:pt-4"}>
            <Outlet />
          </main>
        </div>
        <MentrixPersistentDock />
      </div>
    </MentrixSessionProvider>
  );
}
