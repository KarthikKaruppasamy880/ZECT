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
        onWakeStatus?: (cb: (payload: { ok?: boolean; reason?: string; engine?: string }) => void) => () => void;
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

export default function MentrixWakeBridge() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<string>("");

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

    const unsubs: Array<() => void> = [];
    if (desktop.onWakeStatus) {
      unsubs.push(
        desktop.onWakeStatus((s) => {
          if (s?.ok) setStatus("Listening for Hey Mentrix (headset mic)");
          else if (s?.reason === "disabled") setStatus("Wake disabled");
          else setStatus(`Wake: use Ctrl+Shift+Space (${s?.reason || "starting"})`);
        }),
      );
    }
    desktop.getWakeStatus?.().then((s) => {
      if (s?.ok) setStatus("Listening for Hey Mentrix (headset mic)");
      else setStatus("Wake: Ctrl+Shift+Space · Mentrix menu → Restart wake listening");
    });

    return () => unsubs.forEach((u) => u());
  }, []);

  if (!window.zectDesktop?.isDesktopApp || !status) return null;

  return (
    <div
      className="hidden md:block text-[11px] text-teal-800 bg-teal-50 border border-teal-100 rounded px-2 py-1"
      data-testid="mentrix-wake-bridge"
      title="Set Windows default microphone to your headset"
    >
      {status}
    </div>
  );
}
