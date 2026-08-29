/**
 * Mentrix desktop launcher controls — shortcut + relaunch after updates.
 */
import { useCallback, useEffect, useState } from "react";
import { ExternalLink, RefreshCw, Rocket } from "lucide-react";

type ShortcutStatus = {
  ok?: boolean;
  supported?: boolean;
  exists?: boolean;
  stale?: boolean;
  shortcutPath?: string;
  mode?: string;
  version?: string;
  error?: string;
  launcherScript?: string;
};

export default function MentrixDesktopPanel() {
  const launcher = window.zectDesktop?.launcher;
  const [status, setStatus] = useState<ShortcutStatus | null>(null);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    if (!launcher?.getShortcutStatus) return;
    try {
      const s = await launcher.getShortcutStatus();
      setStatus(s);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Could not read shortcut status");
    }
  }, [launcher]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (!window.zectDesktop?.isDesktopApp || !launcher) return null;

  const statusLabel = !status?.supported
    ? "Desktop shortcuts are supported on Windows only"
    : !status?.exists
      ? "No desktop shortcut yet"
      : status.stale
        ? "Shortcut exists but is out of date"
        : "Desktop shortcut is ready";

  async function run(action: "shortcut" | "relaunch" | "pull") {
    setMessage("");
    setBusy(action);
    try {
      if (action === "shortcut") {
        const res = await launcher!.createShortcut!();
        if (!res?.ok) {
          setMessage(res?.error || "Could not create shortcut");
          return;
        }
        setMessage(`Shortcut ${res.operation === "update" ? "updated" : "created"} on your desktop`);
      } else if (action === "relaunch") {
        await launcher!.relaunch!();
      } else {
        const res = await launcher!.pullUpdatesAndRelaunch!();
        if (!res?.ok) {
          setMessage(res?.error || res?.stderr || "Update failed");
          return;
        }
        setMessage("Pulling updates and relaunching…");
      }
      await refresh();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy("");
    }
  }

  return (
    <div
      className="rounded-xl border border-slate-700/80 bg-slate-900/60 p-3"
      data-testid="mentrix-desktop-panel"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-300">Desktop launcher</p>
          <p className="mt-1 text-[11px] text-slate-400" data-testid="mentrix-desktop-shortcut-status">
            {statusLabel}
            {status?.version ? ` · v${status.version}` : ""}
            {status?.mode === "dev" ? " · dev stack" : ""}
          </p>
          {status?.shortcutPath ? (
            <p className="mt-1 truncate text-[10px] text-slate-500" title={status.shortcutPath}>
              {status.shortcutPath}
            </p>
          ) : null}
          {message ? (
            <p className="mt-1 text-[11px] text-teal-300" data-testid="mentrix-desktop-message">
              {message}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            data-testid="mentrix-desktop-shortcut-create"
            disabled={!!busy || status?.supported === false}
            onClick={() => void run("shortcut")}
            className="inline-flex items-center gap-1.5 rounded-lg border border-teal-700 bg-teal-950/40 px-3 py-1.5 text-xs text-teal-100 disabled:opacity-50"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            {status?.exists ? "Update shortcut" : "Create shortcut"}
          </button>
          <button
            type="button"
            data-testid="mentrix-desktop-relaunch"
            disabled={!!busy}
            onClick={() => void run("relaunch")}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 px-3 py-1.5 text-xs disabled:opacity-50"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Relaunch ZECT
          </button>
          <button
            type="button"
            data-testid="mentrix-desktop-pull-relaunch"
            disabled={!!busy}
            onClick={() => {
              if (!window.confirm("Pull latest code from git, refresh the desktop shortcut, and relaunch ZECT?")) {
                return;
              }
              void run("pull");
            }}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 px-3 py-1.5 text-xs disabled:opacity-50"
            title="git pull --ff-only, update shortcut, relaunch"
          >
            <Rocket className="h-3.5 w-3.5" />
            Update &amp; relaunch
          </button>
        </div>
      </div>
      <p className="mt-2 text-[10px] text-slate-500">
        Pin ZECT to your desktop. After you pull code changes, click the shortcut or use Update &amp; relaunch here.
      </p>
    </div>
  );
}
