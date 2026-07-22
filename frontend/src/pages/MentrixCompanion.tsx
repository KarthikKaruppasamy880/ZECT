/**
 * Mentrix Companion Home — company personal agent (visual + tools + permissions).
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bot, Mic, MicOff, Monitor, Send, Sparkles } from "lucide-react";
import {
  mentrixCompanionPolicy,
  mentrixCompanionPolicyImport,
  mentrixCompanionTurn,
  mentrixListRuns,
} from "@/lib/api";
import MentrixConfirmModal, { type PendingConfirm } from "@/components/MentrixConfirmModal";

declare global {
  interface Window {
    zectDesktop?: {
      isDesktopApp?: boolean;
      mentrix?: {
        onWake?: (cb: (p: { phrase?: string }) => void) => () => void;
        onSttGoal?: (cb: (p: { goal?: string }) => void) => () => void;
        onComputerMode?: (cb: (p: { computerMode?: boolean; reason?: string }) => void) => () => void;
        setComputerMode?: (enabled: boolean) => Promise<unknown>;
        confirmAction?: (payload: unknown) => Promise<unknown>;
        computer?: (action: string, args?: Record<string, unknown>) => Promise<unknown>;
      };
    };
  }
}

type AvatarState = "idle" | "listening" | "thinking" | "speaking" | "working" | "needs_permission";

type ChatMsg = { role: "user" | "assistant" | "system"; text: string };

type BoardItem = { type?: string; title?: string; body?: string };

function speak(text: string, enabled: boolean) {
  if (!enabled || typeof window === "undefined" || !window.speechSynthesis) return;
  try {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text.slice(0, 500));
    u.rate = 1.05;
    window.speechSynthesis.speak(u);
  } catch {
    /* ignore */
  }
}

const AVATAR_RING: Record<AvatarState, string> = {
  idle: "border-slate-500 shadow-slate-700/40",
  listening: "border-teal-400 shadow-teal-500/50 animate-pulse",
  thinking: "border-amber-400 shadow-amber-500/40 animate-pulse",
  speaking: "border-emerald-400 shadow-emerald-500/50",
  working: "border-sky-400 shadow-sky-500/40 animate-pulse",
  needs_permission: "border-amber-500 shadow-amber-600/60",
};

export default function MentrixCompanion() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<ChatMsg[]>([
    {
      role: "assistant",
      text: "I'm Mentrix — your company agent for research, content, reporting, docs, and Delivery. Ask me anything. Sensitive actions always need your permission.",
    },
  ]);
  const [input, setInput] = useState("");
  const [avatar, setAvatar] = useState<AvatarState>("idle");
  const [board, setBoard] = useState<BoardItem[]>([]);
  const [statusLine, setStatusLine] = useState("Ready");
  const [tts, setTts] = useState(true);
  const [listening, setListening] = useState(false);
  const [computerMode, setComputerMode] = useState(false);
  const [pending, setPending] = useState<PendingConfirm[]>([]);
  const [lastMessage, setLastMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [runsHint, setRunsHint] = useState("");
  const recognitionRef = useRef<any>(null);
  const chatEnd = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    chatEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    mentrixListRuns(3)
      .then((runs) => {
        if (Array.isArray(runs) && runs[0]) {
          setRunsHint(`#${runs[0].id} ${runs[0].status} · ${runs[0].mode}`);
        }
      })
      .catch(() => {});
  }, []);

  // Desktop wake → focus companion; Computer Mode idle auto-off
  useEffect(() => {
    const desktop = window.zectDesktop?.mentrix;
    const unsubs: Array<() => void> = [];
    if (desktop?.onWake) {
      unsubs.push(
        desktop.onWake(() => {
          setAvatar("listening");
          speak("Mentrix ready. How can I help?", tts);
        }),
      );
    }
    if (desktop?.onComputerMode) {
      unsubs.push(
        desktop.onComputerMode((p) => {
          if (p?.computerMode === false) {
            setComputerMode(false);
            setStatusLine(
              p.reason === "idle_auto_off"
                ? "Computer Mode auto-off after idle"
                : "Computer Mode OFF",
            );
          }
        }),
      );
    }
    const onDom = () => setAvatar("listening");
    window.addEventListener("mentrix-wake", onDom);
    return () => {
      unsubs.forEach((u) => u());
      window.removeEventListener("mentrix-wake", onDom);
    };
  }, [tts]);

  const applyNavigate = useCallback(
    (path: string | null | undefined) => {
      if (!path) return;
      if (path === "__back__") {
        navigate(-1);
        return;
      }
      navigate(path);
    },
    [navigate],
  );

  const runTurn = useCallback(
    async (message: string, confirmed: string[] = []) => {
      setLoading(true);
      setAvatar(confirmed.length ? "working" : "thinking");
      setStatusLine("Mentrix thinking…");
      try {
        const res = await mentrixCompanionTurn(message, {
          confirmed_tools: confirmed,
          project_key: localStorage.getItem("zect_lattice_key") || "",
        });
        const pendingItems: PendingConfirm[] = res.pending_confirmations || [];
        if (pendingItems.length) {
          setPending(pendingItems);
          setLastMessage(message);
          setAvatar("needs_permission");
          setStatusLine("Waiting for your permission");
          speak("I need your permission to continue.", tts);
        } else {
          setPending([]);
          setMessages((m) => [
            ...m,
            { role: "user", text: message },
            { role: "assistant", text: res.reply || "Done." },
          ]);
          if (res.board?.length) setBoard((b) => [...res.board, ...b].slice(0, 12));
          setAvatar("speaking");
          setStatusLine("Mentrix replied");
          speak(res.reply || "", tts);
          applyNavigate(res.navigate);
          // Desktop computer tools only when Computer Mode ON (after confirm)
          const desktopActs = (res.tools || []).filter(
            (t: any) => t.result?.desktop && !t.denied,
          );
          for (const t of desktopActs) {
            if (!computerMode) {
              setStatusLine("Computer Mode is OFF — enable it for desktop control");
              continue;
            }
            const action = String(t.result.desktop);
            await window.zectDesktop?.mentrix?.confirmAction?.({ tool: t.tool, action });
            await window.zectDesktop?.mentrix?.computer?.(action, {
              ...t.result,
              ...(t.result.args || {}),
              app: t.result.app,
              path: t.result.path,
            });
          }
        }
      } catch (e) {
        setMessages((m) => [
          ...m,
          { role: "user", text: message },
          { role: "assistant", text: e instanceof Error ? e.message : "Companion turn failed" },
        ]);
        setAvatar("idle");
      } finally {
        setLoading(false);
        setTimeout(() => setAvatar((a) => (a === "speaking" ? "idle" : a)), 2500);
      }
    },
    [applyNavigate, computerMode, tts],
  );

  const onSend = async () => {
    const msg = input.trim();
    if (!msg || loading) return;
    setInput("");
    await runTurn(msg);
  };

  const onAllow = async (tools: string[]) => {
    setPending([]);
    const msg = lastMessage || input;
    setMessages((m) => {
      if (m[m.length - 1]?.text === msg && m[m.length - 1]?.role === "user") return m;
      return [...m, { role: "user", text: msg }];
    });
    await runTurn(msg, tools);
  };

  const toggleListen = () => {
    const SR =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const desktop = window.zectDesktop?.isDesktopApp;
    if (listening) {
      try {
        recognitionRef.current?.stop?.();
      } catch {
        /* ignore */
      }
      setListening(false);
      setAvatar("idle");
      return;
    }
    if (!SR && !desktop) {
      setStatusLine("Speech recognition unavailable — type your request");
      return;
    }
    if (SR && !desktop) {
      const rec = new SR();
      recognitionRef.current = rec;
      rec.continuous = false;
      rec.interimResults = false;
      rec.lang = "en-US";
      rec.onresult = (ev: any) => {
        const t = ev.results?.[0]?.[0]?.transcript || "";
        if (t) {
          setInput(t);
          setMessages((m) => [...m, { role: "user", text: t }]);
          runTurn(t);
        }
      };
      rec.onerror = () => {
        setListening(false);
        setAvatar("idle");
      };
      rec.onend = () => {
        setListening(false);
        setAvatar("idle");
      };
      try {
        rec.start();
        setListening(true);
        setAvatar("listening");
      } catch {
        setListening(false);
      }
      return;
    }
    // Desktop: mark listening; wake STT feeds transcripts via IPC
    setListening(true);
    setAvatar("listening");
    setStatusLine("Listening — say your request after Hey Mentrix");
  };

  useEffect(() => {
    const desktop = window.zectDesktop?.mentrix;
    if (!desktop?.onSttGoal) return;
    return desktop.onSttGoal((payload) => {
      if (!payload?.goal || !listening) return;
      setMessages((m) => [...m, { role: "user", text: payload.goal! }]);
      runTurn(payload.goal);
    });
  }, [listening, runTurn]);

  return (
    <div className="max-w-6xl mx-auto space-y-4" data-testid="mentrix-companion-page">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Mentrix Companion</h1>
          <p className="text-sm text-slate-600">
            Company personal agent — research, content, reporting, docs, Delivery. Sensitive work always asks.
          </p>
        </div>
          <div className="flex flex-wrap gap-2 text-xs">
          <button
            type="button"
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-slate-700"
            data-testid="mentrix-policy-export"
            onClick={async () => {
              try {
                const pack = await mentrixCompanionPolicy();
                await navigator.clipboard.writeText(JSON.stringify(pack, null, 2));
                setStatusLine("Org Mentrix policy copied to clipboard");
              } catch (e) {
                setStatusLine(e instanceof Error ? e.message : "Policy export failed");
              }
            }}
          >
            Export org policy
          </button>
          <button
            type="button"
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-slate-700"
            data-testid="mentrix-policy-import"
            onClick={async () => {
              const raw = window.prompt("Paste Mentrix org policy JSON to import");
              if (!raw?.trim()) return;
              try {
                const pack = JSON.parse(raw);
                const res = await mentrixCompanionPolicyImport(pack, false);
                setStatusLine(`Imported ${res.imported_rules ?? 0} Mentrix policy rules`);
              } catch (e) {
                setStatusLine(e instanceof Error ? e.message : "Policy import failed");
              }
            }}
          >
            Import org policy
          </button>
          <Link to="/mentrix" className="rounded-lg border border-slate-300 px-3 py-1.5 text-slate-700">
            Mentrix Delivery
          </Link>
          <Link to="/permissions" className="rounded-lg border border-slate-300 px-3 py-1.5 text-slate-700">
            Permissions
          </Link>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <div className="rounded-2xl border border-slate-800 bg-slate-950 text-slate-100 p-6 min-h-[480px] flex flex-col">
          <div className="flex flex-col items-center gap-3 py-6">
            <div
              data-testid="mentrix-avatar"
              data-state={avatar}
              className={`h-36 w-36 rounded-full border-4 bg-gradient-to-br from-slate-800 to-slate-900 shadow-2xl flex items-center justify-center ${AVATAR_RING[avatar]}`}
            >
              <Bot className="h-16 w-16 text-teal-300" />
            </div>
            <p className="text-sm text-teal-200/90">GOOD TO SEE YOU</p>
            <p className="text-xs text-slate-400" data-testid="mentrix-companion-status">
              {statusLine}
              {runsHint ? ` · Delivery ${runsHint}` : ""}
            </p>
            <label className="inline-flex items-center gap-2 text-xs text-slate-300">
              <input
                type="checkbox"
                checked={computerMode}
                onChange={async (e) => {
                  const on = e.target.checked;
                  if (on) {
                    const ok = window.confirm(
                      "Enable Mentrix Computer Mode? Mentrix may open allowlisted apps and capture screenshots only after you confirm each sensitive action.",
                    );
                    if (!ok) return;
                  }
                  setComputerMode(on);
                  await window.zectDesktop?.mentrix?.setComputerMode?.(on);
                }}
                data-testid="mentrix-computer-mode"
              />
              <Monitor className="h-3.5 w-3.5" />
              Computer Mode {computerMode ? "ON" : "OFF"}
            </label>
          </div>

          <div className="flex-1 overflow-auto space-y-2 border-t border-slate-800 pt-4" data-testid="mentrix-companion-chat">
            {messages.map((m, i) => (
              <div
                key={i}
                className={
                  m.role === "user"
                    ? "ml-8 rounded-lg bg-teal-900/40 border border-teal-800 px-3 py-2 text-sm"
                    : "mr-8 rounded-lg bg-slate-900 border border-slate-800 px-3 py-2 text-sm"
                }
              >
                {m.text}
              </div>
            ))}
            <div ref={chatEnd} />
          </div>

          <div className="mt-3 flex gap-2 items-end">
            <textarea
              data-testid="mentrix-companion-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              rows={2}
              placeholder="Ask Mentrix — status, research, brief, report, open Lattice…"
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
              data-testid="mentrix-companion-mic"
              onClick={toggleListen}
              className={`rounded-lg p-2.5 border ${listening ? "bg-teal-700 border-teal-500" : "border-slate-600"}`}
              title="Voice"
            >
              {listening ? <Mic className="h-5 w-5" /> : <MicOff className="h-5 w-5" />}
            </button>
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
          <label className="mt-2 inline-flex items-center gap-2 text-xs text-slate-400">
            <input type="checkbox" checked={tts} onChange={(e) => setTts(e.target.checked)} />
            Speak replies (TTS)
          </label>
        </div>

        <aside className="space-y-3">
          <div className="rounded-xl border border-slate-200 bg-white p-4" data-testid="mentrix-board">
            <div className="flex items-center gap-2 font-semibold text-slate-900 mb-2">
              <Sparkles className="h-4 w-4 text-teal-700" />
              Mentrix Board
            </div>
            {!board.length && (
              <p className="text-xs text-slate-500">
                Briefs, reports, research citations, and diagnose plans appear here.
              </p>
            )}
            <div className="space-y-3 max-h-[420px] overflow-auto">
              {board.map((item, i) => (
                <article key={i} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                  <h3 className="text-sm font-medium text-slate-800">{item.title || "Artifact"}</h3>
                  <pre className="mt-1 text-[11px] text-slate-600 whitespace-pre-wrap font-sans">
                    {item.body || ""}
                  </pre>
                </article>
              ))}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 text-xs text-slate-600 space-y-1">
            <p className="font-semibold text-slate-800">Quick asks</p>
            {[
              "What's my Mentrix Delivery status?",
              "Open Lattice",
              "Research latest on AI marketing",
              "Draft a content brief for Q3 launch",
              "Go back",
            ].map((q) => (
              <button
                key={q}
                type="button"
                className="block w-full text-left rounded border border-slate-100 px-2 py-1.5 hover:bg-teal-50"
                onClick={() => {
                  setInput(q);
                  setMessages((m) => [...m, { role: "user", text: q }]);
                  runTurn(q);
                }}
              >
                {q}
              </button>
            ))}
          </div>
        </aside>
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
