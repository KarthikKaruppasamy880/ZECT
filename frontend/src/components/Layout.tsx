import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";

interface LayoutProps {
  onLogout?: () => void;
}

export default function Layout({ onLogout }: LayoutProps) {
  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar onLogout={onLogout} />
      <main className="ml-56 p-6">
        <Outlet />
      </main>
    </div>
  );
}
