/**
 * ZECT Present product shell.
 * Dashboard → Create / Blank / Import → Studio → Review/Rehearse → Export
 */
import { NavLink, Outlet, useLocation } from "react-router-dom";

const NAV = [
  { to: "/present", label: "Dashboard", end: true, testId: "present-nav-dashboard" },
  { to: "/present/create", label: "Create with AI", end: false, testId: "present-nav-create" },
  { to: "/present/templates", label: "Templates", end: false, testId: "present-nav-templates" },
];

export default function PresentShell() {
  const location = useLocation();
  const studio = /\/present\/d\/[^/]+\/edit\/?$/.test(location.pathname);

  return (
    <div className={studio ? "zect-page flex h-[calc(100vh-3.5rem)] min-h-0 flex-col space-y-2" : "zect-page space-y-4"} data-testid="zect-present-page">
      {studio ? (
        <p className="sr-only">Present Studio</p>
      ) : (
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[11px] uppercase tracking-wide text-teal-800">ZECT Present</p>
            <h1 className="text-2xl font-semibold text-slate-900">Presentations</h1>
          </div>
          <nav className="flex flex-wrap gap-1.5" aria-label="Present">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                data-testid={item.testId}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-1.5 text-xs font-medium ${
                    isActive ? "bg-teal-800 text-white" : "border border-slate-200 bg-white text-slate-700"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      )}
      <div className={studio ? "min-h-0 flex-1" : undefined}>
        <Outlet />
      </div>
    </div>
  );
}
