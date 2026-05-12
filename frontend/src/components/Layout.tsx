import { useState, useEffect, useCallback } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import ProjectRepoSelector from "./ProjectRepoSelector";

interface LayoutProps {
  onLogout?: () => void;
}

export default function Layout({ onLogout }: LayoutProps) {
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

  // Keyboard shortcut: Ctrl+B to toggle sidebar
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
    <div className="min-h-screen bg-slate-50">
      <Sidebar
        onLogout={onLogout}
        collapsed={collapsed}
        onToggle={handleToggle}
        mobileOpen={mobileOpen}
        onMobileClose={handleMobileClose}
      />
      {/* Main content with responsive margin */}
      <div
        className={`transition-all duration-200 ease-in-out ${
          collapsed ? "md:ml-16" : "md:ml-56"
        }`}
      >
        {/* Top bar with project/repo selector */}
        <div className="hidden md:flex items-center justify-between px-6 py-2 border-b border-slate-200 bg-white">
          <ProjectRepoSelector />
          <div className="text-xs text-slate-400">ZECT v2.0</div>
        </div>
        <main className="p-4 md:p-6 pt-16 md:pt-4">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
