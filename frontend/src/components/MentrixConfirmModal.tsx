/**
 * Always-ask confirmation for Mentrix Companion sensitive tools.
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
  useEffect(() => {
    if (!open || !items.length || !speakPrompt || typeof window === "undefined") return;
    if (!window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(
        `Allow Mentrix to run ${items.map((i) => i.tool.replace(/_/g, " ")).join(", ")}?`,
      );
      u.rate = 1.05;
      window.speechSynthesis.speak(u);
    } catch {
      /* ignore */
    }
  }, [open, items, speakPrompt]);

  if (!open || !items.length) return null;
  const names = items.map((i) => i.tool);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      data-testid="mentrix-confirm-modal"
      role="dialog"
      aria-modal="true"
    >
      <div className="w-full max-w-md rounded-xl border border-amber-200 bg-white shadow-xl">
        <div className="flex items-start gap-3 border-b border-amber-100 bg-amber-50 px-4 py-3">
          <ShieldAlert className="h-5 w-5 text-amber-700 mt-0.5" />
          <div>
            <h2 className="font-semibold text-slate-900">Mentrix needs your permission</h2>
            <p className="text-xs text-slate-600 mt-1">
              Sensitive company or desktop actions always require your OK.
            </p>
          </div>
        </div>
        <ul className="px-4 py-3 space-y-2 max-h-48 overflow-auto text-sm">
          {items.map((item) => (
            <li key={item.tool} className="rounded-lg border border-slate-200 px-3 py-2">
              <div className="font-mono text-xs text-teal-800">{item.tool}</div>
              <div className="text-slate-600 text-xs mt-1">{item.reason || "Confirm to continue"}</div>
            </li>
          ))}
        </ul>
        <div className="flex justify-end gap-2 border-t border-slate-100 px-4 py-3">
          <button
            type="button"
            data-testid="mentrix-confirm-deny"
            onClick={onDeny}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700"
          >
            Deny
          </button>
          <button
            type="button"
            data-testid="mentrix-confirm-allow"
            onClick={() => onAllow(names)}
            className="rounded-lg bg-teal-700 px-3 py-1.5 text-sm text-white hover:bg-teal-800"
          >
            Allow
          </button>
        </div>
      </div>
    </div>
  );
}
