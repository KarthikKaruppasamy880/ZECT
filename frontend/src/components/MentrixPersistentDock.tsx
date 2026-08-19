/**
 * Floating Mentrix dock — survives route changes; hidden on full HUD path.
 */
import { Link, useLocation } from "react-router-dom";
import { useEffect } from "react";
import { Bot, Mic, MicOff, Send, X } from "lucide-react";
import { ORB, useMentrixSession } from "@/mentrix/MentrixSessionContext";
import MentrixConfirmModal from "@/components/MentrixConfirmModal";
import CompanionScopeStrip from "@/components/CompanionScopeStrip";

export default function MentrixPersistentDock() {
  const location = useLocation();
  const hideChrome = location.pathname === "/mentrix-home";
  const s = useMentrixSession();

  useEffect(() => {
    if (hideChrome || !s.dockExpanded) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") s.setDockExpanded(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [hideChrome, s.dockExpanded, s.setDockExpanded]);

  if (hideChrome) {
    // Full HUD owns chrome; Keep Allow modal available if pending while on HUD
    // (HUD also renders modal — skip duplicate).
    return null;
  }

  return (
    <>
      <div
        className={`fixed bottom-4 right-4 z-40 flex max-h-[70vh] flex-col gap-2 ${
          s.dockExpanded ? "w-[min(100vw-2rem,22rem)]" : "w-auto items-end"
        }`}
        data-testid="mentrix-persistent-dock"
      >
        {s.dockExpanded ? (
          <div className="overflow-hidden rounded-2xl border border-teal-800/60 bg-slate-950/95 text-slate-100 shadow-2xl backdrop-blur">
            <div className="flex items-center justify-between gap-2 border-b border-slate-800 px-3 py-2">
              <div className="flex items-center gap-2">
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full border-2 bg-gradient-to-br ${ORB[s.avatar]}`}
                  data-testid="mentrix-dock-orb"
                  data-state={s.avatar}
                >
                  <Bot className="h-4 w-4 text-teal-300" />
                </div>
                <div>
                  <p className="text-xs font-semibold tracking-wide text-teal-200">MENTRIX</p>
                  <p className="max-w-[12rem] truncate text-[10px] text-slate-400" title={s.statusLine}>
                    {s.voiceConnecting
                      ? "Connecting…"
                      : s.voiceConnected
                        ? "Voice live"
                        : s.statusLine}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <Link
                  to="/mentrix-home"
                  className="rounded border border-slate-700 px-2 py-1 text-[10px] text-teal-200 hover:bg-slate-900"
                  data-testid="mentrix-dock-open-hud"
                >
                  Open HUD
                </Link>
                <button
                  type="button"
                  className="rounded p-1 text-slate-400 hover:text-white"
                  aria-label="Collapse Mentrix dock"
                  onClick={() => s.setDockExpanded(false)}
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            <div className="border-b border-slate-800 px-2 py-1">
              <CompanionScopeStrip compact provenance={s.lastProvenance} progress={s.lastProgress} />
            </div>

            <div className="max-h-40 space-y-1.5 overflow-auto px-3 py-2 text-xs" data-testid="mentrix-dock-chat">
              {s.messages.slice(-8).map((m, i) => (
                <div
                  key={i}
                  className={
                    m.role === "user"
                      ? "ml-4 rounded border border-teal-900/50 bg-teal-950/40 px-2 py-1"
                      : "mr-2 rounded border border-slate-800 bg-slate-900/80 px-2 py-1"
                  }
                >
                  {m.text}
                </div>
              ))}
              {s.streamReply ? (
                <div className="mr-2 rounded border border-emerald-900 bg-slate-900/80 px-2 py-1 text-emerald-100">
                  {s.streamReply}
                </div>
              ) : null}
              <div ref={s.chatEndRef} />
            </div>

            <div className="space-y-2 border-t border-slate-800 px-3 py-2">
              <div className="flex flex-wrap items-center gap-1.5">
                <label className="inline-flex items-center gap-1 text-[10px] text-slate-400">
                  Mic
                  <select
                    data-testid="mentrix-dock-mic"
                    className="max-w-[9rem] rounded bg-slate-900 text-[10px] text-slate-100"
                    value={s.micDeviceId}
                    onChange={(e) => {
                      s.setMicDeviceId(e.target.value);
                      s.pushLog(`Mic selected: ${e.target.value.slice(0, 8)}…`);
                    }}
                  >
                    {s.micDevices.length === 0 ? (
                      <option value="">Default</option>
                    ) : (
                      s.micDevices.map((d) => (
                        <option key={d.deviceId} value={d.deviceId}>
                          {d.label}
                        </option>
                      ))
                    )}
                  </select>
                </label>
                <label className="inline-flex items-center gap-1 text-[10px] text-slate-400">
                  Skill
                  <select
                    data-testid="mentrix-dock-skill"
                    className="max-w-[8rem] rounded bg-slate-900 text-[10px] text-slate-100"
                    value={s.activeSkillId}
                    onChange={(e) => s.setActiveSkillId(e.target.value)}
                  >
                    <option value="">None</option>
                    {s.skills.map((sk) => (
                      <option key={sk.id} value={String(sk.id)}>
                        {sk.name}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  data-testid="mentrix-dock-voice"
                  disabled={
                    s.voiceConnecting || (!s.voiceConnected && s.realtimePreflight?.ready === false)
                  }
                  onClick={s.toggleVoice}
                  className={`inline-flex items-center gap-1 rounded px-2 py-1 text-[10px] font-medium disabled:opacity-50 ${
                    s.voiceConnected || s.voiceConnecting
                      ? "bg-teal-600 text-white"
                      : "border border-slate-600 text-slate-200"
                  }`}
                >
                  {s.voiceConnected || s.voiceConnecting ? (
                    <Mic className="h-3 w-3" />
                  ) : (
                    <MicOff className="h-3 w-3" />
                  )}
                  {s.voiceConnecting
                    ? "Connecting…"
                    : s.voiceConnected
                      ? "Disconnect"
                      : "Connect Voice"}
                </button>
              </div>
              <div className="flex items-end gap-1.5">
                <textarea
                  data-testid="mentrix-dock-input"
                  value={s.input}
                  onChange={(e) => s.setInput(e.target.value)}
                  rows={2}
                  placeholder="Ask Mentrix…"
                  className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-white"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      void s.onSend();
                    }
                  }}
                />
                {s.loading ? (
                  <button
                    type="button"
                    data-testid="mentrix-dock-cancel"
                    onClick={() => s.cancelTurn()}
                    className="rounded-lg border border-amber-700 px-2 py-2 text-[10px] text-amber-200"
                  >
                    Cancel
                  </button>
                ) : null}
                <button
                  type="button"
                  data-testid="mentrix-dock-send"
                  aria-label="Send message"
                  disabled={s.loading || !s.input.trim()}
                  onClick={() => void s.onSend()}
                  className="rounded-lg bg-teal-600 p-2 disabled:opacity-40"
                >
                  <Send className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        ) : (
          <button
            type="button"
            data-testid="mentrix-dock-collapsed"
            aria-expanded="false"
            aria-label="Expand Mentrix dock"
            onClick={() => s.setDockExpanded(true)}
            className="ml-auto flex items-center gap-2 rounded-full border border-teal-700/70 bg-slate-950/95 px-3 py-2 text-left shadow-xl backdrop-blur hover:border-teal-500"
          >
            <div
              className={`flex h-10 w-10 items-center justify-center rounded-full border-2 bg-gradient-to-br ${ORB[s.avatar]}`}
            >
              <Bot className="h-5 w-5 text-teal-300" />
            </div>
            <div className="pr-1">
              <p className="text-xs font-semibold text-teal-100">Mentrix</p>
              <p className="text-[10px] text-slate-400">
                {s.voiceConnected ? "Voice connected" : "Tap to expand"}
              </p>
            </div>
          </button>
        )}
      </div>

      <MentrixConfirmModal
        open={s.pending.length > 0}
        items={s.pending}
        speakPrompt={s.browserTtsEnabled}
        onAllow={s.onAllow}
        onDeny={() => {
          s.setPending([]);
          s.setAvatar("idle");
          s.setMessages((m) => [
            ...m,
            { role: "system", text: "Permission denied — Mentrix did not run those tools." },
          ]);
        }}
      />
    </>
  );
}
