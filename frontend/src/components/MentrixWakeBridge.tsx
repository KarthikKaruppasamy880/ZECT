/**
 * App-wide Mentrix wake status chip (after login).
 * Wake handling + Connect Voice live in MentrixSessionProvider (survives navigation).
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

declare global {
  interface Window {
    zectDesktop?: {
      isDesktopApp?: boolean;
      selectDirectory?: (opts?: {
        title?: string;
        defaultPath?: string;
      }) => Promise<{ ok?: boolean; canceled?: boolean; path?: string; error?: string }>;
      launcher?: {
        getShortcutStatus?: () => Promise<{
          ok?: boolean;
          supported?: boolean;
          exists?: boolean;
          stale?: boolean;
          shortcutPath?: string;
          mode?: string;
          version?: string;
          error?: string;
        }>;
        createShortcut?: () => Promise<{ ok?: boolean; operation?: string; error?: string }>;
        relaunch?: () => Promise<{ ok?: boolean }>;
        pullUpdatesAndRelaunch?: () => Promise<{ ok?: boolean; error?: string; stderr?: string }>;
      };
      mentrix?: {
        onWake?: (cb: (payload: { phrase?: string; source?: string }) => void) => () => void;
        onWakeStatus?: (cb: (payload: { ok?: boolean; reason?: string; engine?: string; wakeEnabled?: boolean }) => void) => () => void;
        getWakeStatus?: () => Promise<{ ok?: boolean; reason?: string; engine?: string; wakeEnabled?: boolean }>;
        onSttGoal?: (cb: (payload: { goal?: string }) => void) => () => void;
        onComputerMode?: (cb: (payload: { computerMode?: boolean; reason?: string }) => void) => () => void;
        setComputerMode?: (enabled: boolean) => Promise<unknown>;
        setEmergencyStop?: (active: boolean) => Promise<unknown>;
        setDictationEnabled?: (enabled: boolean) => Promise<unknown>;
        armDictation?: (durationMs?: number) => Promise<unknown>;
        disarmDictation?: () => Promise<unknown>;
        setDictationPaused?: (paused: boolean) => Promise<unknown>;
        setWakeEnabled?: (enabled: boolean) => Promise<unknown>;
        submitTranscript?: (t: string) => Promise<{ matched?: boolean }>;
        confirmAction?: (payload: unknown) => Promise<unknown>;
        computer?: (action: string, args?: Record<string, unknown>) => Promise<unknown>;
      };
    };
  }
}

function labelForWake(s: { ok?: boolean; reason?: string; wakeEnabled?: boolean } | undefined): string {
  if (s?.wakeEnabled === false || s?.reason === "disabled") return "Hey Mentrix off — click to enable";
  if (s?.ok) return "Listening for Hey Mentrix (headset mic)";
  return `Wake: Ctrl+Shift+Space (${s?.reason || "off"})`;
}

export default function MentrixWakeBridge() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<string>("");
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    const onSpaNav = (ev: Event) => {
      const path = (ev as CustomEvent<{ path?: string }>).detail?.path;
      if (path) navigate(path);
    };
    window.addEventListener("mentrix-spa-navigate", onSpaNav);
    return () => window.removeEventListener("mentrix-spa-navigate", onSpaNav);
  }, [navigate]);

  useEffect(() => {
    const desktop = window.zectDesktop?.mentrix;
    if (!desktop) return;

    const apply = (s: { ok?: boolean; reason?: string; wakeEnabled?: boolean } | undefined) => {
      setEnabled(Boolean(s?.wakeEnabled ?? s?.ok));
      setStatus(labelForWake(s));
    };

    const unsubs: Array<() => void> = [];
    if (desktop.onWakeStatus) {
      unsubs.push(desktop.onWakeStatus(apply));
    }
    desktop.getWakeStatus?.().then(apply);

    return () => unsubs.forEach((u) => u());
  }, []);

  if (!window.zectDesktop?.isDesktopApp || !status) return null;

  const toggle = () => {
    void window.zectDesktop?.mentrix?.setWakeEnabled?.(!enabled);
  };

  return (
    <button
      type="button"
      className="hidden md:block text-[11px] text-teal-800 bg-teal-50 border border-teal-100 rounded px-2 py-1"
      data-testid="mentrix-wake-bridge"
      title="Click to enable or disable Hey Mentrix. Headset mic is the Windows default recording device."
      onClick={toggle}
    >
      {status}
    </button>
  );
}
