/**
 * Mentrix Companion HUD — streaming operator shell (orb, voice, artifacts, computer mode).
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Bot,
  Eye,
  Maximize2,
  Mic,
  MicOff,
  Monitor,
  Send,
  Sparkles,
} from "lucide-react";
import {
  mentrixCompanionIntegrations,
  mentrixCompanionPolicy,
  mentrixCompanionPolicyImport,
  mentrixCompanionStream,
  mentrixCompanionStreamResume,
  mentrixCompanionTurn,
  mentrixListRuns,
  type MentrixStreamEvent,
} from "@/lib/api";
import MentrixConfirmModal, { type PendingConfirm } from "@/components/MentrixConfirmModal";
import MentrixArtifacts, { type ArtifactItem } from "@/components/MentrixArtifacts";
import MentrixDesktopPanel from "@/components/MentrixDesktopPanel";
import {
  probeMentrixRealtimePreflight,
  startMentrixRealtime,
  confirmRealtimeTools,
  type RealtimePreflight,
  type RealtimeSessionHandle,
} from "@/lib/mentrixRealtime";
import {
  ensureMicPermission,
  getStoredMicDeviceId,
  listMicDevices,
  setStoredMicDeviceId,
  type MicDevice,
} from "@/lib/micDevices";

type AvatarState = "idle" | "listening" | "thinking" | "speaking" | "working" | "needs_permission";
type ChatMsg = { role: "user" | "assistant" | "system"; text: string };
type LogLine = { ts: string; text: string };

function speak(text: string, enabled: boolean) {
  if (!enabled || typeof window === "undefined" || !window.speechSynthesis) return;
  try {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text.slice(0, 500));
    u.rate = 1.05;
    window.speechSynthesis.speak(u);
  } catch {
    /* ignore — Realtime voice replies use OpenAI audio, not browser TTS */
  }
}

const ORB: Record<AvatarState, string> = {
  idle: "from-slate-800 to-slate-950 border-slate-500 shadow-slate-700/40",
  listening: "from-teal-900 to-slate-950 border-teal-400 shadow-teal-500/50 animate-pulse",
  thinking: "from-amber-950 to-slate-950 border-amber-400 shadow-amber-500/40 animate-pulse",
  speaking: "from-emerald-950 to-slate-950 border-emerald-400 shadow-emerald-500/50",
  working: "from-sky-950 to-slate-950 border-sky-400 shadow-sky-500/40 animate-pulse",
  needs_permission: "from-amber-950 to-slate-950 border-amber-500 shadow-amber-600/60",
};

function applyNav(path: string | null | undefined, navigate: (to: number | string) => void) {
  if (!path) return;
  if (path === "__back__") {
    navigate(-1);
    return;
  }
  try {
    navigate(path);
  } catch {
    window.location.assign(path);
  }
}

export default function MentrixCompanion() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<ChatMsg[]>([
    {
      role: "assistant",
      text: "I'm Mentrix — your company operator. Ask for status, research, notes, Delivery, or say Open Lattice.",
    },
  ]);
  const [input, setInput] = useState("");
  const [avatar, setAvatar] = useState<AvatarState>("idle");
  const [board, setBoard] = useState<ArtifactItem[]>([]);
  const [log, setLog] = useState<LogLine[]>([]);
  const [statusLine, setStatusLine] = useState("SYSTEMS OPERATIONAL");
  const [tts, setTts] = useState(true);
  const [voiceConnected, setVoiceConnected] = useState(false);
  const [voiceConnecting, setVoiceConnecting] = useState(false);
  const [computerMode, setComputerMode] = useState(false);
  const [displayMode, setDisplayMode] = useState(false);
  const [showArtifacts, setShowArtifacts] = useState(true);
  const [pending, setPending] = useState<PendingConfirm[]>([]);
  const [turnId, setTurnId] = useState("");
  const [loading, setLoading] = useState(false);
  const [runsHint, setRunsHint] = useState("");
  const [streamReply, setStreamReply] = useState("");
  const [lastMessage, setLastMessageKeep] = useState("");
  const [realtimePreflight, setRealtimePreflight] = useState<RealtimePreflight | null>(null);
  const [micDevices, setMicDevices] = useState<MicDevice[]>([]);
  const [micDeviceId, setMicDeviceId] = useState(() => getStoredMicDeviceId());
  const [integrations, setIntegrations] = useState<{
    slack: boolean;
    jira: boolean;
    openai: boolean;
  } | null>(null);
  const realtimeRef = useRef<RealtimeSessionHandle | null>(null);
  const voiceConnectingRef = useRef(false);
  const micDeviceIdRef = useRef(micDeviceId);
  micDeviceIdRef.current = micDeviceId;
  const pendingArgsRef = useRef<Record<string, Record<string, unknown>>>({});
  const chatEnd = useRef<HTMLDivElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const runTurnRef = useRef<(message: string, confirmed?: string[], resumeId?: string) => Promise<void>>();

  const pushLog = useCallback((text: string) => {
    const ts = new Date().toLocaleTimeString();
    setLog((l) => [{ ts, text }, ...l].slice(0, 80));
  }, []);

  useEffect(() => {
    chatEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamReply]);

  useEffect(() => {
    document.body.dataset.mentrixHud = "1";
    return () => {
      delete document.body.dataset.mentrixHud;
    };
  }, []);

  useEffect(() => {
    mentrixListRuns(3)
      .then((runs) => {
        if (Array.isArray(runs) && runs[0]) {
          setRunsHint(`#${runs[0].id} ${runs[0].status}`);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    probeMentrixRealtimePreflight()
      .then(setRealtimePreflight)
      .catch(() => setRealtimePreflight({ ready: false, reason: "probe_failed" }));
    mentrixCompanionIntegrations()
      .then((s) => setIntegrations({ slack: !!s.slack, jira: !!s.jira, openai: !!s.openai }))
      .catch(() => setIntegrations(null));
    void (async () => {
      await ensureMicPermission();
      const devices = await listMicDevices();
      setMicDevices(devices);
      const stored = getStoredMicDeviceId();
      if (stored && devices.some((d) => d.deviceId === stored)) {
        setMicDeviceId(stored);
      } else if (!stored && devices[0]?.deviceId) {
        setMicDeviceId(devices[0].deviceId);
        setStoredMicDeviceId(devices[0].deviceId);
      }
    })();
  }, []);

  const refreshRealtimePreflight = useCallback(async () => {
    try {
      const pf = await probeMentrixRealtimePreflight();
      setRealtimePreflight(pf);
      return pf;
    } catch {
      const pf = { ready: false, reason: "probe_failed" } as RealtimePreflight;
      setRealtimePreflight(pf);
      return pf;
    }
  }, []);

  const stopVoiceSession = useCallback(() => {
    try {
      realtimeRef.current?.stop();
    } catch {
      /* ignore */
    }
    realtimeRef.current = null;
    voiceConnectingRef.current = false;
    setVoiceConnecting(false);
    setVoiceConnected(false);
    setAvatar("idle");
  }, []);

  const startVoiceSession = useCallback(async () => {
    // Hard lock — ignore wake + double-clicks while connecting or already live.
    if (voiceConnectingRef.current) {
      pushLog("Connect Voice — already connecting (ignored)");
      return;
    }
    if (realtimeRef.current) {
      pushLog("Connect Voice — already connected (ignored)");
      return;
    }
    voiceConnectingRef.current = true;
    setVoiceConnecting(true);
    setAvatar("listening");
    setStatusLine("Connect Voice…");
    try {
      // Always remint — reusing ephemeral client_secret after disconnect causes blank/WS failures.
      const preflight = await refreshRealtimePreflight();
      if (!preflight?.ready || !preflight.client_secret) {
        setVoiceConnected(false);
        setAvatar("idle");
        setStatusLine(`Realtime unavailable — ${preflight?.reason || "check OPENAI_API_KEY"}`);
        pushLog(`realtime_unavailable ${preflight?.reason || "unknown"}`);
        return;
      }
      const handle = await startMentrixRealtime({
        skipRealtime: false,
        // Mint already done above; client remints again inside unless forceReuse.
        forceReusePreflight: true,
        preflight,
        deviceId: micDeviceIdRef.current || undefined,
        handlers: {
          onOrb: (s) => setAvatar(s as AvatarState),
          onLog: pushLog,
          onTranscript: (role, text) => {
            if (!text?.trim()) return;
            setMessages((m) => [...m, { role, text }]);
            if (role === "user") setLastMessageKeep(text);
          },
          onNavigate: (path) => applyNav(path, navigate as any),
          onArtifact: (item) => setBoard((b) => [item as ArtifactItem, ...b].slice(0, 16)),
          onPendingConfirm: (pendingList) => {
            const mapped = pendingList.map((p) => {
              const tool = String(p.tool || "");
              const fullArgs = (p.args as Record<string, unknown>) || {};
              const redacted =
                (p.args_redacted as Record<string, unknown>) ||
                Object.fromEntries(
                  Object.entries(fullArgs).map(([k, v]) => [
                    k,
                    k === "text" || k === "body" || k === "path" ? "…" : v,
                  ]),
                );
              pendingArgsRef.current[tool] = fullArgs;
              return {
                tool,
                action: String(p.action || p.tool || ""),
                args: fullArgs,
                args_redacted: redacted,
                reason: String(p.reason || "Allow required"),
              };
            });
            setPending(mapped);
            setAvatar("needs_permission");
            speak("I need your permission to continue.", tts);
          },
          onError: (err) => pushLog(`realtime ${err}`),
          onFallback: (reason) => {
            pushLog(`realtime_unavailable ${reason}`);
            try {
              realtimeRef.current?.stop();
            } catch {
              /* ignore */
            }
            realtimeRef.current = null;
            setVoiceConnected(false);
            setAvatar("idle");
            setStatusLine(`Realtime unavailable — ${reason}. Use typed Quick asks or Retry.`);
          },
        },
      });
      if (handle.mode !== "realtime") {
        setVoiceConnected(false);
        setAvatar("idle");
        return;
      }
      realtimeRef.current = handle;
      // Keep Connecting… until mic is actually open (prevents double-start race).
      const ok = await handle.ready;
      if (!ok || realtimeRef.current !== handle) {
        try {
          handle.stop();
        } catch {
          /* ignore */
        }
        if (realtimeRef.current === handle) realtimeRef.current = null;
        setVoiceConnected(false);
        setAvatar("idle");
        setStatusLine("Connect Voice failed — Retry");
        return;
      }
      setVoiceConnected(true);
      setStatusLine("Realtime voice connected — speak naturally");
    } catch (e) {
      pushLog(`Connect Voice failed: ${e instanceof Error ? e.message : "error"}`);
      stopVoiceSession();
      setStatusLine("Connect Voice failed — Retry");
    } finally {
      voiceConnectingRef.current = false;
      setVoiceConnecting(false);
    }
  }, [navigate, pushLog, refreshRealtimePreflight, stopVoiceSession, tts]);

  useEffect(() => {
    const desktop = window.zectDesktop?.mentrix;
    const unsubs: Array<() => void> = [];
    if (desktop?.onWake) {
      unsubs.push(
        desktop.onWake(() => {
          setAvatar("listening");
          pushLog("Wake — Connect Voice (Realtime)");
          void startVoiceSession();
        }),
      );
    }
    if (desktop?.onComputerMode) {
      unsubs.push(
        desktop.onComputerMode((p) => {
          if (p?.computerMode === false) {
            setComputerMode(false);
            setStatusLine(
              p.reason === "idle_auto_off" ? "Computer Mode auto-off" : "Computer Mode OFF",
            );
          }
        }),
      );
    }
    const onDom = () => {
      setAvatar("listening");
      void startVoiceSession();
    };
    window.addEventListener("mentrix-wake", onDom);
    return () => {
      unsubs.forEach((u) => u());
      window.removeEventListener("mentrix-wake", onDom);
    };
  }, [pushLog, startVoiceSession]);

  const handleStreamEvent = useCallback(
    (ev: MentrixStreamEvent) => {
      if (ev.turn_id) setTurnId(ev.turn_id);
      const d = ev.data || {};
      switch (ev.event) {
        case "thinking":
          setAvatar("thinking");
          setStatusLine("Mentrix thinking…");
          pushLog("thinking");
          break;
        case "tool_start":
          setAvatar("working");
          pushLog(`Tool: ${d.tool}`);
          break;
        case "tool_end":
          pushLog(`Tool end: ${d.tool} ${d.ok ? "ok" : d.error || "fail"}`);
          break;
        case "artifact":
          setBoard((b) => [d as ArtifactItem, ...b].slice(0, 16));
          pushLog(`Artifact: ${d.title || d.type || "item"}`);
          break;
        case "navigate":
          applyNav(d.path, navigate as any);
          pushLog(`Navigate ${d.path}`);
          break;
        case "pending_confirm":
          setAvatar("needs_permission");
          setPending((p) => {
            if (p.some((x) => x.tool === d.tool)) return p;
            return [...p, { tool: d.tool, args: d.args, reason: d.reason }];
          });
          setStatusLine("Waiting for Allow");
          break;
        case "token":
          setStreamReply((r) => r + (d.text || ""));
          setAvatar("speaking");
          break;
        case "done": {
          const reply = d.reply || "";
          setStreamReply("");
          setMessages((m) => [...m, { role: "assistant", text: reply || "Done." }]);
          if (d.board?.length) setBoard((b) => [...d.board, ...b].slice(0, 16));
          if (d.navigate) applyNav(d.navigate, navigate as any);
          if (d.pending_confirmations?.length) {
            setPending(d.pending_confirmations);
            setAvatar("needs_permission");
          } else {
            setAvatar("speaking");
            speak(reply, tts);
          }
          setStatusLine(d.latency_mode === "fast_tools" ? "Replied (instant)" : "SYSTEMS OPERATIONAL");
          pushLog(`done ${d.latency_ms || 0}ms`);
          // Desktop computer acts from tools in done path via turn fallback tools — handled when streaming tool_end with desktop
          break;
        }
        case "error":
          setMessages((m) => [...m, { role: "assistant", text: d.error || "Stream error" }]);
          setAvatar("idle");
          pushLog(`error ${d.error}`);
          break;
        default:
          break;
      }
    },
    [navigate, pushLog, tts],
  );

  const runTurn = useCallback(
    async (message: string, confirmed: string[] = [], resumeId = "") => {
      setLoading(true);
      setAvatar(confirmed.length ? "working" : "thinking");
      setStatusLine("Mentrix thinking…");
      setStreamReply("");
      if (!confirmed.length && !resumeId) {
        setMessages((m) => {
          if (m[m.length - 1]?.role === "user" && m[m.length - 1]?.text === message) return m;
          return [...m, { role: "user", text: message }];
        });
      }
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      const kill = window.setTimeout(() => controller.abort(), 45_000);
      try {
        if (resumeId) {
          await mentrixCompanionStreamResume(resumeId, confirmed, {
            signal: controller.signal,
            onEvent: handleStreamEvent,
          });
        } else {
          try {
            await mentrixCompanionStream(message, {
              project_key: localStorage.getItem("zect_lattice_key") || "",
              confirmed_tools: confirmed,
              signal: controller.signal,
              onEvent: handleStreamEvent,
            });
          } catch {
            // Fallback to non-stream turn
            const res = await mentrixCompanionTurn(message, {
              confirmed_tools: confirmed,
              project_key: localStorage.getItem("zect_lattice_key") || "",
              signal: controller.signal,
            });
            if (res.navigate) applyNav(res.navigate, navigate as any);
            if (res.pending_confirmations?.length) {
              setPending(res.pending_confirmations);
              setTurnId(res.turn_id || "");
              setLastMessageKeep(message);
              setAvatar("needs_permission");
              speak("I need your permission to continue.", tts);
            } else {
              setPending([]);
              setMessages((m) => [...m, { role: "assistant", text: res.reply || "Done." }]);
              if (res.board?.length) setBoard((b) => [...res.board, ...b].slice(0, 16));
              setAvatar("speaking");
              speak(res.reply || "", tts);
            }
            // Desktop tools
            for (const t of res.tools || []) {
              if (t.result?.desktop && !t.denied && computerMode) {
                await window.zectDesktop?.mentrix?.computer?.(t.result.desktop, {
                  ...t.result,
                  app: t.result.app,
                  path: t.result.path,
                });
              }
            }
          }
        }
      } catch (e) {
        const msg =
          e instanceof Error && e.name === "AbortError"
            ? "Mentrix timed out — try a shorter ask."
            : e instanceof Error
              ? e.message
              : "Companion turn failed";
        setMessages((m) => [...m, { role: "assistant", text: msg }]);
        setAvatar("idle");
      } finally {
        window.clearTimeout(kill);
        setLoading(false);
        setTimeout(() => setAvatar((a) => (a === "speaking" ? "idle" : a)), 2200);
      }
    },
    [computerMode, handleStreamEvent, navigate, tts],
  );

  runTurnRef.current = runTurn;

  const onSend = async () => {
    const msg = input.trim();
    if (!msg || loading) return;
    setInput("");
    setLastMessageKeep(msg);
    await runTurn(msg);
  };

  const onAllow = async (tools: string[]) => {
    setPending([]);
    const msg = lastMessage || input;
    if (realtimeRef.current?.mode === "realtime") {
      const outputs = await confirmRealtimeTools(
        tools,
        pendingArgsRef.current,
        {
          onNavigate: (path) => applyNav(path, navigate as any),
          onArtifact: (item) => setBoard((b) => [item as ArtifactItem, ...b].slice(0, 16)),
          onLog: pushLog,
          onOrb: (s) => setAvatar(s as AvatarState),
        },
      );
      const summary = outputs.map((o) => {
        try {
          const j = JSON.parse(o);
          return j.spoken_summary || j.note || o.slice(0, 120);
        } catch {
          return o.slice(0, 120);
        }
      }).join(" ");
      realtimeRef.current.resumeAfterTool(summary || "Done.");
      setAvatar("speaking");
      return;
    }
    if (turnId) {
      await runTurn(msg, tools, turnId);
    } else {
      await runTurn(msg, tools);
    }
  };

  const toggleVoice = () => {
    if (voiceConnectingRef.current) return;
    if (voiceConnected || realtimeRef.current) {
      stopVoiceSession();
      setStatusLine("Voice disconnected");
      pushLog("Voice disconnected");
      return;
    }
    void startVoiceSession();
  };

  useEffect(() => {
    return () => {
      stopVoiceSession();
    };
  }, [stopVoiceSession]);

  return (
    <div
      className={`-m-4 md:-m-6 min-h-[calc(100vh-4rem)] bg-slate-950 text-slate-100 ${displayMode ? "fixed inset-0 z-40 m-0 p-4" : ""}`}
      data-testid="mentrix-companion-page"
    >
      <div className="mx-auto flex h-full max-w-7xl flex-col gap-3 p-4">
        <header className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[10px] uppercase tracking-[0.25em] text-teal-500/80">Mentrix Operator</p>
            <h1 className="text-3xl font-bold tracking-tight text-teal-100">MENTRIX</h1>
            <p className="text-sm text-slate-400">
              Company personal agent — research, content, reporting, docs, Delivery
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <button
              type="button"
              className="rounded-lg border border-slate-700 px-3 py-1.5"
              data-testid="mentrix-policy-export"
              onClick={async () => {
                try {
                  const pack = await mentrixCompanionPolicy();
                  await navigator.clipboard.writeText(JSON.stringify(pack, null, 2));
                  setStatusLine("Org policy copied");
                } catch (e) {
                  setStatusLine(e instanceof Error ? e.message : "Export failed");
                }
              }}
            >
              Export org policy
            </button>
            <button
              type="button"
              className="rounded-lg border border-slate-700 px-3 py-1.5"
              data-testid="mentrix-policy-import"
              onClick={async () => {
                const raw = window.prompt("Paste Mentrix org policy JSON");
                if (!raw?.trim()) return;
                try {
                  const pack = JSON.parse(raw);
                  const res = await mentrixCompanionPolicyImport(pack, false);
                  setStatusLine(`Imported ${res.imported_rules ?? 0} rules`);
                } catch (e) {
                  setStatusLine(e instanceof Error ? e.message : "Import failed");
                }
              }}
            >
              Import org policy
            </button>
            <Link to="/mentrix" className="rounded-lg border border-slate-700 px-3 py-1.5">
              Mentrix Delivery
            </Link>
          </div>
          <MentrixDesktopPanel />
        </header>

        <div className={`grid flex-1 gap-3 ${showArtifacts && !displayMode ? "lg:grid-cols-[1fr_380px]" : "grid-cols-1"}`}>
          <section className="flex flex-col rounded-2xl border border-teal-900/40 bg-gradient-to-b from-slate-900 to-slate-950 p-4">
            {!displayMode && (
              <>
                <div className="flex flex-col items-center gap-2 py-4">
                  <div
                    data-testid="mentrix-avatar"
                    data-state={avatar}
                    className={`flex h-40 w-40 items-center justify-center rounded-full border-4 bg-gradient-to-br shadow-2xl ${ORB[avatar]}`}
                  >
                    <Bot className="h-16 w-16 text-teal-300" />
                  </div>
                  <p className="text-sm font-medium uppercase tracking-widest text-teal-200/90">Good to see you</p>
                  <p className="text-xs text-slate-400" data-testid="mentrix-companion-status">
                    ● {statusLine}
                    {runsHint ? ` · Delivery ${runsHint}` : ""}
                  </p>
                  <p
                    className={`text-[11px] ${realtimePreflight?.ready ? "text-emerald-400" : "text-amber-400"}`}
                    data-testid="mentrix-realtime-status"
                  >
                    {realtimePreflight === null
                      ? "Checking Realtime…"
                      : realtimePreflight.ready
                        ? `Realtime ready${realtimePreflight.model ? ` · ${realtimePreflight.model}` : ""}`
                        : `Realtime unavailable — ${realtimePreflight.reason || "check OPENAI_API_KEY"} · use typed asks or Retry`}
                  </p>
                  {integrations ? (
                    <p className="text-[10px] text-slate-500" data-testid="mentrix-integrations-status">
                      OpenAI {integrations.openai ? "ready" : "missing"} · Slack{" "}
                      {integrations.slack ? "ready" : "not set"} · Jira{" "}
                      {integrations.jira ? "ready" : "not set"}
                    </p>
                  ) : null}
                  <div className="mt-2 flex flex-wrap justify-center gap-2">
                    <label className="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 px-2 py-1.5 text-xs">
                      <span className="text-slate-400">Mic</span>
                      <select
                        data-testid="mentrix-mic-select"
                        className="max-w-[180px] rounded bg-slate-900 text-slate-100"
                        value={micDeviceId}
                        onChange={(e) => {
                          const id = e.target.value;
                          setMicDeviceId(id);
                          setStoredMicDeviceId(id);
                          pushLog(`Mic selected: ${micDevices.find((d) => d.deviceId === id)?.label || id}`);
                        }}
                      >
                        {micDevices.length === 0 ? (
                          <option value="">Default microphone</option>
                        ) : (
                          micDevices.map((d) => (
                            <option key={d.deviceId} value={d.deviceId}>
                              {d.label}
                            </option>
                          ))
                        )}
                      </select>
                    </label>
                    <button
                      type="button"
                      data-testid="mentrix-connect-voice"
                      onClick={toggleVoice}
                      disabled={
                        voiceConnecting || (!voiceConnected && realtimePreflight?.ready === false)
                      }
                      className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium disabled:opacity-50 ${
                        voiceConnected || voiceConnecting
                          ? "bg-teal-600 text-white"
                          : "border border-slate-600 text-slate-200"
                      }`}
                    >
                      {voiceConnected || voiceConnecting ? (
                        <Mic className="h-3.5 w-3.5" />
                      ) : (
                        <MicOff className="h-3.5 w-3.5" />
                      )}
                      {voiceConnecting
                        ? "Connecting…"
                        : voiceConnected
                          ? "Disconnect Voice"
                          : "Connect Voice"}
                    </button>
                    {!realtimePreflight?.ready && realtimePreflight !== null ? (
                      <button
                        type="button"
                        data-testid="mentrix-realtime-retry"
                        onClick={() => void refreshRealtimePreflight()}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-amber-700 px-3 py-1.5 text-xs text-amber-200"
                      >
                        Retry Realtime
                      </button>
                    ) : null}
                    <button
                      type="button"
                      data-testid="mentrix-display-mode"
                      onClick={() => setDisplayMode((d) => !d)}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 px-3 py-1.5 text-xs"
                    >
                      <Eye className="h-3.5 w-3.5" />
                      Display
                    </button>
                    <label className="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 px-3 py-1.5 text-xs">
                      <input
                        type="checkbox"
                        checked={computerMode}
                        data-testid="mentrix-computer-mode"
                        onChange={async (e) => {
                          const on = e.target.checked;
                          if (on) {
                            const ok = window.confirm(
                              "Enable Mentrix Computer Mode? Allowlisted apps/screenshots only after each confirm.",
                            );
                            if (!ok) return;
                          }
                          setComputerMode(on);
                          await window.zectDesktop?.mentrix?.setComputerMode?.(on);
                          pushLog(`Computer Mode ${on ? "ON" : "OFF"}`);
                        }}
                      />
                      <Monitor className="h-3.5 w-3.5" />
                      Computer Mode
                    </label>
                    <button
                      type="button"
                      data-testid="mentrix-artifacts-toggle"
                      onClick={() => setShowArtifacts((s) => !s)}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 px-3 py-1.5 text-xs"
                    >
                      <Sparkles className="h-3.5 w-3.5" />
                      Artifacts
                    </button>
                  </div>
                </div>

                <div
                  className="max-h-36 flex-1 space-y-1 overflow-auto border-t border-slate-800 pt-3 text-[11px] text-slate-400"
                  data-testid="mentrix-live-log"
                >
                  {log.length === 0 && <p>Live log — tool events stream here</p>}
                  {log.map((l, i) => (
                    <div key={i}>
                      <span className="text-teal-700">{l.ts}</span> {l.text}
                    </div>
                  ))}
                </div>

                <div
                  className="mt-3 max-h-48 flex-1 space-y-2 overflow-auto border-t border-slate-800 pt-3"
                  data-testid="mentrix-companion-chat"
                >
                  {messages.map((m, i) => (
                    <div
                      key={i}
                      className={
                        m.role === "user"
                          ? "ml-6 rounded-lg border border-teal-800 bg-teal-950/40 px-3 py-2 text-sm"
                          : "mr-6 rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-2 text-sm"
                      }
                    >
                      {m.text}
                    </div>
                  ))}
                  {streamReply ? (
                    <div className="mr-6 rounded-lg border border-emerald-900 bg-slate-900/80 px-3 py-2 text-sm text-emerald-100">
                      {streamReply}
                    </div>
                  ) : null}
                  <div ref={chatEnd} />
                </div>

                <div className="mt-3 flex items-end gap-2">
                  <textarea
                    data-testid="mentrix-companion-input"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    rows={2}
                    placeholder="Ask Mentrix…"
                    className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        onSend();
                      }
                    }}
                  />
                  <button
                    type="button"
                    data-testid="mentrix-companion-send"
                    disabled={loading || !input.trim()}
                    onClick={onSend}
                    className="rounded-lg bg-teal-600 p-2.5 disabled:opacity-40"
                  >
                    <Send className="h-5 w-5" />
                  </button>
                </div>
                <label className="mt-2 inline-flex items-center gap-2 text-xs text-slate-500">
                  <input type="checkbox" checked={tts} onChange={(e) => setTts(e.target.checked)} />
                  Speak replies (TTS)
                </label>
              </>
            )}
            {displayMode && (
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <span className="text-xs uppercase tracking-widest text-teal-500">Artifacts · Display</span>
                <button
                  type="button"
                  className="rounded border border-slate-600 px-2 py-1 text-xs"
                  onClick={() => setDisplayMode(false)}
                >
                  Hide
                </button>
              </div>
            )}
            {displayMode && <MentrixArtifacts items={board} displayMode />}
          </section>

          {showArtifacts && !displayMode && (
            <aside className="space-y-3 rounded-2xl border border-teal-900/40 bg-slate-900/80 p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 font-semibold text-teal-200">
                  <Sparkles className="h-4 w-4" />
                  ARTIFACTS
                </div>
                <button
                  type="button"
                  className="text-slate-400 hover:text-teal-300"
                  title="Fullscreen artifacts"
                  onClick={() => setDisplayMode(true)}
                >
                  <Maximize2 className="h-4 w-4" />
                </button>
              </div>
              <MentrixArtifacts items={board} />
              <div className="space-y-1 border-t border-slate-800 pt-3 text-xs text-slate-400">
                <p className="font-semibold text-slate-200">Quick asks</p>
                {[
                  "What's my Mentrix Delivery status?",
                  "What's the weather in Austin?",
                  "Slack digest",
                  "Check my email",
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
                      setLastMessageKeep(q);
                      runTurn(q);
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

      <MentrixConfirmModal
        open={pending.length > 0}
        items={pending}
        speakPrompt={tts}
        onAllow={onAllow}
        onDeny={() => {
          setPending([]);
          setAvatar("idle");
          setMessages((m) => [
            ...m,
            { role: "system", text: "Permission denied — Mentrix did not run those tools." },
          ]);
        }}
      />
    </div>
  );
}
