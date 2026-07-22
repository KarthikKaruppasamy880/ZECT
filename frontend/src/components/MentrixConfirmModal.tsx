/**
 * Fast Always-ask Allow? overlay for Mentrix Companion.
 */
import { useEffect } from "react";
import { ShieldAlert } from "lucide-react";

export type PendingConfirm = {
  tool: string;
  args?: Record<string, unknown>;
  reason?: string;
  audit_id?: number;
};

type Props = {
  open: boolean;
  items: PendingConfirm[];
  onAllow: (tools: string[]) => void;
  onDeny: () => void;
  speakPrompt?: boolean;
};

export default function MentrixConfirmModal({
  open,
  items,
  onAllow,
  onDeny,
  speakPrompt = true,
}: Props) {
  const names = items.map((i) => i.tool);

  useEffect(() => {
    if (!open || !items.length || !speakPrompt || typeof window === "undefined") return;
    if (!window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(
        `Allow Mentrix to run ${names.map((n) => n.replace(/_/g, " ")).join(", ")}?`,
      );
      u.rate = 1.08;
      window.speechSynthesis.speak(u);
    } catch {
      /* ignore */
    }
  }, [open, items, speakPrompt, names.join(",")]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        onAllow(names);
      } else if (e.key === "Escape") {
        e.preventDefault();
        onDeny();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, names, onAllow, onDeny]);

  if (!open || !items.length) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-end justify-center bg-black/55 p-4 sm:items-center"
      data-testid="mentrix-confirm-modal"
      role="dialog"
      aria-modal="true"
      aria-label="Allow Mentrix"
    >
      <div className="w-full max-w-md rounded-2xl border border-teal-500/40 bg-slate-950 text-slate-100 shadow-2xl shadow-teal-950/50">
        <div className="flex items-start gap-3 border-b border-teal-900/60 bg-teal-950/40 px-4 py-3">
          <ShieldAlert className="mt-0.5 h-5 w-5 text-amber-400" />
          <div>
            <h2 className="text-base font-semibold tracking-wide">Allow?</h2>
            <p className="mt-0.5 text-xs text-slate-400">
              Mentrix needs your OK — Enter to Allow, Esc to Deny.
            </p>
          </div>
        </div>
        <ul className="max-h-40 space-y-2 overflow-auto px-4 py-3 text-sm">
          {items.map((item) => (
            <li key={item.tool} className="rounded-lg border border-slate-700 px-3 py-2">
              <div className="font-mono text-xs text-teal-300">{item.tool}</div>
              <div className="mt-1 text-xs text-slate-400">{item.reason || "Confirm to continue"}</div>
            </li>
          ))}
        </ul>
        <div className="flex justify-end gap-2 border-t border-slate-800 px-4 py-3">
          <button
            type="button"
            data-testid="mentrix-confirm-deny"
            onClick={onDeny}
            className="rounded-lg border border-slate-600 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-900"
          >
            Deny
          </button>
          <button
            type="button"
            data-testid="mentrix-confirm-allow"
            onClick={() => onAllow(names)}
            className="rounded-lg bg-teal-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-teal-500"
          >
            Allow
          </button>
        </div>
      </div>
    </div>
  );
}
