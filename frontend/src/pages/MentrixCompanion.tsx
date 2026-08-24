/**
 * Mentrix Companion HUD — Chat is the personal agent; Incident / Voice are focused tools.
 * Deep links: ?incident=1 / ?voice=1.
 */
import { Link, useSearchParams } from "react-router-dom";
import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Eye,
  Maximize2,
  Mic,
  MicOff,
  Monitor,
  MoreHorizontal,
  Send,
  Sparkles,
} from "lucide-react";
import {
  mentrixCompanionPolicy,
  mentrixCompanionPolicyImport,
} from "@/lib/api";
import MentrixConfirmModal from "@/components/MentrixConfirmModal";
import MentrixArtifacts from "@/components/MentrixArtifacts";
import MentrixDesktopPanel from "@/components/MentrixDesktopPanel";
import PresentDeckPanel from "@/components/PresentDeckPanel";
import IncidentRunbookPanel from "@/components/IncidentRunbookPanel";
import CloneVoicePanel from "@/components/CloneVoicePanel";
import ModelSelector from "@/components/ModelSelector";
import CompanionScopeStrip from "@/components/CompanionScopeStrip";
import { computerTargetHint } from "@/lib/computerTarget";
import { ttsPlaybackChip } from "@/mentrix/companionChatVoice";
import { setStoredMicDeviceId, setStoredSpeakerDeviceId } from "@/lib/micDevices";
import MentrixAvatarOrb from "@/components/MentrixAvatarOrb";
import { useMentrixSession } from "@/mentrix/MentrixSessionContext";

type CompanionMode = "chat" | "incident" | "voice";

function ComputerTargetChip() {
  const [label, setLabel] = useState("Inspecting…");
  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const computer = window.zectDesktop?.mentrix?.computer;
        if (!computer) {
          if (!cancelled) setLabel("Browser only — use Electron");
          return;
        }
        const res = (await computer("ui_inspect", {})) as {
          ok?: boolean;
          allowlisted?: boolean;
          summary?: { process_name?: string; foreground_title?: string; frontmost?: string };
        };
        if (cancelled) return;
        if (!res?.ok) {
          setLabel("No foreground window");
          return;
        }
        const name =
          res.summary?.process_name ||
          res.summary?.frontmost ||
          res.summary?.foreground_title ||
          "unknown";
        setLabel(computerTargetHint(name, Boolean(res.allowlisted)));
      } catch {
        if (!cancelled) setLabel("Inspect failed");
      }
    };
    void tick();
    const id = window.setInterval(() => void tick(), 2500);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);
  return (
    <p
      className="text-[10px] text-teal-300/90 max-w-[360px] break-words"
      data-testid="computer-active-target"
      title={label}
    >
      Active: {label}
    </p>
  );
}

export default function MentrixCompanion() {
  const s = useMentrixSession();
  const [searchParams, setSearchParams] = useSearchParams();
  const [eventsOpen, setEventsOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const mode: CompanionMode =
    searchParams.get("voice") === "1"
      ? "voice"
      : searchParams.get("incident") === "1"
        ? "incident"
        : "chat";

  const setMode = (next: CompanionMode, focusTab = false) => {
    const sp = new URLSearchParams(searchParams);
    sp.delete("voice");
    sp.delete("incident");
    if (next === "voice") sp.set("voice", "1");
    if (next === "incident") sp.set("incident", "1");
    setSearchParams(sp, { replace: true });
    if (focusTab) {
      requestAnimationFrame(() => {
        document.getElementById(`mentrix-tab-${next}`)?.focus();
      });
    }
  };

  return (
    <div
      className={`flex min-h-0 flex-col overflow-hidden bg-slate-950 text-slate-100 ${
        s.displayMode ? "fixed inset-0 z-40 m-0 p-3 sm:p-4" : "h-full min-h-0 flex-1"
      }`}
      data-testid="mentrix-companion-page"
    >
      <div className="mx-auto flex h-full min-h-0 w-full max-w-7xl flex-col gap-2 p-3 sm:gap-3 sm:p-4">
        <header className="flex shrink-0 flex-wrap items-start justify-between gap-2 sm:gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-[10px] uppercase tracking-[0.25em] text-teal-500/80">Mentrix Operator</p>
            <h1 className="text-xl font-bold tracking-tight text-teal-100">MENTRIX</h1>
            <p className="text-sm text-slate-400">
              Company orchestrator — Project, WorkItem, Developer, Present, Voice, Process. Companion does not edit code or decks.
            </p>
            <div className="mt-2 max-w-3xl">
              <CompanionScopeStrip provenance={s.lastProvenance} progress={s.lastProgress} />
            </div>
            <div
              className="relative z-40 mt-3 flex flex-wrap gap-1 rounded-xl border border-slate-800 bg-slate-900/80 p-1"
              data-testid="mentrix-companion-modes"
              role="tablist"
              aria-label="Companion modes"
              onKeyDown={(e) => {
                const order = ["chat", "incident", "voice"] as const;
                const idx = order.indexOf(mode);
                if (e.key === "ArrowRight" || e.key === "ArrowDown") {
                  e.preventDefault();
                  setMode(order[(idx + 1) % order.length], true);
                } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
                  e.preventDefault();
                  setMode(order[(idx + order.length - 1) % order.length], true);
                } else if (e.key === "Home") {
                  e.preventDefault();
                  setMode("chat", true);
                } else if (e.key === "End") {
                  e.preventDefault();
                  setMode("voice", true);
                }
              }}
            >
              {(
                [
                  { id: "chat" as const, label: "Chat", icon: Sparkles },
                  { id: "incident" as const, label: "Incident", icon: AlertTriangle },
                  { id: "voice" as const, label: "Voice", icon: Mic },
                ] as const
              ).map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  type="button"
                  role="tab"
                  id={`mentrix-tab-${id}`}
                  aria-selected={mode === id}
                  aria-controls={`mentrix-panel-${id}`}
                  tabIndex={mode === id ? 0 : -1}
                  data-testid={`mentrix-mode-${id}`}
                  data-mode-alias={id === "voice" ? "mentrix-mode-voice" : undefined}
                  onClick={() => setMode(id)}
                  className={`inline-flex min-h-11 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                    mode === id
                      ? "bg-teal-800/80 text-teal-50"
                      : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {label}
                </button>
              ))}
            </div>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <button
              type="button"
              className="inline-flex min-h-11 items-center rounded-lg border border-slate-700 px-3 py-1.5"
              data-testid="mentrix-policy-export"
              onClick={async () => {
                try {
                  const pack = await mentrixCompanionPolicy();
                  await navigator.clipboard.writeText(JSON.stringify(pack, null, 2));
                  s.setStatusLine("Org policy copied");
                } catch (e) {
                  s.setStatusLine(e instanceof Error ? e.message : "Export failed");
                }
              }}
            >
              Export org policy
            </button>
            <button
              type="button"
              className="inline-flex min-h-11 items-center rounded-lg border border-slate-700 px-3 py-1.5"
              data-testid="mentrix-policy-import"
              onClick={async () => {
                const raw = window.prompt("Paste Mentrix org policy JSON");
                if (!raw?.trim()) return;
                try {
                  const pack = JSON.parse(raw);
                  const res = await mentrixCompanionPolicyImport(pack, false);
                  s.setStatusLine(`Imported ${res.imported_rules ?? 0} rules`);
                } catch (e) {
                  s.setStatusLine(e instanceof Error ? e.message : "Import failed");
                }
              }}
            >
              Import org policy
            </button>
            <Link
              to="/mentrix"
              className="inline-flex min-h-11 items-center rounded-lg border border-slate-700 px-3 py-1.5"
            >
              Mentrix Delivery
            </Link>
            <button
              type="button"
              data-testid="mentrix-companion-more"
              className="inline-flex min-h-11 items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 md:hidden"
              onClick={() => setMoreOpen(true)}
            >
              <MoreHorizontal className="h-4 w-4" />
              More
            </button>
          </div>
          {mode === "chat" && (
            <div className="hidden w-full md:block" data-testid="mentrix-desktop-launcher">
              <MentrixDesktopPanel />
            </div>
          )}
        </header>

        <div
          className={`grid min-h-0 flex-1 gap-3 ${
            mode === "chat" && (s.showArtifacts || s.displayMode)
              ? "grid-rows-[minmax(0,1fr)_auto] lg:grid-rows-1 lg:grid-cols-[minmax(0,1fr)_minmax(16rem,22rem)]"
              : "grid-cols-1"
          }`}
        >
          <section
            id={`mentrix-panel-${mode}`}
            role="tabpanel"
            aria-labelledby={`mentrix-tab-${mode}`}
            className="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-teal-900/40 bg-gradient-to-b from-slate-900 to-slate-950 p-4"
          >
            {!s.displayMode && mode === "incident" && (
              <div
                id="mentrix-incident-runbook"
                data-testid="mentrix-incident-section"
                className="space-y-3"
              >
                <IncidentRunbookPanel defaultExpanded />
              </div>
            )}
            {!s.displayMode && mode === "voice" && (
              <div
                id="mentrix-voice-cloning"
                data-testid="mentrix-voice-section"
                className="min-h-0 flex-1 space-y-3 overflow-y-auto rounded-xl border border-teal-700/60 bg-slate-950/90 p-3 shadow-lg shadow-teal-950/40"
              >
                <div className="rounded-lg border border-teal-800/50 bg-slate-900/80 p-3 space-y-2">
                  <p className="text-[10px] uppercase tracking-[0.2em] text-teal-400">Voice</p>
                  <p className="mt-1 text-xs text-slate-300">
                    Companion conversation voice is separate from presentation narration. Clone setup
                    also lives in Settings → Voice. Decks are generated on Present — this tab does not
                    replace that surface.
                  </p>
                  <dl className="grid gap-1 text-[11px] text-slate-300 sm:grid-cols-2" data-testid="mentrix-voice-roles">
                    <div>
                      <dt className="text-teal-400">Companion Voice</dt>
                      <dd>Speak replies in this HUD (default clone, then fallback).</dd>
                    </div>
                    <div>
                      <dt className="text-teal-400">Default Presentation Voice</dt>
                      <dd>Narrate / rehearse on Present uses your default clone.</dd>
                    </div>
                    <div>
                      <dt className="text-teal-400">Fallback Presentation Voice</dt>
                      <dd>Stock OpenAI voice if Voicebox is offline.</dd>
                    </div>
                    <div>
                      <dt className="text-teal-400">Auto fallback policy</dt>
                      <dd>Clone first; if Voicebox is down, stock TTS; No Narration is explicit.</dd>
                    </div>
                  </dl>
                  <div className="flex flex-wrap gap-2">
                    <a
                      href="/settings#voice"
                      className="zect-btn zect-btn-secondary text-xs"
                      data-testid="voice-open-settings"
                    >
                      Open Voice settings
                    </a>
                    <Link
                      to="/present/create"
                      className="zect-btn zect-btn-primary text-xs"
                      data-testid="mentrix-voice-handoff-present"
                    >
                      Open Present
                    </Link>
                  </div>
                </div>
                <CloneVoicePanel variant="dark" defaultExpanded />
                <div>
                  <p className="mb-2 text-[10px] uppercase tracking-[0.2em] text-teal-400">
                    Present — hand off to ZECT Present (not a second editor)
                  </p>
                  <PresentDeckPanel variant="dark" mode="companion" />
                </div>
              </div>
            )}
            {mode === "chat" && (
              <>
                <div
                  className="flex min-h-0 flex-1 flex-col overflow-hidden"
                  data-testid="mentrix-companion-scroll"
                >
                <div className={`flex shrink-0 flex-col items-center gap-1 py-1 ${s.displayMode ? "sm:py-1" : "sm:gap-2 sm:py-2"}`}>
                  <MentrixAvatarOrb state={s.avatar} compact={s.displayMode} />
                  <p
                    className="text-sm font-medium uppercase tracking-widest text-teal-200/90"
                    data-testid="mentrix-greeting"
                  >
                    Good to see you
                  </p>
                  <p className="text-xs text-slate-400" data-testid="mentrix-companion-status">
                    ● {s.statusLine}
                    {s.voiceTelemetry?.mode && s.voiceTelemetry.mode !== "idle" && (
                      <span className="ml-2 text-[10px] text-slate-400">
                        [{s.voiceTelemetry.mode}
                        {s.voiceTelemetry.lastMark
                          ? ` · ${s.voiceTelemetry.lastMark} ${s.voiceTelemetry.lastMs}ms`
                          : ""}
                        ]
                      </span>
                    )}
                    {s.runsHint ? ` · Delivery ${s.runsHint}` : ""}
                  </p>
                  <p
                    className={`text-[11px] ${s.realtimePreflight?.ready ? "text-emerald-400" : "text-amber-400"}`}
                    data-testid="mentrix-realtime-status"
                  >
                    {s.realtimePreflight === null
                      ? "Checking Realtime…"
                      : s.realtimePreflight.ready
                        ? `Realtime ready${s.realtimePreflight.model ? ` · ${s.realtimePreflight.model}` : ""}`
                        : `Realtime unavailable — ${s.realtimePreflight.reason || "check OPENAI_API_KEY"} · use typed asks or Retry`}
                  </p>
                  {s.integrations ? (
                    <p className="max-w-full truncate px-2 text-[10px] text-slate-500" data-testid="mentrix-integrations-status">
                      Mentrix Local{" "}
                      {(s.integrations as { mentrix_local?: boolean }).mentrix_local
                        ? "online"
                        : "offline"}
                      {" · OpenAI "}
                      {s.integrations.openai ? "ready" : "missing"} · Slack{" "}
                      {s.integrations.slack ? "ready" : "not set"} · Jira{" "}
                      {s.integrations.jira ? "ready" : "not set"}
                      {" · DD "}
                      {(s.integrations as { datadog?: boolean }).datadog ? "ready" : "not set"}
                      {" · GH "}
                      {(s.integrations as { github?: boolean }).github ? "ready" : "not set"}
                      {" · Browser "}
                      <span
                        data-testid="mentrix-browser-health"
                        title={
                          (s.integrations as { browser_hint?: string }).browser_hint ||
                          "Browser automation via Playwright"
                        }
                      >
                        {(s.integrations as { browser?: boolean }).browser ? "online" : "offline"}
                      </span>
                      {" · Skill "}
                      {s.activeSkillId
                        ? s.skills.find((sk) => String(sk.id) === s.activeSkillId)?.name ||
                          `#${s.activeSkillId}`
                        : "None"}
                    </p>
                  ) : null}
                  <div className="mt-2 flex flex-wrap justify-center gap-2">
                    <label className="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 px-2 py-1.5 text-xs">
                      <span className="text-slate-400">Mic</span>
                      <select
                        data-testid="mentrix-mic-select"
                        className="max-w-[180px] rounded bg-slate-900 text-slate-100"
                        value={s.micDeviceId}
                        onChange={(e) => {
                          const id = e.target.value;
                          s.setMicDeviceId(id);
                          setStoredMicDeviceId(id);
                          s.pushLog(
                            `Mic selected: ${s.micDevices.find((d) => d.deviceId === id)?.label || id}`,
                          );
                        }}
                      >
                        {s.micDevices.length === 0 ? (
                          <option value="">Default microphone</option>
                        ) : (
                          s.micDevices.map((d) => (
                            <option key={d.deviceId} value={d.deviceId}>
                              {d.label}
                            </option>
                          ))
                        )}
                      </select>
                    </label>
                    <label className="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 px-2 py-1.5 text-xs">
                      <span className="text-slate-400">Speakers</span>
                      <select
                        data-testid="mentrix-speaker-select"
                        className="max-w-[180px] rounded bg-slate-900 text-slate-100"
                        value={s.speakerDeviceId}
                        onChange={(e) => {
                          const id = e.target.value;
                          s.setSpeakerDeviceId(id);
                          setStoredSpeakerDeviceId(id);
                          s.pushLog(
                            `Speakers selected: ${s.speakerDevices.find((d) => d.deviceId === id)?.label || id || "default"}`,
                          );
                        }}
                      >
                        <option value="">Default speakers</option>
                        {s.speakerDevices.map((d) => (
                          <option key={d.deviceId} value={d.deviceId}>
                            {d.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 px-2 py-1.5 text-xs">
                      <span className="text-slate-400">Skill</span>
                      <select
                        data-testid="mentrix-active-skill"
                        className="max-w-[140px] rounded bg-slate-900 text-slate-100"
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
                    <div
                      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 px-2 py-1.5 text-xs [&_select]:bg-slate-900 [&_select]:text-slate-100 [&_select]:border-0"
                      data-testid="mentrix-chat-model"
                    >
                      <span className="text-slate-400">Model</span>
                      <ModelSelector
                        value={s.chatModel}
                        onChange={s.setChatModel}
                        compact
                        showGatewayChip
                      />
                    </div>
                    <button
                      type="button"
                      data-testid="mentrix-connect-voice"
                      onClick={s.toggleVoice}
                      disabled={
                        s.voiceConnecting ||
                        (!s.voiceConnected && s.realtimePreflight?.ready === false)
                      }
                      className={`inline-flex min-h-11 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium disabled:opacity-50 ${
                        s.voiceConnected || s.voiceConnecting
                          ? "bg-teal-600 text-white"
                          : "border border-slate-600 text-slate-200"
                      }`}
                    >
                      {s.voiceConnected || s.voiceConnecting ? (
                        <Mic className="h-3.5 w-3.5" />
                      ) : (
                        <MicOff className="h-3.5 w-3.5" />
                      )}
                      {s.voiceConnecting
                        ? "Connecting…"
                        : s.voiceConnected
                          ? "Disconnect Voice"
                          : "Connect Voice"}
                    </button>
                    <p
                      className="hidden basis-full px-1 text-[10px] text-slate-500 2xl:block"
                      data-testid="mentrix-skills-model-hud"
                    >
                      Skill dropdown = playbook context · Model = chat LLM · Connect Voice = OpenAI
                      Realtime mic · Local LLM chip = offline gateway (not the same as Realtime).
                    </p>
                    {!s.realtimePreflight?.ready && s.realtimePreflight !== null ? (
                      <button
                        type="button"
                        data-testid="mentrix-realtime-retry"
                        onClick={() => void s.refreshRealtimePreflight()}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-amber-700 px-3 py-1.5 text-xs text-amber-200"
                      >
                        Retry Realtime
                      </button>
                    ) : null}
                    <button
                      type="button"
                      data-testid="mentrix-display-mode"
                      onClick={() => s.setDisplayMode((d) => !d)}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 px-3 py-1.5 text-xs"
                    >
                      <Eye className="h-3.5 w-3.5" />
                      Display
                    </button>
                    <label className="inline-flex min-h-11 items-center gap-1.5 rounded-lg border border-slate-600 px-3 py-1.5 text-xs">
                      <input
                        type="checkbox"
                        checked={s.computerMode}
                        data-testid="mentrix-computer-mode"
                        onChange={async (e) => {
                          const on = e.target.checked;
                          if (on) {
                            const ok = window.confirm(
                              "Enable Mentrix Computer Mode? Allowlisted apps/screenshots only after each confirm.",
                            );
                            if (!ok) return;
                          }
                          s.setComputerMode(on);
                          await window.zectDesktop?.mentrix?.setComputerMode?.(on);
                          s.pushLog(`Computer Mode ${on ? "ON" : "OFF"}`);
                        }}
                      />
                      <Monitor className="h-3.5 w-3.5" />
                      Computer Mode
                    </label>
                    {s.computerMode ? (
                      <ComputerTargetChip />
                    ) : null}
                    <p className="max-w-[280px] text-[10px] text-slate-500" data-testid="computer-mode-hint">
                      Desktop folders and clicks require Electron + Computer Mode ON (allowlisted apps /
                      notes / Present Deck only — never delete). Organize files uses File Organize.
                    </p>
                    {!s.computerMode ? (
                      <p className="max-w-[280px] text-[10px] text-amber-400" data-testid="computer-mode-mkdir-blocked">
                        Computer Mode is off — desktop_mkdir is blocked until you enable it and confirm.
                      </p>
                    ) : null}
                    <button
                      type="button"
                      data-testid="mentrix-artifacts-toggle"
                      onClick={() => s.setShowArtifacts((x) => !x)}
                      className="inline-flex min-h-11 items-center gap-1.5 rounded-lg border border-slate-600 px-3 py-1.5 text-xs"
                    >
                      <Sparkles className="h-3.5 w-3.5" />
                      Artifacts
                    </button>
                  </div>
                </div>

                <div className="shrink-0 border-t border-slate-800 pt-1">
                  <button
                    type="button"
                    data-testid="mentrix-events-toggle"
                    onClick={() => setEventsOpen((o) => !o)}
                    className="rounded px-1 py-0.5 text-[10px] uppercase tracking-wide text-slate-500 hover:text-teal-300"
                  >
                    {eventsOpen ? "Hide events" : "Events"}
                  </button>
                  {eventsOpen ? (
                    <div
                      className="mt-1 max-h-24 space-y-1 overflow-y-auto overscroll-contain text-[11px] text-slate-400"
                      data-testid="mentrix-live-log"
                    >
                      {s.log.length === 0 && <p>Live log — tool events stream here</p>}
                      {s.log.map((l, i) => (
                        <div key={i} className="break-words whitespace-pre-wrap">
                          <span className="text-teal-700">{l.ts}</span> {l.text}
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>

                <div
                  className="mt-2 min-h-[12rem] flex-1 space-y-2 overflow-y-auto overscroll-contain border-t border-slate-800 pt-2"
                  data-testid="mentrix-companion-chat"
                >
                  {s.messages.map((m, i) => (
                    <div
                      key={i}
                      className={
                        m.role === "user"
                          ? "ml-6 rounded-lg border border-teal-800 bg-teal-950/40 px-3 py-2 text-sm break-words whitespace-pre-wrap"
                          : "mr-6 rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-2 text-sm break-words whitespace-pre-wrap"
                      }
                    >
                      {m.text}
                    </div>
                  ))}
                  {s.streamReply ? (
                    <div className="mr-6 rounded-lg border border-emerald-900 bg-slate-900/80 px-3 py-2 text-sm text-emerald-100 break-words whitespace-pre-wrap">
                      {s.streamReply}
                    </div>
                  ) : null}
                  <div ref={s.chatEndRef} />
                </div>
                <p className="mt-2 hidden text-[11px] text-slate-500 2xl:block">
                  Chat is the personal agent. Use{" "}
                  <button type="button" className="underline text-teal-400" onClick={() => setMode("incident")}>
                    Incident
                  </button>{" "}
                  for runbooks or{" "}
                  <button type="button" className="underline text-teal-400" onClick={() => setMode("voice")}>
                    Voice
                  </button>{" "}
                  for ZECT Voicebox clone + Present Deck.
                </p>
                {s.displayMode && (
                  <div className="mt-2 text-[10px] text-teal-500/80">Present mode uses fullscreen artifacts</div>
                )}
                </div>
                <div
                  className="relative z-20 shrink-0 border-t border-slate-800 bg-slate-950 pt-2"
                  data-testid="mentrix-companion-composer"
                >
                <div className="mt-0 flex min-w-0 items-end gap-2">
                  <textarea
                    data-testid="mentrix-companion-input"
                    value={s.input}
                    onChange={(e) => s.setInput(e.target.value)}
                    rows={2}
                    placeholder="Ask Mentrix…"
                    autoComplete="off"
                    className="relative z-20 min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white pointer-events-auto"
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
                      data-testid="mentrix-companion-cancel"
                      onClick={() => s.cancelTurn()}
                      className="shrink-0 rounded-lg border border-amber-700 px-3 py-2.5 text-xs text-amber-200"
                    >
                      Cancel
                    </button>
                  ) : null}
                  {!s.loading && s.lastMessage ? (
                    <button
                      type="button"
                      data-testid="mentrix-companion-retry"
                      onClick={() => s.retryTurn()}
                      className="shrink-0 rounded-lg border border-slate-600 px-3 py-2.5 text-xs"
                    >
                      Retry
                    </button>
                  ) : null}
                  <button
                    type="button"
                    data-testid="mentrix-companion-send"
                    disabled={s.loading || !s.input.trim()}
                    onClick={() => void s.onSend()}
                    className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg bg-teal-600 p-2.5 disabled:opacity-40"
                  >
                    <Send className="h-5 w-5" />
                  </button>
                </div>
                <label className="mt-2 inline-flex items-center gap-2 text-xs text-slate-500">
                  <input
                    type="checkbox"
                    data-testid="mentrix-tts-toggle"
                    checked={s.tts}
                    onChange={(e) => s.setTts(e.target.checked)}
                  />
                  Speak replies (TTS) — uses your cloned voice when set. Uncheck if you hear two voices.
                  <span
                    className="rounded border border-slate-700 px-1.5 py-0.5 text-[10px] uppercase text-teal-300"
                    data-testid="mentrix-tts-playback"
                  >
                    {ttsPlaybackChip({
                      ttsEnabled: s.tts,
                      ttsPlayback: s.ttsPlayback,
                      voiceConnected: s.voiceConnected,
                    })}
                  </span>
                </label>
                <div className="mt-2 flex flex-wrap gap-2">
                  <button
                    type="button"
                    data-testid="mentrix-present-narrate"
                    className="inline-flex min-h-11 items-center rounded-lg border border-teal-700 px-3 py-1.5 text-xs text-teal-200 hover:bg-teal-950"
                    onClick={() => void s.presentNarrate?.()}
                  >
                    Present / Narrate
                  </button>
                </div>
                <p
                  data-testid="mentrix-present-hint"
                  className="mt-1.5 text-[11px] text-slate-500"
                >
                  Uses Mentrix Board artifacts + your default ZECT Voicebox voice (not PowerPoint files).
                  For decks, open{" "}
                  <Link to="/present" className="text-teal-400 underline" data-testid="mentrix-present-decks-link">
                    Present
                  </Link>
                  .
                </p>
                </div>
              </>
            )}
            {mode === "chat" && s.displayMode ? (
              <p className="shrink-0 text-[10px] text-teal-500/80">Display keeps Chat visible — artifacts are the side pane.</p>
            ) : null}
          </section>

          {mode === "chat" && (s.showArtifacts || s.displayMode) && (
            <aside
              className="relative z-10 flex min-h-[9rem] flex-col space-y-3 overflow-y-auto rounded-2xl border border-teal-900/40 bg-slate-900/80 p-4 max-lg:max-h-[40vh] max-lg:rounded-t-2xl lg:h-full lg:min-h-0"
              data-testid="mentrix-companion-artifacts"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 font-semibold text-teal-200">
                  <Sparkles className="h-4 w-4" />
                  ARTIFACTS
                </div>
                <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="text-xs text-slate-400 hover:text-teal-300 lg:hidden"
                  title="Close artifacts"
                  data-testid="mentrix-artifacts-close"
                  onClick={() => s.setShowArtifacts(false)}
                >
                  Close
                </button>
                <button
                  type="button"
                  className="text-slate-400 hover:text-teal-300"
                  title="Fullscreen artifacts"
                  onClick={() => s.setDisplayMode(true)}
                >
                  <Maximize2 className="h-4 w-4" />
                </button>
                {s.displayMode ? (
                  <>
                    <button
                      type="button"
                      data-testid="mentrix-present-narrate-display"
                      className="rounded border border-teal-600 px-2 py-1 text-[10px] text-teal-200"
                      onClick={() => void s.presentNarrate?.()}
                    >
                      Narrate
                    </button>
                    <button
                      type="button"
                      className="rounded border border-slate-600 px-2 py-1 text-[10px]"
                      onClick={() => s.setDisplayMode(false)}
                    >
                      Hide
                    </button>
                  </>
                ) : null}
                </div>
              </div>
              <MentrixArtifacts items={s.board} displayMode={s.displayMode} />
              <div className="space-y-1 border-t border-slate-800 pt-3 text-xs text-slate-400">
                <p className="font-semibold text-slate-200">Quick asks</p>
                {[
                  "What's my Mentrix Delivery status?",
                  "What's the weather in Austin?",
                  "Slack digest",
                  "Check my email",
                  "Show connector architecture",
                  "Is the coding engine ready?",
                  "Open Lattice",
                  "Open Sandbox",
                  "Research latest on AI marketing",
                  "Draft a content brief for Q3 launch",
                  "Diagnose why this is failing",
                  "Add note: hello from Mentrix",
                  "Generate image: Mentrix operator thumbnail",
                  "Go back",
                ].map((q) => (
                  <button
                    key={q}
                    type="button"
                    className="block w-full rounded border border-slate-800 px-2 py-1.5 text-left hover:bg-teal-950/50"
                    onClick={() => {
                      s.setLastMessageKeep(q);
                      void s.runTurn(q);
                    }}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </aside>
          )}
        </div>
      </div>

      {moreOpen ? (
        <div
          className="fixed inset-0 z-50 md:hidden"
          data-testid="mentrix-companion-more-sheet"
        >
          <button
            type="button"
            className="absolute inset-0 bg-black/60"
            aria-label="Close more"
            onClick={() => setMoreOpen(false)}
          />
          <div className="absolute inset-x-0 bottom-0 max-h-[80vh] space-y-3 overflow-y-auto rounded-t-2xl border border-teal-900/40 bg-slate-900 p-4">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wide text-teal-200">More</p>
              <button
                type="button"
                className="inline-flex min-h-11 items-center rounded-lg border border-slate-700 px-3 text-xs"
                data-testid="mentrix-companion-more-close"
                onClick={() => setMoreOpen(false)}
              >
                Close
              </button>
            </div>
            <div data-testid="mentrix-desktop-launcher-sheet">
              <MentrixDesktopPanel />
            </div>
            <p className="text-[11px] text-slate-500">
              Phone-thin chat also lives at <Link to="/m/companion" className="text-teal-400 underline">/m/companion</Link>.
              This HUD is the full Companion for mobile browsers.
            </p>
          </div>
        </div>
      ) : null}

      <MentrixConfirmModal
        open={s.pending.length > 0}
        items={s.pending}
        speakPrompt={false}
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
    </div>
  );
}
