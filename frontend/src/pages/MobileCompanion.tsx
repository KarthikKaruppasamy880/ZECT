"""Thin mobile Companion client — chat + desktop command enqueue."""

import { useEffect, useState } from "react";
import {
  mentrixCompanionTurn,
  mentrixDesktopBridgeEnqueue,
  mentrixDesktopBridgeStatus,
} from "@/lib/api";

type BridgeStatus = { online?: boolean; error?: string; hint?: string };

export default function MobileCompanion() {
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [bridge, setBridge] = useState<BridgeStatus | null>(null);
  const [deskCmd, setDeskCmd] = useState("write_note");
  const [enqueueMsg, setEnqueueMsg] = useState("");

  const refreshBridge = async () => {
    try {
      const st = await mentrixDesktopBridgeStatus();
      setBridge(st);
    } catch {
      setBridge({ online: false, error: "desktop_offline", hint: "Cannot reach API" });
    }
  };

  useEffect(() => {
    refreshBridge();
    const t = setInterval(refreshBridge, 15000);
    return () => clearInterval(t);
  }, []);

  const sendChat = async () => {
    if (!message.trim()) return;
    setBusy(true);
    try {
      const out = await mentrixCompanionTurn(message.trim());
      setReply(out?.reply || JSON.stringify(out));
    } catch (e) {
      setReply(e instanceof Error ? e.message : "turn failed");
    } finally {
      setBusy(false);
    }
  };

  const enqueueDesktop = async () => {
    setEnqueueMsg("");
    try {
      await mentrixDesktopBridgeEnqueue({
        action: deskCmd,
        content: "Mobile Mentrix note",
        folder: "Desktop",
        filename: "mentrix-mobile-note.md",
      });
      setEnqueueMsg("Queued for Electron agent");
    } catch (e) {
      setEnqueueMsg(e instanceof Error ? e.message : "desktop offline");
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 max-w-lg mx-auto" data-testid="mobile-companion">
      <h1 className="text-xl font-semibold mb-1">Mentrix Mobile</h1>
      <p className="text-xs text-slate-400 mb-4">
        Thin Companion client. Desktop work runs on your linked Electron agent — not on the phone.
      </p>

      <div
        data-testid="mobile-desktop-status"
        className={`text-xs rounded border px-2 py-1.5 mb-4 ${
          bridge?.online ? "border-emerald-700 text-emerald-200" : "border-amber-700 text-amber-200"
        }`}
      >
        Desktop agent: {bridge?.online ? "online" : "offline"}
        {!bridge?.online && bridge?.hint ? ` — ${bridge.hint}` : ""}
      </div>

      <textarea
        data-testid="mobile-companion-input"
        className="w-full rounded-lg bg-slate-900 border border-slate-700 p-2 text-sm min-h-[88px]"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Ask Mentrix…"
      />
      <button
        type="button"
        data-testid="mobile-companion-send"
        disabled={busy}
        onClick={sendChat}
        className="mt-2 w-full rounded-lg bg-teal-700 hover:bg-teal-600 py-2 text-sm font-medium disabled:opacity-50"
      >
        {busy ? "Thinking…" : "Send"}
      </button>
      {reply ? (
        <pre className="mt-3 text-xs whitespace-pre-wrap bg-slate-900 border border-slate-800 rounded-lg p-3">
          {reply}
        </pre>
      ) : null}

      <div className="mt-6 border-t border-slate-800 pt-4 space-y-2">
        <h2 className="text-sm font-medium">Desktop command</h2>
        <select
          className="w-full rounded bg-slate-900 border border-slate-700 text-sm p-2"
          value={deskCmd}
          onChange={(e) => setDeskCmd(e.target.value)}
        >
          <option value="write_note">Write allowlisted note</option>
          <option value="open_presentation">Open Present Deck path</option>
          <option value="screenshot">Screenshot</option>
        </select>
        <button
          type="button"
          data-testid="mobile-desktop-enqueue"
          onClick={enqueueDesktop}
          className="w-full rounded-lg border border-slate-600 py-2 text-sm"
        >
          Queue to Electron
        </button>
        {enqueueMsg ? <p className="text-xs text-slate-400">{enqueueMsg}</p> : null}
      </div>
    </div>
  );
}
