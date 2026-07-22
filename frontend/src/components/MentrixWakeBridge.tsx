/**
 * App-wide Mentrix wake bridge (after login).
 * Desktop: native Windows wake + hotkey navigate to /mentrix-home.
 */
import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";

declare global {
  interface Window {
    zectDesktop?: {
      isDesktopApp?: boolean;
      mentrix?: {
        onWake?: (cb: (payload: { phrase?: string; source?: string }) => void) => () => void;
        onWakeStatus?: (cb: (payload: { ok?: boolean; reason?: string; engine?: string }) => void) => () => void;
        getWakeStatus?: () => Promise<{ ok?: boolean; reason?: string; engine?: string; wakeEnabled?: boolean }>;
      };
    };
  }
}

export default function MentrixWakeBridge() {
  const navigate = useNavigate();
  const location = useLocation();
  const [status, setStatus] = useState<string>("");

  useEffect(() => {
    const desktop = window.zectDesktop?.mentrix;
    if (!desktop) return;

    const unsubs: Array<() => void> = [];
    if (desktop.onWake) {
      unsubs.push(
        desktop.onWake((payload) => {
          if (location.pathname !== "/mentrix-home") {
            navigate("/mentrix-home");
          }
          window.dispatchEvent(
            new CustomEvent("mentrix-wake", { detail: { phrase: payload?.phrase || "Mentrix" } }),
          );
        }),
      );
    }
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
  }, [navigate, location.pathname]);

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
