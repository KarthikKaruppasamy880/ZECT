/**
 * Shared Mentrix agent session — survives SPA route changes under Layout.
 * Owns Realtime voice, chat, board, and turn streaming for HUD + floating dock.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type Dispatch,
  type ReactNode,
  type RefObject,
  type SetStateAction,
} from "react";
import { useNavigate } from "react-router-dom";
import {
  apiFetch,
  getSkills,
  mentrixCompanionIntegrations,
  mentrixCompanionStream,
  mentrixCompanionStreamResume,
  mentrixCompanionTurn,
  mentrixListRuns,
  type MentrixStreamEvent,
} from "@/lib/api";
import type { PendingConfirm } from "@/components/MentrixConfirmModal";
import type { ArtifactItem } from "@/components/MentrixArtifacts";
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
import { fetchMentrixAgentContext } from "@/mentrix/agentContext";
import {
  applyDesktopToolOutput,
  COMPUTER_MODE_HINT,
  isOpenAiQuotaError,
  OPENAI_QUOTA_STATUS,
} from "@/mentrix/desktopBridge";
import { cancelBrowserSpeech, speakMentrix } from "@/mentrix/speak";

export type AvatarState =
  | "idle"
  | "listening"
  | "thinking"
  | "speaking"
  | "working"
  | "needs_permission";

export type ChatMsg = { role: "user" | "assistant" | "system"; text: string };
export type LogLine = { ts: string; text: string };

const SESSION_KEY = "mentrix_session_v1";
const SKILL_KEY = "mentrix_active_skill_id";
const DEFAULT_MSG: ChatMsg = {
  role: "assistant",
  text: "I'm Mentrix — your company operator. Ask for status, research, notes, Delivery, or say Open Lattice.",
};

export const ORB: Record<AvatarState, string> = {
  idle: "from-slate-800 to-slate-950 border-slate-500 shadow-slate-700/40",
  listening: "from-teal-900 to-slate-950 border-teal-400 shadow-teal-500/50 animate-pulse",
  thinking: "from-amber-950 to-slate-950 border-amber-400 shadow-amber-500/40 animate-pulse",
  speaking: "from-emerald-950 to-slate-950 border-emerald-400 shadow-emerald-500/50",
  working: "from-sky-950 to-slate-950 border-sky-400 shadow-sky-500/40 animate-pulse",
  needs_permission: "from-amber-950 to-slate-950 border-amber-500 shadow-amber-600/60",
};

function speak(text: string, enabled: boolean, onFail?: (err: string) => void) {
  // Companion chat: prefer clone, but fall back to OpenAI/browser if Voicebox profile is stale.
  // Present / Test speak keep requireClone: true (strict).
  void speakMentrix(text, enabled, { requireClone: false }).then((r) => {
    if (!r.ok) {
      console.warn("[mentrix TTS]", r.error);
      onFail?.(r.error);
    }
  });
}

function loadPersistedMessages(): ChatMsg[] {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return [DEFAULT_MSG];
    const parsed = JSON.parse(raw) as { messages?: ChatMsg[] };
    if (Array.isArray(parsed.messages) && parsed.messages.length) {
      return parsed.messages.slice(-20);
    }
  } catch {
    /* ignore */
  }
  return [DEFAULT_MSG];
}

function persistMessages(messages: ChatMsg[]) {
  try {
    sessionStorage.setItem(
      SESSION_KEY,
      JSON.stringify({ messages: messages.slice(-20), ts: Date.now() }),
    );
  } catch {
    /* ignore */
  }
}

function readActiveProjectId(): string {
  try {
    const raw = localStorage.getItem("zect_active_project");
    if (!raw) return "";
    const parsed = JSON.parse(raw) as { projectId?: number | null };
    return parsed.projectId != null ? String(parsed.projectId) : "";
  } catch {
    return "";
  }
}

export function applyNav(path: string | null | undefined, navigate: (to: number | string) => void) {
  if (!path) return;
  if (path === "__back__") {
    navigate(-1);
    return;
  }
  // SPA-only — never hard-assign (avoids remounting the Layout session).
  try {
    navigate(path);
  } catch {
    /* ignore */
  }
}

type SkillOpt = { id: number; name: string };

type MentrixSessionValue = {
  messages: ChatMsg[];
  setMessages: Dispatch<SetStateAction<ChatMsg[]>>;
  input: string;
  setInput: (v: string) => void;
  avatar: AvatarState;
  setAvatar: Dispatch<SetStateAction<AvatarState>>;
  board: ArtifactItem[];
  setBoard: Dispatch<SetStateAction<ArtifactItem[]>>;
  log: LogLine[];
  statusLine: string;
  setStatusLine: (v: string) => void;
  tts: boolean;
  setTts: (v: boolean) => void;
  browserTtsEnabled: boolean;
  voiceConnected: boolean;
  voiceConnecting: boolean;
  /** Phase 6 — Mentrix voice provider + last latency checkpoint */
  voiceTelemetry: { mode: "realtime" | "fallback" | "idle"; lastMark: string; lastMs: number; ttsEngine: string };
  computerMode: boolean;
  setComputerMode: Dispatch<SetStateAction<boolean>>;
  displayMode: boolean;
  setDisplayMode: Dispatch<SetStateAction<boolean>>;
  showArtifacts: boolean;
  setShowArtifacts: Dispatch<SetStateAction<boolean>>;
  pending: PendingConfirm[];
  setPending: Dispatch<SetStateAction<PendingConfirm[]>>;
  turnId: string;
  loading: boolean;
  runsHint: string;
  streamReply: string;
  lastMessage: string;
  setLastMessageKeep: (v: string) => void;
  realtimePreflight: RealtimePreflight | null;
  micDevices: MicDevice[];
  micDeviceId: string;
  setMicDeviceId: (id: string) => void;
  integrations: { slack: boolean; jira: boolean; openai: boolean; datadog?: boolean; github?: boolean } | null;
  dockExpanded: boolean;
  setDockExpanded: Dispatch<SetStateAction<boolean>>;
  wakeQueued: boolean;
  skills: SkillOpt[];
  activeSkillId: string;
  setActiveSkillId: (id: string) => void;
  pushLog: (text: string) => void;
  refreshRealtimePreflight: () => Promise<RealtimePreflight>;
  startVoice: () => Promise<void>;
  stopVoice: () => void;
  toggleVoice: () => void;
  runTurn: (message: string, confirmed?: string[], resumeId?: string) => Promise<void>;
  onSend: () => Promise<void>;
  presentNarrate: () => Promise<void>;
  onAllow: (tools: string[]) => Promise<void>;
  applyNavPath: (path: string | null | undefined) => void;
  chatEndRef: RefObject<HTMLDivElement>;
};

const MentrixSessionContext = createContext<MentrixSessionValue | null>(null);

export function MentrixSessionProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<ChatMsg[]>(loadPersistedMessages);
  const [input, setInput] = useState("");
  const [avatar, setAvatar] = useState<AvatarState>("idle");
  const [board, setBoard] = useState<ArtifactItem[]>([]);
  const [log, setLog] = useState<LogLine[]>([]);
  const [statusLine, setStatusLine] = useState("SYSTEMS OPERATIONAL");
  const [tts, setTts] = useState(true);
  const [voiceConnected, setVoiceConnected] = useState(false);
  const [voiceConnecting, setVoiceConnecting] = useState(false);
  const [voiceTelemetry, setVoiceTelemetry] = useState<{
    mode: "realtime" | "fallback" | "idle";
    lastMark: string;
    lastMs: number;
    ttsEngine: string;
  }>({ mode: "idle", lastMark: "", lastMs: 0, ttsEngine: "" });
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
  const [micDeviceId, setMicDeviceIdState] = useState(() => getStoredMicDeviceId());
  const [integrations, setIntegrations] = useState<{
    slack: boolean;
    jira: boolean;
    openai: boolean;
    datadog?: boolean;
    github?: boolean;
  } | null>(null);
  const [dockExpanded, setDockExpanded] = useState(false);
  const [wakeQueued, setWakeQueued] = useState(false);
  const [skills, setSkills] = useState<SkillOpt[]>([]);
  const [activeSkillId, setActiveSkillIdState] = useState(
    () => localStorage.getItem(SKILL_KEY) || "",
  );

  const realtimeRef = useRef<RealtimeSessionHandle | null>(null);
  const voiceConnectingRef = useRef(false);
  const micDeviceIdRef = useRef(micDeviceId);
  micDeviceIdRef.current = micDeviceId;
  const pendingArgsRef = useRef<Record<string, Record<string, unknown>>>({});
  const chatEndRef = useRef<HTMLDivElement>(null!);
  const abortRef = useRef<AbortController | null>(null);
  const providerReadyRef = useRef(false);
  const ttsRef = useRef(tts);
  ttsRef.current = tts;
  const computerModeRef = useRef(computerMode);
  computerModeRef.current = computerMode;
  const voiceConnectedRef = useRef(voiceConnected);
  voiceConnectedRef.current = voiceConnected;
  // When Connect Voice / Realtime owns the speaker, companion chat TTS must stay
  // silent — otherwise users hear two overlapping voices (Realtime + speakMentrix).
  const browserTtsEnabled = tts && !voiceConnected;

  const speakAllowed = useCallback(() => ttsRef.current && !voiceConnectedRef.current && !realtimeRef.current, []);

  const speakChat = useCallback((text: string, onFail?: (err: string) => void) => {
    if (!speakAllowed()) return;
    speak(text, true, onFail);
  }, [speakAllowed]);

  const pushLog = useCallback((text: string) => {
    const ts = new Date().toLocaleTimeString();
    setLog((l) => [{ ts, text }, ...l].slice(0, 80));
  }, []);

  const handleDesktopOutput = useCallback(
    async (output: string | Record<string, unknown>) => {
      const res = await applyDesktopToolOutput(output, computerModeRef.current);
      if (res.skipped) return;
      if (res.error === "computer_mode_off") {
        setStatusLine(COMPUTER_MODE_HINT);
        pushLog("Computer Mode required for desktop tools");
      } else if (res.error === "not_desktop_app") {
        pushLog("Desktop tools require the ZECT Electron app");
      } else if (!res.ok) {
        pushLog(
          `Desktop tool failed: ${res.error || "unknown"}${res.hint ? ` (${res.hint})` : ""}${
            res.verified === false ? " · unverified" : ""
          }`,
        );
      } else if (res.verified === false) {
        pushLog("Desktop action ran but verification did not confirm target window");
      } else {
        pushLog("Desktop action OK");
      }
    },
    [pushLog],
  );

  const handleQuotaError = useCallback(
    (err: string) => {
      pushLog(`realtime ${err}`);
      if (!isOpenAiQuotaError(err)) return;
      setRealtimePreflight({ ready: false, reason: "openai_quota" });
      setStatusLine(OPENAI_QUOTA_STATUS);
      setVoiceConnected(false);
      setAvatar("idle");
    },
    [pushLog],
  );

  const applyNavPath = useCallback(
    (path: string | null | undefined) => applyNav(path, navigate as (to: number | string) => void),
    [navigate],
  );

  const setMicDeviceId = useCallback((id: string) => {
    setMicDeviceIdState(id);
    setStoredMicDeviceId(id);
  }, []);

  const setActiveSkillId = useCallback((id: string) => {
    setActiveSkillIdState(id);
    if (id) localStorage.setItem(SKILL_KEY, id);
    else localStorage.removeItem(SKILL_KEY);
  }, []);

  useEffect(() => {
    persistMessages(messages);
  }, [messages]);

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
    getSkills()
      .then((list) => {
        if (!Array.isArray(list)) return;
        setSkills(
          list
            .filter((s) => s?.id != null)
            .map((s) => ({ id: Number(s.id), name: String(s.name || `Skill ${s.id}`) })),
        );
      })
      .catch(() => setSkills([]));
    void (async () => {
      await ensureMicPermission();
      const devices = await listMicDevices();
      setMicDevices(devices);
      const stored = getStoredMicDeviceId();
      if (stored && devices.some((d) => d.deviceId === stored)) {
        setMicDeviceIdState(stored);
      } else if (!stored && devices[0]?.deviceId) {
        setMicDeviceIdState(devices[0].deviceId);
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

  const stopVoice = useCallback(() => {
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

  const startVoice = useCallback(async () => {
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
    setDockExpanded(true);
    cancelBrowserSpeech();
    try {
      const preflight = await refreshRealtimePreflight();
      if (!preflight?.ready || !preflight.client_secret) {
        setVoiceConnected(false);
        setAvatar("idle");
        setStatusLine(`Realtime unavailable — ${preflight?.reason || "check OPENAI_API_KEY"}`);
        pushLog(`realtime_unavailable ${preflight?.reason || "unknown"}`);
        return;
      }
      const agentCtx = await fetchMentrixAgentContext({
        skillId: activeSkillId,
        projectId: readActiveProjectId(),
      });
      const handle = await startMentrixRealtime({
        skipRealtime: false,
        forceReusePreflight: true,
        preflight,
        deviceId: micDeviceIdRef.current || undefined,
        extraInstructions: agentCtx || undefined,
        handlers: {
          getComputerMode: () => computerModeRef.current,
          onDesktopOutput: (output) => handleDesktopOutput(output),
          onOrb: (s) => setAvatar(s as AvatarState),
          onLog: pushLog,
          onPerfMark: (m) => {
            setVoiceTelemetry((prev) => ({
              ...prev,
              lastMark: m.name,
              lastMs: m.elapsedMs,
            }));
          },
          onTranscript: (role, text) => {
            if (!text?.trim()) return;
            setMessages((m) => {
              const last = m[m.length - 1];
              if (last?.role === role && last?.text === text) return m;
              // Grow the last assistant bubble while Realtime text deltas stream in.
              if (
                role === "assistant" &&
                last?.role === "assistant" &&
                text.startsWith(last.text)
              ) {
                return [...m.slice(0, -1), { role, text }];
              }
              return [...m, { role, text }];
            });
            if (role === "user") setLastMessageKeep(text);
          },
          onNavigate: (path) => applyNavPath(path),
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
            speakChat("I need your permission to continue.");
          },
          onError: (err) => {
            if (/Voice output:/i.test(String(err))) {
              setStatusLine(String(err));
              pushLog(String(err));
              return;
            }
            handleQuotaError(err);
          },
          onFallback: (reason) => {
            pushLog(`realtime_unavailable ${reason}`);
            if (isOpenAiQuotaError(String(reason))) {
              handleQuotaError(String(reason));
            }
            try {
              realtimeRef.current?.stop();
            } catch {
              /* ignore */
            }
            realtimeRef.current = null;
            setVoiceConnected(false);
            setAvatar("idle");
            if (!isOpenAiQuotaError(String(reason))) {
              setStatusLine(`Realtime unavailable — ${reason}. Use typed Quick asks or Retry.`);
            }
          },
        },
      });
      if (handle.mode !== "realtime") {
        setVoiceTelemetry((prev) => ({ ...prev, mode: "fallback", ttsEngine: prev.ttsEngine || "browser" }));
        setVoiceConnected(false);
        setAvatar("idle");
        return;
      }
      setVoiceTelemetry((prev) => ({ ...prev, mode: "realtime" }));
      realtimeRef.current = handle;
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
      stopVoice();
      setStatusLine("Connect Voice failed — Retry");
    } finally {
      voiceConnectingRef.current = false;
      setVoiceConnecting(false);
    }
  }, [activeSkillId, applyNavPath, handleDesktopOutput, handleQuotaError, pushLog, refreshRealtimePreflight, speakChat, stopVoice]);

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
          applyNavPath(d.path);
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
          if (d.navigate) applyNavPath(d.navigate);
          if (d.pending_confirmations?.length) {
            setPending(d.pending_confirmations);
            setAvatar("needs_permission");
          } else {
            setAvatar("speaking");
            speakChat(reply, (err) => setStatusLine(`Voice: ${err}`));
          }
          setStatusLine(d.latency_mode === "fast_tools" ? "Replied (instant)" : "SYSTEMS OPERATIONAL");
          pushLog(`done ${d.latency_ms || 0}ms`);
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
    [applyNavPath, pushLog, speakChat],
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
      let streamFinalized = false;
      const agentContext = await fetchMentrixAgentContext({
        skillId: activeSkillId,
        projectId: readActiveProjectId(),
      });
      const onStreamEvent = (ev: MentrixStreamEvent) => {
        if (ev.event === "done" || ev.event === "error") streamFinalized = true;
        handleStreamEvent(ev);
      };
      try {
        if (resumeId) {
          await mentrixCompanionStreamResume(resumeId, confirmed, {
            signal: controller.signal,
            onEvent: onStreamEvent,
          });
        } else {
          try {
            await mentrixCompanionStream(message, {
              project_key: localStorage.getItem("zect_lattice_key") || "",
              confirmed_tools: confirmed,
              agent_context: agentContext,
              signal: controller.signal,
              onEvent: onStreamEvent,
            });
          } catch {
            // Stream already emitted done/error — do not append or speak again.
            if (streamFinalized || controller.signal.aborted) return;
            const res = await mentrixCompanionTurn(message, {
              confirmed_tools: confirmed,
              project_key: localStorage.getItem("zect_lattice_key") || "",
              agent_context: agentContext,
              signal: controller.signal,
            });
            if (res.navigate) applyNavPath(res.navigate);
            if (res.pending_confirmations?.length) {
              setPending(res.pending_confirmations);
              setTurnId(res.turn_id || "");
              setLastMessageKeep(message);
              setAvatar("needs_permission");
              speakChat("I need your permission to continue.");
            } else {
              setPending([]);
              setMessages((m) => {
                const reply = res.reply || "Done.";
                const last = m[m.length - 1];
                if (last?.role === "assistant" && last?.text === reply) return m;
                return [...m, { role: "assistant", text: reply }];
              });
              if (res.board?.length) setBoard((b) => [...res.board, ...b].slice(0, 16));
              setAvatar("speaking");
              speakChat(res.reply || "");
            }
            for (const t of res.tools || []) {
              if (t.result?.desktop && !t.denied) {
                await handleDesktopOutput(t.result as Record<string, unknown>);
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
    [activeSkillId, applyNavPath, handleDesktopOutput, handleStreamEvent, speakChat],
  );

  const onSend = useCallback(async () => {
    const msg = input.trim();
    if (!msg || loading) return;
    setInput("");
    setLastMessageKeep(msg);
    await runTurn(msg);
  }, [input, loading, runTurn]);

  const presentNarrate = useCallback(async () => {
    setDisplayMode(true);
    setTts(true);
    const chunks: string[] = [];
    for (const item of board.slice(0, 5)) {
      const title = (item as { title?: string }).title || (item as { type?: string }).type || "Artifact";
      const body =
        (item as { body?: string }).body ||
        (typeof (item as { data?: unknown }).data === "string"
          ? String((item as { data?: string }).data)
          : "") ||
        "";
      const text = `${title}. ${body}`.replace(/\s+/g, " ").trim().slice(0, 800);
      if (text) chunks.push(text);
    }
    if (!chunks.length) {
      const last = [...messages].reverse().find((m) => m.role === "assistant")?.text;
      if (last) chunks.push(last.slice(0, 800));
    }
    if (!chunks.length) {
      chunks.push(
        "Mentrix Present mode. Add artifacts or ask Mentrix for a brief, then Narrate again.",
      );
    }
    setAvatar("speaking");
    setStatusLine("Present / Narrate");
    if (voiceConnectedRef.current || realtimeRef.current) {
      setStatusLine("Present text shown — Disconnect Voice to narrate with chat TTS");
      setAvatar("idle");
      return;
    }
    let lastErr = "";
    for (const chunk of chunks) {
      const result = await speakMentrix(chunk, true);
      if (!result.ok) lastErr = result.error;
    }
    setAvatar("idle");
    if (lastErr) setStatusLine(`Voice: ${lastErr}`);
    else setStatusLine("Present / Narrate complete");
  }, [board, messages]);

  const onAllow = useCallback(
    async (tools: string[]) => {
      setPending([]);
      const msg = lastMessage || input;
      if (realtimeRef.current?.mode === "realtime") {
        const outputs = await confirmRealtimeTools(tools, pendingArgsRef.current, {
          onNavigate: (path) => applyNavPath(path),
          onArtifact: (item) => setBoard((b) => [item as ArtifactItem, ...b].slice(0, 16)),
          onLog: pushLog,
          onOrb: (s) => setAvatar(s as AvatarState),
          onDesktopOutput: (output) => handleDesktopOutput(output),
        });
        const summary = outputs
          .map((o) => {
            try {
              const j = JSON.parse(o);
              return j.spoken_summary || j.note || o.slice(0, 120);
            } catch {
              return o.slice(0, 120);
            }
          })
          .join(" ");
        realtimeRef.current.resumeAfterTool(summary || "Done.");
        setAvatar("speaking");
        return;
      }
      if (turnId) await runTurn(msg, tools, turnId);
      else await runTurn(msg, tools);
    },
    [applyNavPath, handleDesktopOutput, input, lastMessage, pushLog, runTurn, turnId],
  );

  const toggleVoice = useCallback(() => {
    if (voiceConnectingRef.current) return;
    if (voiceConnected || realtimeRef.current) {
      stopVoice();
      setStatusLine("Voice disconnected");
      pushLog("Voice disconnected");
      return;
    }
    void startVoice();
  }, [pushLog, startVoice, stopVoice, voiceConnected]);

  const startVoiceRef = useRef(startVoice);
  startVoiceRef.current = startVoice;
  const applyNavPathRef = useRef(applyNavPath);
  applyNavPathRef.current = applyNavPath;
  const stopVoiceRef = useRef(stopVoice);
  stopVoiceRef.current = stopVoice;

  // Wake / SPA navigate — Layout lifetime. Do not stop voice when handlers rebind.
  useEffect(() => {
    providerReadyRef.current = true;
    const desktop = window.zectDesktop?.mentrix;
    const unsubs: Array<() => void> = [];
    if (desktop?.onWake) {
      unsubs.push(
        desktop.onWake(() => {
          setAvatar("listening");
          setDockExpanded(true);
          pushLog("Wake — Connect Voice (Realtime)");
          void startVoiceRef.current();
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
    const onDomWake = () => {
      setAvatar("listening");
      setDockExpanded(true);
      void startVoiceRef.current();
    };
    const onSpaNav = (ev: Event) => {
      const path = (ev as CustomEvent<{ path?: string }>).detail?.path;
      if (path) applyNavPathRef.current(path);
    };
    window.addEventListener("mentrix-wake", onDomWake);
    window.addEventListener("mentrix-spa-navigate", onSpaNav);

    // Electron agent: heartbeat + poll mobile desktop-bridge queue
    let bridgeTimer: ReturnType<typeof setInterval> | null = null;
    if (desktop) {
      // Sync API emergency stop → Electron so Computer Mode honors it
      void (async () => {
        try {
          const res = await apiFetch("/api/permissions/emergency-stop");
          if (res.ok) {
            const body = await res.json();
            await desktop.setEmergencyStop?.(!!body.active);
          }
        } catch {
          /* ignore */
        }
      })();
      const tickBridge = async () => {
        try {
          const { mentrixDesktopBridgeHeartbeat, mentrixDesktopBridgePoll, mentrixDesktopBridgeAck } =
            await import("@/lib/api");
          await mentrixDesktopBridgeHeartbeat();
          const polled = await mentrixDesktopBridgePoll();
          for (const item of polled.items || []) {
            const cmd = item.command || {};
            const action = String(cmd.action || "write_note");
            let result: Record<string, unknown> = { ok: false, error: "computer_mode_off" };
            if (computerModeRef.current && desktop.computer) {
              result = (await desktop.computer(action, cmd)) as Record<string, unknown>;
            } else if (!computerModeRef.current) {
              result = {
                ok: false,
                error: "computer_mode_off",
                hint: "Desktop actions require Electron + Computer Mode on.",
              };
            }
            await mentrixDesktopBridgeAck(item.id, result);
            pushLog(`Desktop bridge ${action}: ${result.ok ? "ok" : result.error || "fail"}`);
          }
        } catch {
          /* ignore bridge errors */
        }
      };
      void tickBridge();
      bridgeTimer = setInterval(tickBridge, 8000);
    }

    return () => {
      unsubs.forEach((u) => u());
      window.removeEventListener("mentrix-wake", onDomWake);
      window.removeEventListener("mentrix-spa-navigate", onSpaNav);
      if (bridgeTimer) clearInterval(bridgeTimer);
    };
  }, [pushLog]);

  useEffect(() => {
    if (!wakeQueued) return;
    setWakeQueued(false);
    setDockExpanded(true);
    void startVoiceRef.current();
  }, [wakeQueued]);

  // Queue wake if event fires before provider effects settle (first paint).
  useEffect(() => {
    const early = () => {
      if (!providerReadyRef.current) {
        setWakeQueued(true);
        setDockExpanded(true);
      }
    };
    window.addEventListener("mentrix-wake", early, true);
    return () => window.removeEventListener("mentrix-wake", early, true);
  }, []);

  // Stop Realtime only when authenticated Layout unmounts (logout).
  useEffect(() => {
    return () => {
      stopVoiceRef.current();
    };
  }, []);

  const value = useMemo<MentrixSessionValue>(
    () => ({
      messages,
      setMessages,
      input,
      setInput,
      avatar,
      setAvatar,
      board,
      setBoard,
      log,
      statusLine,
      setStatusLine,
      tts,
      setTts,
      browserTtsEnabled,
      voiceConnected,
      voiceConnecting,
      voiceTelemetry,
      computerMode,
      setComputerMode,
      displayMode,
      setDisplayMode,
      showArtifacts,
      setShowArtifacts,
      pending,
      setPending,
      turnId,
      loading,
      runsHint,
      streamReply,
      lastMessage,
      setLastMessageKeep,
      realtimePreflight,
      micDevices,
      micDeviceId,
      setMicDeviceId,
      integrations,
      dockExpanded,
      setDockExpanded,
      wakeQueued,
      skills,
      activeSkillId,
      setActiveSkillId,
      pushLog,
      refreshRealtimePreflight,
      startVoice,
      stopVoice,
      toggleVoice,
      runTurn,
      onSend,
      presentNarrate,
      onAllow,
      applyNavPath,
      chatEndRef,
    }),
    [
      messages,
      input,
      avatar,
      board,
      log,
      statusLine,
      tts,
      browserTtsEnabled,
      voiceConnected,
      voiceConnecting,
      voiceTelemetry,
      computerMode,
      displayMode,
      showArtifacts,
      pending,
      turnId,
      loading,
      runsHint,
      streamReply,
      lastMessage,
      realtimePreflight,
      micDevices,
      micDeviceId,
      setMicDeviceId,
      integrations,
      dockExpanded,
      wakeQueued,
      skills,
      activeSkillId,
      setActiveSkillId,
      pushLog,
      refreshRealtimePreflight,
      startVoice,
      stopVoice,
      toggleVoice,
      runTurn,
      onSend,
      presentNarrate,
      onAllow,
      applyNavPath,
    ],
  );

  return (
    <MentrixSessionContext.Provider value={value}>{children}</MentrixSessionContext.Provider>
  );
}

export function useMentrixSession(): MentrixSessionValue {
  const ctx = useContext(MentrixSessionContext);
  if (!ctx) {
    throw new Error("useMentrixSession must be used within MentrixSessionProvider");
  }
  return ctx;
}
