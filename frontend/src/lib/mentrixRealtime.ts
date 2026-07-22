/**
 * Mentrix OpenAI Realtime Connect Voice client.
 * Uses ephemeral client_secret from Mentrix backend; tools go through Mentrix broker.
 */
import { apiFetch, authHeaders } from "@/lib/api";

export type RealtimeHandlers = {
  onOrb?: (state: string) => void;
  onLog?: (line: string) => void;
  onTranscript?: (role: "user" | "assistant", text: string) => void;
  onNavigate?: (path: string) => void;
  onArtifact?: (item: Record<string, unknown>) => void;
  onPendingConfirm?: (pending: Array<Record<string, unknown>>) => void;
  onError?: (err: string) => void;
  onFallback?: (reason: string) => void;
};

export type RealtimePreflight = {
  ready: boolean;
  reason?: string;
  client_secret?: string;
  model?: string;
  openai_ws_url?: string;
};

export type RealtimeSessionHandle = {
  stop: () => void;
  mode: "realtime" | "fallback";
  resumeAfterTool: (output: string) => void;
};

const TARGET_SAMPLE_RATE = 24000;

function floatTo16BitPCM(float32: Float32Array): ArrayBuffer {
  const buf = new ArrayBuffer(float32.length * 2);
  const view = new DataView(buf);
  for (let i = 0; i < float32.length; i++) {
    let s = Math.max(-1, Math.min(1, float32[i]));
    view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return buf;
}

function resampleTo24k(input: Float32Array, inputRate: number): Float32Array {
  if (inputRate === TARGET_SAMPLE_RATE) return input;
  const ratio = inputRate / TARGET_SAMPLE_RATE;
  const outLen = Math.max(1, Math.floor(input.length / ratio));
  const out = new Float32Array(outLen);
  for (let i = 0; i < outLen; i++) {
    const srcIdx = i * ratio;
    const idx = Math.floor(srcIdx);
    const frac = srcIdx - idx;
    const a = input[idx] ?? 0;
    const b = input[idx + 1] ?? a;
    out[i] = a + (b - a) * frac;
  }
  return out;
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}

function base64ToInt16(b64: string): Int16Array {
  const binary = atob(b64);
  const buf = new ArrayBuffer(binary.length);
  const view = new Uint8Array(buf);
  for (let i = 0; i < binary.length; i++) view[i] = binary.charCodeAt(i);
  return new Int16Array(buf);
}

/** Preflight Realtime session mint without opening mic/WS. */
export async function probeMentrixRealtimePreflight(): Promise<RealtimePreflight> {
  const sessionRes = await apiFetch("/api/mentrix/companion/realtime/session", { method: "POST" });
  const session = await sessionRes.json().catch(() => ({}));
  if (!sessionRes.ok || !session.realtime_enabled || !session.client_secret) {
    return {
      ready: false,
      reason: String(session.reason || session.detail || "realtime_unavailable"),
    };
  }
  return {
    ready: true,
    client_secret: session.client_secret,
    model: session.model,
    openai_ws_url: session.openai_ws_url,
  };
}

async function executeTool(
  tool: string,
  args: Record<string, unknown>,
  confirmed: boolean,
  handlers: RealtimeHandlers,
): Promise<string> {
  const res = await apiFetch("/api/mentrix/companion/realtime/tool", {
    method: "POST",
    body: JSON.stringify({
      tool,
      args,
      confirmed,
      project_key: localStorage.getItem("zect_lattice_key") || "",
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    handlers.onError?.(data.detail || "Tool failed");
    return JSON.stringify({ ok: false, error: data.detail || "tool_failed" });
  }
  for (const ev of data.events || []) {
    if (ev.event === "navigate" && ev.data?.path) handlers.onNavigate?.(ev.data.path);
    if (ev.event === "artifact") handlers.onArtifact?.(ev.data || {});
    if (ev.event === "tool_start") handlers.onLog?.(`Tool: ${ev.data?.tool}`);
    if (ev.event === "pending_confirm") handlers.onOrb?.("needs_permission");
  }
  if (data.pending && data.pending_confirmations?.length) {
    handlers.onPendingConfirm?.(data.pending_confirmations);
    return JSON.stringify({ ok: false, pending: true, tool });
  }
  return data.output || JSON.stringify(data.result || { ok: true });
}

export type StartMentrixRealtimeOptions = {
  handlers: RealtimeHandlers;
  /** Skip WS when preflight already failed — go straight to fallback */
  skipRealtime?: boolean;
  /** Reuse preflight session to avoid duplicate mint */
  preflight?: RealtimePreflight;
};

export async function startMentrixRealtime(
  handlersOrOptions: RealtimeHandlers | StartMentrixRealtimeOptions,
): Promise<RealtimeSessionHandle> {
  const opts: StartMentrixRealtimeOptions =
    "handlers" in handlersOrOptions ? handlersOrOptions : { handlers: handlersOrOptions };
  const handlers = opts.handlers;

  if (opts.skipRealtime) {
    const reason = opts.preflight?.reason || "realtime_unavailable";
    handlers.onFallback?.(String(reason));
    handlers.onLog?.(`realtime_fallback ${reason}`);
    return { mode: "fallback", stop: () => undefined, resumeAfterTool: () => undefined };
  }

  let session: Record<string, unknown>;
  if (opts.preflight?.ready && opts.preflight.client_secret) {
    session = {
      realtime_enabled: true,
      client_secret: opts.preflight.client_secret,
      model: opts.preflight.model,
      openai_ws_url: opts.preflight.openai_ws_url,
    };
  } else {
    const sessionRes = await apiFetch("/api/mentrix/companion/realtime/session", { method: "POST" });
    session = await sessionRes.json().catch(() => ({}));
    if (!sessionRes.ok || !session.realtime_enabled || !session.client_secret) {
      const reason = session.reason || session.detail || "realtime_unavailable";
      handlers.onFallback?.(String(reason));
      handlers.onLog?.(`realtime_fallback ${reason}`);
      return { mode: "fallback", stop: () => undefined, resumeAfterTool: () => undefined };
    }
  }

  handlers.onLog?.("Connect Voice — OpenAI Realtime");
  handlers.onOrb?.("listening");

  const wsUrl =
    (session.openai_ws_url as string) ||
    `wss://api.openai.com/v1/realtime?model=${session.model}`;
  const ws = new WebSocket(wsUrl, [
    "realtime",
    `openai-insecure-api-key.${session.client_secret}`,
    "openai-beta.realtime-v1",
  ]);

  let audioCtx: AudioContext | null = null;
  let mediaStream: MediaStream | null = null;
  let captureNode: ScriptProcessorNode | null = null;
  let source: MediaStreamAudioSourceNode | null = null;
  let stopped = false;
  const playQueue: Int16Array[] = [];
  let playing = false;

  const resumeAfterTool = (output: string) => {
    if (stopped || ws.readyState !== WebSocket.OPEN) return;
    ws.send(
      JSON.stringify({
        type: "conversation.item.create",
        item: {
          type: "message",
          role: "user",
          content: [{ type: "input_text", text: `Tool result: ${output.slice(0, 3500)}` }],
        },
      }),
    );
    ws.send(JSON.stringify({ type: "response.create" }));
    handlers.onOrb?.("speaking");
  };

  const stop = () => {
    stopped = true;
    try {
      ws.close();
    } catch {
      /* ignore */
    }
    try {
      captureNode?.disconnect();
      source?.disconnect();
      mediaStream?.getTracks().forEach((t) => t.stop());
      void audioCtx?.close();
    } catch {
      /* ignore */
    }
  };

  const playNext = async () => {
    if (playing || !playQueue.length || !audioCtx) return;
    playing = true;
    handlers.onOrb?.("speaking");
    const chunk = playQueue.shift()!;
    const float = new Float32Array(chunk.length);
    for (let i = 0; i < chunk.length; i++) float[i] = chunk[i] / 0x8000;
    const buf = audioCtx.createBuffer(1, float.length, TARGET_SAMPLE_RATE);
    buf.copyToChannel(float, 0);
    const node = audioCtx.createBufferSource();
    node.buffer = buf;
    node.connect(audioCtx.destination);
    node.onended = () => {
      playing = false;
      if (playQueue.length) void playNext();
      else if (!stopped) handlers.onOrb?.("listening");
    };
    node.start();
  };

  ws.onopen = async () => {
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioCtx = new AudioContext();
      const inputRate = audioCtx.sampleRate;
      source = audioCtx.createMediaStreamSource(mediaStream);
      captureNode = audioCtx.createScriptProcessor(4096, 1, 1);
      captureNode.onaudioprocess = (ev) => {
        if (stopped || ws.readyState !== WebSocket.OPEN) return;
        const input = ev.inputBuffer.getChannelData(0);
        const resampled = resampleTo24k(input, inputRate);
        const pcm = floatTo16BitPCM(resampled);
        ws.send(
          JSON.stringify({
            type: "input_audio_buffer.append",
            audio: arrayBufferToBase64(pcm),
          }),
        );
      };
      source.connect(captureNode);
      captureNode.connect(audioCtx.destination);
      ws.send(
        JSON.stringify({
          type: "session.update",
          session: {
            turn_detection: { type: "server_vad" },
            input_audio_transcription: { model: "whisper-1" },
          },
        }),
      );
    } catch (e) {
      const msg = e instanceof Error ? e.message : "mic_failed";
      if (msg.toLowerCase().includes("permission") || msg.toLowerCase().includes("denied")) {
        handlers.onError?.("realtime_mic_denied");
      } else {
        handlers.onError?.("realtime_audio_context_failed");
      }
      handlers.onFallback?.("mic_failed");
      stop();
    }
  };

  ws.onerror = () => {
    handlers.onFallback?.("ws_error");
    stop();
  };

  ws.onclose = () => {
    if (!stopped) handlers.onLog?.("Realtime WS closed");
  };

  ws.onmessage = async (ev) => {
    let msg: any;
    try {
      msg = JSON.parse(ev.data);
    } catch {
      return;
    }
    const t = msg.type as string;
    if (t === "input_audio_buffer.speech_started") handlers.onOrb?.("listening");
    if (t === "response.created") handlers.onOrb?.("thinking");
    if (t === "response.audio.delta" && msg.delta) {
      playQueue.push(base64ToInt16(msg.delta));
      void playNext();
    }
    if (t === "conversation.item.input_audio_transcription.completed" && msg.transcript) {
      handlers.onTranscript?.("user", msg.transcript);
    }
    if (t === "response.audio_transcript.done" && msg.transcript) {
      handlers.onTranscript?.("assistant", msg.transcript);
    }
    if (t === "response.function_call_arguments.done") {
      handlers.onOrb?.("working");
      const name = msg.name || msg.tool_name;
      let args: Record<string, unknown> = {};
      try {
        args = JSON.parse(msg.arguments || "{}");
      } catch {
        args = {};
      }
      const callId = msg.call_id;
      const output = await executeTool(name, args, false, handlers);
      if (ws.readyState === WebSocket.OPEN && !output.includes('"pending":true')) {
        ws.send(
          JSON.stringify({
            type: "conversation.item.create",
            item: {
              type: "function_call_output",
              call_id: callId,
              output,
            },
          }),
        );
        ws.send(JSON.stringify({ type: "response.create" }));
      }
    }
    if (t === "error") {
      handlers.onError?.(msg.error?.message || "realtime_error");
    }
  };

  return { mode: "realtime", stop, resumeAfterTool };
}

/** Confirm pending tools from Realtime Allow overlay. */
export async function confirmRealtimeTools(
  tools: string[],
  argsByTool: Record<string, Record<string, unknown>>,
  handlers: RealtimeHandlers,
): Promise<string[]> {
  const outputs: string[] = [];
  for (const tool of tools) {
    const out = await executeTool(tool, argsByTool[tool] || {}, true, handlers);
    outputs.push(out);
  }
  return outputs;
}

export function mentrixRealtimeWsUrl(): string {
  const api = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
  const wsBase = api.replace(/^http/, "ws");
  const token = typeof localStorage !== "undefined" ? localStorage.getItem("zect_token") : "";
  return `${wsBase}/api/mentrix/companion/realtime?token=${encodeURIComponent(token || "")}`;
}

void authHeaders;
