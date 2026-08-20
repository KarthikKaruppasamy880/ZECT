/**
 * Mentrix OpenAI Realtime Connect Voice client (GA client_secrets + WebSocket).
 * Audio capture uses AudioWorklet (not ScriptProcessor) to avoid Electron renderer freezes.
 */
import { apiFetch, authHeaders, logMentrixExchange } from "@/lib/api";
import { isOpenAiQuotaError } from "@/mentrix/desktopBridge";
import { audioConstraintsForDevice } from "@/lib/micDevices";
import {
  chunkSpeakText,
  createPerfTracker,
  nextSpeakableSentence,
  shouldAppendAssistantTranscript,
  shouldFinalizeClonedResponse,
  clonedRemainderToSpeak,
} from "@/lib/mentrixRealtimeFinalize";
import { registerSpeechCancelListener } from "@/mentrix/speak";

export type RealtimeHandlers = {
  onOrb?: (state: string) => void;
  onLog?: (line: string) => void;
  /** Phase 6 Stage A — surface named latency checkpoints to the HUD */
  onPerfMark?: (mark: { name: string; elapsedMs: number }) => void;
  onTranscript?: (role: "user" | "assistant", text: string) => void;
  onNavigate?: (path: string) => void;
  onArtifact?: (item: Record<string, unknown>) => void;
  onPendingConfirm?: (pending: Array<Record<string, unknown>>) => void;
  onError?: (err: string) => void;
  onFallback?: (reason: string) => void;
  /** Fired when mic + WS are fully ready (or failed before ready) */
  onReady?: (ok: boolean) => void;
  getComputerMode?: () => boolean;
  onDesktopOutput?: (output: string) => void | Promise<void>;
};

export type ClonedVoiceInfo = { voice_id: string; name: string };

export type RealtimePreflight = {
  ready: boolean;
  reason?: string;
  detail?: string;
  api?: string;
  client_secret?: string;
  model?: string;
  openai_ws_url?: string;
  voice?: string;
  cloned_voice?: ClonedVoiceInfo | null;
  /** ZECT Voicebox online at mint — when false, use Realtime PCM even if a clone exists */
  voicebox_online?: boolean;
};

export type RealtimeSessionHandle = {
  stop: () => void;
  mode: "realtime" | "fallback";
  resumeAfterTool: (output: string) => void;
  /** Speak a short cue on the Realtime audio path (not companion chat TTS). */
  speakCue: (text: string) => void;
  ready: Promise<boolean>;
  /** Mentrix-facing provider label (never third-party product names in UI) */
  providerLabel: "realtime" | "fallback";
};

const TARGET_SAMPLE_RATE = 24000;
const MAX_PLAY_QUEUE = 24;

const WORKLET_SRC = `
class MentrixCaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (ch && ch.length) {
      // Copy — underlying buffer is reused by the audio thread.
      this.port.postMessage(ch.slice(0));
    }
    return true;
  }
}
registerProcessor('mentrix-capture', MentrixCaptureProcessor);
`;

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
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
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
      detail: session.detail ? String(session.detail).slice(0, 200) : undefined,
      api: session.api ? String(session.api) : undefined,
    };
  }
  return {
    ready: true,
    client_secret: session.client_secret,
    model: session.model,
    openai_ws_url: session.openai_ws_url,
    voice: session.voice,
    cloned_voice: session.cloned_voice || null,
    voicebox_online: Boolean(session.voicebox_online),
    api: session.api ? String(session.api) : "client_secrets",
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
  const output = data.output || JSON.stringify(data.result || { ok: true });
  if (confirmed && handlers.onDesktopOutput) {
    await handlers.onDesktopOutput(output);
  }
  return output;
}

export type StartMentrixRealtimeOptions = {
  handlers: RealtimeHandlers;
  skipRealtime?: boolean;
  /** Prefer reminting; only reuse when forceReusePreflight is set */
  preflight?: RealtimePreflight;
  forceReusePreflight?: boolean;
  deviceId?: string;
  /** Appended to session instructions (Skills / Dream lessons). */
  extraInstructions?: string;
};

async function attachMicCapture(
  audioCtx: AudioContext,
  mediaStream: MediaStream,
  onPcm: (pcm: ArrayBuffer) => void,
): Promise<{ source: MediaStreamAudioSourceNode; node: AudioNode; dispose: () => void }> {
  const source = audioCtx.createMediaStreamSource(mediaStream);
  const inputRate = audioCtx.sampleRate;
  const mute = audioCtx.createGain();
  mute.gain.value = 0;

  try {
    const blob = new Blob([WORKLET_SRC], { type: "application/javascript" });
    const url = URL.createObjectURL(blob);
    await audioCtx.audioWorklet.addModule(url);
    URL.revokeObjectURL(url);
    const worklet = new AudioWorkletNode(audioCtx, "mentrix-capture");
    worklet.port.onmessage = (ev) => {
      const input = ev.data as Float32Array;
      if (!input?.length) return;
      const resampled = resampleTo24k(input, inputRate);
      onPcm(floatTo16BitPCM(resampled));
    };
    source.connect(worklet);
    worklet.connect(mute);
    mute.connect(audioCtx.destination);
    return {
      source,
      node: worklet,
      dispose: () => {
        try {
          worklet.port.onmessage = null;
          worklet.disconnect();
        } catch {
          /* ignore */
        }
      },
    };
  } catch {
    // Fallback ScriptProcessor — used only if AudioWorklet unavailable.
    const captureNode = audioCtx.createScriptProcessor(8192, 1, 1);
    captureNode.onaudioprocess = (ev) => {
      const input = ev.inputBuffer.getChannelData(0);
      const resampled = resampleTo24k(input, inputRate);
      onPcm(floatTo16BitPCM(resampled));
    };
    source.connect(captureNode);
    captureNode.connect(mute);
    mute.connect(audioCtx.destination);
    return {
      source,
      node: captureNode,
      dispose: () => {
        try {
          captureNode.onaudioprocess = null;
          captureNode.disconnect();
        } catch {
          /* ignore */
        }
      },
    };
  }
}

export async function startMentrixRealtime(
  handlersOrOptions: RealtimeHandlers | StartMentrixRealtimeOptions,
): Promise<RealtimeSessionHandle> {
  const opts: StartMentrixRealtimeOptions =
    "handlers" in handlersOrOptions ? handlersOrOptions : { handlers: handlersOrOptions };
  const handlers = opts.handlers;

  const noopReady = Promise.resolve(false);
  if (opts.skipRealtime) {
    const reason = opts.preflight?.reason || "realtime_unavailable";
    handlers.onFallback?.(String(reason));
    handlers.onLog?.(`realtime_unavailable ${reason}`);
    handlers.onReady?.(false);
    return {
      mode: "fallback",
      providerLabel: "fallback",
      stop: () => undefined,
      resumeAfterTool: () => undefined,
      speakCue: () => undefined,
      ready: noopReady,
    };
  }

  // Always remint unless explicitly reusing — reconnect with stale ek_ keys crashes/fails often.
  let session: Record<string, unknown>;
  if (opts.forceReusePreflight && opts.preflight?.ready && opts.preflight.client_secret) {
    session = {
      realtime_enabled: true,
      client_secret: opts.preflight.client_secret,
      model: opts.preflight.model,
      openai_ws_url: opts.preflight.openai_ws_url,
      voice: opts.preflight.voice,
      cloned_voice: opts.preflight.cloned_voice || null,
      voicebox_online: opts.preflight.voicebox_online,
    };
  } else {
    const sessionRes = await apiFetch("/api/mentrix/companion/realtime/session", { method: "POST" });
    session = await sessionRes.json().catch(() => ({}));
    if (!sessionRes.ok || !session.realtime_enabled || !session.client_secret) {
      const reason = session.reason || session.detail || "realtime_unavailable";
      handlers.onFallback?.(String(reason));
      handlers.onLog?.(`realtime_unavailable ${reason}`);
      handlers.onReady?.(false);
      return {
        mode: "fallback",
        providerLabel: "fallback",
        stop: () => undefined,
        resumeAfterTool: () => undefined,
        speakCue: () => undefined,
        ready: noopReady,
      };
    }
  }

  const clonedVoice = (session.cloned_voice as ClonedVoiceInfo | null) || null;
  const voiceboxOnline = Boolean(session.voicebox_online);
  // Clone TTS only when Voicebox is online — otherwise Realtime PCM stock voice (low latency).
  const clonedVoiceActive = Boolean(clonedVoice) && voiceboxOnline;
  if (clonedVoice && !voiceboxOnline) {
    handlers.onLog?.(
      "ZECT Voicebox offline — using Realtime stock voice for low latency (reconnect after Voicebox is up for your clone)",
    );
  }

  handlers.onLog?.(
    clonedVoiceActive
      ? `Connect Voice — OpenAI Realtime (cloned voice: ${clonedVoice!.name})`
      : "Connect Voice — OpenAI Realtime",
  );
  handlers.onOrb?.("listening");

  const wsUrl =
    (session.openai_ws_url as string) ||
    `wss://api.openai.com/v1/realtime?model=${session.model || "gpt-realtime"}`;
  const ws = new WebSocket(wsUrl, [
    "realtime",
    `openai-insecure-api-key.${session.client_secret}`,
  ]);

  let audioCtx: AudioContext | null = null;
  let mediaStream: MediaStream | null = null;
  let captureDispose: (() => void) | null = null;
  let source: MediaStreamAudioSourceNode | null = null;
  let stopped = false;
  const playQueue: Int16Array[] = [];
  let playing = false;
  const handledCallIds = new Set<string>();
  /** Assigned after enqueueSpeak exists — cues must not use companion chat TTS. */
  let speakCue: (text: string) => void = () => undefined;
  let lastToolSpoken = "";
  let loggedPcmWhileClone = false;
  // The Realtime API allows only one response in flight per conversation at a
  // time. A single turn can include several function calls (e.g. slack_digest
  // for two channels + delivery_status) whose completions race each other —
  // each used to fire its own response.create, and the losers errored with
  // "Conversation already has an active response in progress" and got dropped.
  // responseInFlight is set the instant we send response.create (not on the
  // server's response.created ack, which arrives too late to prevent the
  // race) so at most one is ever outstanding; a second caller just flags
  // pendingResponseCreate and the queued create fires once response.done lands.
  let responseInFlight = false;
  let pendingResponseCreate = false;
  let resolveReady: (ok: boolean) => void = () => undefined;
  const ready = new Promise<boolean>((resolve) => {
    resolveReady = resolve;
  });
  let readySettled = false;
  const settleReady = (ok: boolean) => {
    if (readySettled) return;
    readySettled = true;
    resolveReady(ok);
    handlers.onReady?.(ok);
  };

  /** HTMLAudio for cloned TTS — never decode MP3 into the 24 kHz Realtime AudioContext. */
  let clonedSpeakEl: HTMLAudioElement | null = null;
  let clonedSpeakUrl: string | null = null;
  const SILENT_WAV =
    "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA=";

  const unlockClonedOutput = async () => {
    try {
      const a = new Audio(SILENT_WAV);
      a.setAttribute("playsinline", "true");
      a.volume = 0.01;
      a.style.display = "none";
      document.body.appendChild(a);
      await a.play().catch(() => undefined);
      a.pause();
      a.remove();
    } catch {
      /* ignore */
    }
  };

  const mountClonedAudio = (audio: HTMLAudioElement) => {
    audio.setAttribute("playsinline", "true");
    audio.preload = "auto";
    audio.volume = 1;
    audio.muted = false;
    audio.style.position = "fixed";
    audio.style.width = "0";
    audio.style.height = "0";
    audio.style.opacity = "0";
    audio.style.pointerEvents = "none";
    if (!audio.isConnected) document.body.appendChild(audio);
  };

  const stopClonedSpeakEl = () => {
    try {
      if (clonedSpeakEl) {
        clonedSpeakEl.onended = null;
        clonedSpeakEl.onerror = null;
        clonedSpeakEl.pause();
        clonedSpeakEl.removeAttribute("src");
        clonedSpeakEl.load();
        clonedSpeakEl.remove();
      }
    } catch {
      /* ignore */
    }
    clonedSpeakEl = null;
    if (clonedSpeakUrl) {
      try {
        URL.revokeObjectURL(clonedSpeakUrl);
      } catch {
        /* ignore */
      }
      clonedSpeakUrl = null;
    }
  };

  const unregisterSpeechCancel = registerSpeechCancelListener(stopClonedSpeakEl);

  const requestResponse = () => {
    if (stopped || ws.readyState !== WebSocket.OPEN) return;
    if (responseInFlight) {
      pendingResponseCreate = true;
      return;
    }
    responseInFlight = true;
    ws.send(JSON.stringify({ type: "response.create" }));
  };

  const runFunctionCall = async (name: string, callId: string, rawArgs: unknown) => {
    if (!name || !callId || handledCallIds.has(callId)) return;
    handledCallIds.add(callId);
    handlers.onOrb?.("working");
    let args: Record<string, unknown> = {};
    try {
      args =
        typeof rawArgs === "string"
          ? JSON.parse(rawArgs || "{}")
          : (rawArgs as Record<string, unknown>) || {};
    } catch {
      args = {};
    }
    const output = await executeTool(name, args, false, handlers);
    lastToolSpoken = "";
    try {
      const parsed = JSON.parse(output) as { spoken_summary?: unknown; pending?: unknown };
      if (typeof parsed.spoken_summary === "string" && parsed.spoken_summary.trim()) {
        lastToolSpoken = parsed.spoken_summary.trim();
      }
    } catch {
      /* output may be a plain string */
    }
    if (output.includes('"pending":true')) {
      speakCue("I need your permission to continue.");
    }
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
      requestResponse();
    }
  };

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
    requestResponse();
    handlers.onOrb?.("speaking");
  };

  const stop = () => {
    if (stopped) return;
    stopped = true;
    unregisterSpeechCancel();
    stopClonedSpeakEl();
    sentenceQueue.length = 0;
    lookahead = null;
    for (const c of inFlightAborts) {
      try {
        c.abort();
      } catch {
        /* ignore */
      }
    }
    inFlightAborts.clear();
    try {
      captureDispose?.();
    } catch {
      /* ignore */
    }
    try {
      source?.disconnect();
      mediaStream?.getTracks().forEach((t) => t.stop());
      void audioCtx?.close();
    } catch {
      /* ignore */
    }
    captureDispose = null;
    source = null;
    mediaStream = null;
    audioCtx = null;
    playQueue.length = 0;
    playing = false;
    try {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    } catch {
      /* ignore */
    }
    settleReady(false);
  };

  const playNext = () => {
    if (playing || !playQueue.length || !audioCtx || stopped) return;
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
      if (playQueue.length) playNext();
      else if (!stopped) handlers.onOrb?.("listening");
    };
    try {
      node.start();
    } catch {
      playing = false;
    }
  };

  ws.onopen = async () => {
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: audioConstraintsForDevice(opts.deviceId),
      });
      if (stopped) {
        mediaStream.getTracks().forEach((t) => t.stop());
        settleReady(false);
        return;
      }
      await unlockClonedOutput();
      audioCtx = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE });
      // Some browsers ignore sampleRate hint — always resample from actual rate.
      const attached = await attachMicCapture(audioCtx, mediaStream, (pcm) => {
        if (stopped || ws.readyState !== WebSocket.OPEN) return;
        try {
          ws.send(
            JSON.stringify({
              type: "input_audio_buffer.append",
              audio: arrayBufferToBase64(pcm),
            }),
          );
        } catch {
          /* ignore */
        }
      });
      source = attached.source;
      captureDispose = attached.dispose;
      const audioInputConfig = {
        // Without a language hint, Whisper auto-detects per utterance and its
        // well-documented failure mode on noisy/quiet/ambiguous audio is to
        // hallucinate fluent-looking text in a random wrong language rather
        // than return low-confidence output — pin it so stray mic noise
        // never turns into a bogus foreign-language "turn."
        transcription: { model: "whisper-1", language: "en" },
        turn_detection: {
          type: "server_vad",
          create_response: true,
          interrupt_response: true,
        },
      };
      ws.send(
        JSON.stringify({
          type: "session.update",
          session: clonedVoiceActive
            ? {
                type: "realtime",
                // Lock output to text — OpenAI's own audio synthesis stays off so
                // the cloned voice (via /api/mentrix/voice/speak) is the only thing
                // that speaks. Any audio.output key here — even an empty one — has
                // been observed re-enabling audio synthesis regardless of
                // output_modalities, so it's omitted entirely, not just left voiceless.
                output_modalities: ["text"],
                audio: { input: audioInputConfig },
              }
            : {
                type: "realtime",
                audio: {
                  input: audioInputConfig,
                  // Re-assert the mint-time voice explicitly — if this session.update's
                  // `audio` object were treated as a full replace rather than a merge,
                  // omitting `output` here would silently reset the voice to the API
                  // default mid-conversation instead of keeping MENTRIX_REALTIME_VOICE.
                  output: { voice: (session.voice as string) || "alloy" },
                },
              },
        }),
      );
      // Inject Skills/Dream context without replacing mint-time Mentrix instructions.
      if (opts.extraInstructions?.trim()) {
        try {
          ws.send(
            JSON.stringify({
              type: "conversation.item.create",
              item: {
                type: "message",
                role: "system",
                content: [
                  {
                    type: "input_text",
                    text: opts.extraInstructions.trim().slice(0, 3500),
                  },
                ],
              },
            }),
          );
        } catch {
          /* ignore */
        }
      }
      handlers.onLog?.(
        `Mic open${opts.deviceId ? ` (${opts.deviceId.slice(0, 8)}…)` : " (default)"} · worklet`,
      );
      settleReady(true);
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

  /** One finalize per OpenAI response id — prevents double bubble + double speak. */
  const finalizedResponseIds = new Set<string>();
  /** Streaming text for cloned (text-only) modality — painted before TTS finishes. */
  let clonedTextAcc = "";
  /** How much of clonedTextAcc has already been dispatched to speech — lets
   * complete sentences start synthesizing as they stream in, instead of the
   * whole reply waiting for response.done before any Chatterbox call fires. */
  let clonedSpokenUpTo = 0;
  /** Last thing the user said — paired with the assistant's reply for auto-logging to Notes. */
  let lastUserTranscript = "";

  // --- Latency instrumentation ------------------------------------------
  // Named checkpoints from end-of-user-speech to first audio, so a slow
  // reply is diagnosed from real numbers instead of guessed. perf.reset()
  // fires at user_speech_stopped (the actual point "response time" is
  // measured from); perf.mark() dedupes so only the FIRST occurrence per
  // turn logs (repeat deltas/sentences within one reply would otherwise
  // spam the log with the same checkpoint name).
  const perf = createPerfTracker();
  const markPerf = (name: string) => {
    const m = perf.mark(name);
    if (m) {
      handlers.onLog?.(`perf: ${m.name} at +${m.elapsedMs}ms`);
      handlers.onPerfMark?.(m);
    }
  };

  // --- Barge-in cancellation ---------------------------------------------
  // turnGeneration increments on every new user turn (speech_started) —
  // anything still fetching/queued/playing from a stale generation is
  // dropped instead of talking over the user. inFlightAborts lets a real
  // in-progress /speak HTTP request be cancelled immediately, not just
  // ignored once it resolves.
  let turnGeneration = 0;
  const inFlightAborts = new Set<AbortController>();
  const cancelCurrentTurn = (reason: string) => {
    turnGeneration += 1;
    sentenceQueue.length = 0;
    lookahead = null;
    for (const c of inFlightAborts) {
      try {
        c.abort();
      } catch {
        /* ignore */
      }
    }
    inFlightAborts.clear();
    if (clonedSpeakEl) {
      stopClonedSpeakEl();
      handlers.onLog?.(`Interrupted (${reason}) — stopped speech`);
    }
  };

  type ClonedSpeakBuffer = { buf: ArrayBuffer; engine: string };

  const fetchClonedSpeakBuffer = async (text: string, gen: number): Promise<ClonedSpeakBuffer | null> => {
    if (gen !== turnGeneration || stopped) return null;
    markPerf("tts_request_started");
    const controller = new AbortController();
    inFlightAborts.add(controller);
    try {
      const res = await apiFetch("/api/mentrix/voice/speak", {
        method: "POST",
        body: JSON.stringify({ text: text.slice(0, 4000), require_clone: false }),
        signal: controller.signal,
      });
      if (gen !== turnGeneration) return null;
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        const detail =
          typeof err.detail === "string" ? err.detail : `Speak failed (${res.status})`;
        handlers.onLog?.(`cloned TTS failed: ${detail}`);
        handlers.onError?.(`Voice output: ${detail}`);
        return null;
      }
      // /speak falls back server-side (Chatterbox -> OpenAI) and still returns
      // 200 — this header is the only way to tell your real clone apart from a
      // silent fallback to a generic voice.
      const engine = res.headers.get("X-Mentrix-TTS-Engine") || "unknown";
      const arrayBuf = await res.arrayBuffer();
      if (gen !== turnGeneration) return null;
      markPerf("tts_first_audio_chunk");
      if (!arrayBuf.byteLength) {
        handlers.onError?.("Voice output: empty audio from /voice/speak");
        return null;
      }
      return { buf: arrayBuf, engine };
    } catch (e) {
      if (controller.signal.aborted) return null; // cancelled by barge-in, not a real error
      const msg = e instanceof Error ? e.message : "speak request failed";
      handlers.onLog?.(`cloned TTS failed: ${msg}`);
      handlers.onError?.(`Voice output: ${msg}`);
      return null;
    } finally {
      inFlightAborts.delete(controller);
    }
  };

  const playClonedMpeg = (arrayBuf: ArrayBuffer): Promise<void> =>
    new Promise((resolve, reject) => {
      stopClonedSpeakEl();
      const blob = new Blob([arrayBuf], { type: "audio/mpeg" });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      mountClonedAudio(audio);
      clonedSpeakEl = audio;
      clonedSpeakUrl = url;
      audio.onplaying = () => markPerf("playback_started");
      audio.onended = () => {
        markPerf("playback_finished");
        stopClonedSpeakEl();
        resolve();
      };
      audio.onerror = () => {
        stopClonedSpeakEl();
        reject(new Error("HTMLAudio playback failed"));
      };
      void audio.play().catch(reject);
    });

  const setMicEnabled = (enabled: boolean) => {
    mediaStream?.getAudioTracks().forEach((t) => {
      t.enabled = enabled;
    });
  };

  /**
   * Speak cloned TTS via HTMLAudio only (never decodeAudioData into the 24 kHz
   * Realtime AudioContext — that crashes Electron on Windows).
   *
   * A single persistent queue + lookahead prefetch spans the WHOLE reply
   * (not just one call's worth of chunks): as soon as a queue item starts
   * being awaited, the NEXT queued item's fetch is kicked off immediately
   * too, so its Chatterbox synthesis overlaps with the current item's
   * playback instead of only starting once playback finishes. enqueueSpeak
   * (called per-sentence as text streams in, and once more for the trailing
   * remainder at response.done) just pushes chunkSpeakText(text)'s pieces
   * onto this queue and (re)starts the runner if it's idle.
   *
   * Mic is muted only while audio is actually PLAYING, not while a chunk is
   * being fetched/synthesized: cloned audio plays through a plain <audio>
   * element the Realtime session's server-side VAD has no idea exists, so
   * without muting, your speakers leaking into the mic gets transcribed as
   * new user speech and the model replies to itself (short, generic,
   * back-to-back non-sequiturs — "Bye.", "Have fun. Have fun. Have fun.").
   * Native (non-cloned) audio doesn't need this at all — OpenAI's own
   * pipeline already knows that audio is its own output.
   */
  type QueueItem = { text: string; gen: number };
  const sentenceQueue: QueueItem[] = [];
  let lookahead: { key: QueueItem; promise: Promise<ClonedSpeakBuffer | null> } | null = null;
  let queueRunning = false;
  let pendingSpeakCount = 0;
  const turnEnginesUsed = new Set<string>();

  const startLookahead = () => {
    if (lookahead || !sentenceQueue.length || stopped) return;
    const item = sentenceQueue[0];
    lookahead = { key: item, promise: fetchClonedSpeakBuffer(item.text, item.gen) };
  };

  const runSpeakQueue = async () => {
    if (queueRunning) return;
    queueRunning = true;
    try {
      while (sentenceQueue.length) {
        if (stopped) {
          sentenceQueue.length = 0;
          break;
        }
        const item = sentenceQueue.shift()!;
        if (item.gen !== turnGeneration) {
          pendingSpeakCount = Math.max(0, pendingSpeakCount - 1);
          continue;
        }
        const bufPromise =
          lookahead && lookahead.key === item ? lookahead.promise : fetchClonedSpeakBuffer(item.text, item.gen);
        lookahead = null;
        // Start fetching whatever's next in line right away — overlaps its
        // synthesis with this item's fetch/playback below.
        startLookahead();
        const itemStartedAt = performance.now();
        let buf: ClonedSpeakBuffer | null = null;
        try {
          if (audioCtx?.state === "suspended") await audioCtx.resume().catch(() => undefined);
          buf = await bufPromise;
        } catch {
          buf = null;
        }
        if (item.gen !== turnGeneration || stopped) {
          pendingSpeakCount = Math.max(0, pendingSpeakCount - 1);
          continue;
        }
        if (buf) {
          turnEnginesUsed.add(buf.engine);
          handlers.onOrb?.("speaking");
          setMicEnabled(false);
          try {
            await playClonedMpeg(buf.buf);
          } catch (playErr) {
            const msg = playErr instanceof Error ? playErr.message : "playback failed";
            if (/NotAllowedError|user interaction/i.test(msg)) {
              handlers.onError?.("Voice output blocked — click the Mentrix window, then speak again");
            } else {
              handlers.onError?.(`Voice output: ${msg}`);
            }
          } finally {
            setMicEnabled(true);
          }
          // Per-sentence timing (distinct from the once-per-turn perf marks
          // above) — verifies there's no multi-second gap reappearing at
          // every period, not just on the first sentence of a reply.
          const preview = item.text.length > 40 ? `${item.text.slice(0, 40)}…` : item.text;
          handlers.onLog?.(`sentence spoken in ${Math.round(performance.now() - itemStartedAt)}ms: "${preview}"`);
        }
        pendingSpeakCount = Math.max(0, pendingSpeakCount - 1);
        if (pendingSpeakCount === 0 && !stopped) {
          if (turnEnginesUsed.size) {
            const label = [...turnEnginesUsed].join(" + ");
            const isClone =
              turnEnginesUsed.size === 1 &&
              (turnEnginesUsed.has("zect_voicebox") || turnEnginesUsed.has("chatterbox"));
            handlers.onLog?.(isClone ? "Spoke via your cloned voice" : `Spoke via: ${label} (not your cloned voice)`);
            turnEnginesUsed.clear();
          }
          handlers.onOrb?.("listening");
        }
      }
    } finally {
      queueRunning = false;
    }
  };

  const enqueueSpeak = (text: string) => {
    if (!text.trim() || stopped) return;
    for (const chunk of chunkSpeakText(text)) {
      sentenceQueue.push({ text: chunk, gen: turnGeneration });
      pendingSpeakCount += 1;
    }
    startLookahead();
    void runSpeakQueue();
  };
  speakCue = (text: string) => enqueueSpeak(text);

  ws.onerror = () => {
    handlers.onFallback?.("ws_error");
    stop();
  };

  ws.onclose = () => {
    if (!stopped) handlers.onLog?.("Realtime WS closed");
    settleReady(false);
  };

  ws.onmessage = async (ev) => {
    if (stopped) return;
    let msg: any;
    try {
      msg = JSON.parse(ev.data);
    } catch {
      return;
    }
    const t = msg.type as string;
    if (t === "input_audio_buffer.speech_started") {
      handlers.onOrb?.("listening");
      // Barge-in: a new user turn (interrupting mid-reply, or just starting
      // a fresh one) invalidates whatever was queued/playing/in-flight from
      // before. If nothing was active this is a no-op beyond bumping the
      // generation counter.
      cancelCurrentTurn("user_speech_started");
    }
    if (t === "input_audio_buffer.speech_stopped") {
      // "Response time" is measured from here, not from response.created —
      // this is the actual moment the user is waiting on a reply from.
      perf.reset();
      markPerf("user_speech_stopped");
    }
    if (t === "response.created") {
      responseInFlight = true;
      handlers.onOrb?.("thinking");
      if (clonedVoiceActive) {
        clonedTextAcc = "";
        clonedSpokenUpTo = 0;
      }
      markPerf("llm_request_started");
    }
    // Paint cloned text as it streams so the bubble is not stuck waiting for TTS.
    if (
      clonedVoiceActive &&
      (t === "response.output_text.delta" || t === "response.text.delta") &&
      typeof msg.delta === "string" &&
      msg.delta
    ) {
      markPerf("llm_first_token");
      clonedTextAcc += msg.delta;
      handlers.onTranscript?.("assistant", clonedTextAcc);
      // Speak each completed sentence the instant it streams in, rather than
      // waiting for the whole reply to finish generating — this is the
      // dominant fix for "takes 10s to hear anything": previously Chatterbox
      // synthesis for sentence 1 didn't start until the LLM had also finished
      // generating sentences 2, 3, ... serially adding both times together.
      const unspoken = clonedTextAcc.slice(clonedSpokenUpTo);
      const boundary = nextSpeakableSentence(unspoken);
      if (boundary) {
        clonedSpokenUpTo += boundary.consumedLength;
        enqueueSpeak(boundary.sentence);
      }
    }
    // When cloned voice is active, never play OpenAI stock PCM — Chatterbox /speak is sole TTS.
    if (
      !clonedVoiceActive &&
      (t === "response.output_audio.delta" || t === "response.audio.delta") &&
      msg.delta
    ) {
      if (playQueue.length >= MAX_PLAY_QUEUE) playQueue.shift();
      playQueue.push(base64ToInt16(msg.delta));
      playNext();
    } else if (
      clonedVoiceActive &&
      (t === "response.output_audio.delta" || t === "response.audio.delta")
    ) {
      playQueue.length = 0;
      if (!loggedPcmWhileClone) {
        loggedPcmWhileClone = true;
        handlers.onLog?.("Clone TTS active — discarded Realtime PCM (prevents double voice)");
      }
    }
    const userTranscript = msg.transcript || msg.item?.content?.[0]?.transcript || "";
    if (
      (t === "conversation.item.input_audio_transcription.completed" ||
        t === "conversation.item.input_audio_transcription.done") &&
      userTranscript
    ) {
      markPerf("transcript_final");
      lastUserTranscript = String(userTranscript);
      handlers.onTranscript?.("user", lastUserTranscript);
    }
    // Non-cloned: chat text comes from audio transcript.done.
    // Cloned: wait for response.done (text modality) so we don't double-append.
    if (
      shouldAppendAssistantTranscript({ clonedVoiceActive, eventType: t }) &&
      msg.transcript
    ) {
      handlers.onTranscript?.("assistant", msg.transcript);
    }
    if (t === "response.function_call_arguments.done") {
      await runFunctionCall(msg.name || msg.tool_name, msg.call_id, msg.arguments || "{}");
    }
    if (t === "response.done") {
      responseInFlight = false;
      const responseId = String(msg.response?.id || msg.response_id || "");
      const outputs = msg.response?.output || [];
      for (const item of outputs) {
        if (item?.type !== "function_call" || !item.call_id || !item.name) continue;
        await runFunctionCall(item.name, item.call_id, item.arguments ?? "{}");
      }
      if (
        shouldFinalizeClonedResponse({
          clonedVoiceActive,
          responseId,
          finalizedIds: finalizedResponseIds,
        })
      ) {
        const text =
          outputs
            .filter((item: any) => item?.type === "message")
            .flatMap((item: any) => item.content || [])
            .filter((c: any) => c?.type === "output_text" && c.text)
            .map((c: any) => c.text)
            .join(" ")
            .trim() || clonedTextAcc.trim();
        if (text) {
          handlers.onTranscript?.("assistant", text);
          if (lastUserTranscript) void logMentrixExchange(lastUserTranscript, text);
        }
        if (clonedTextAcc.trim()) {
          const remaining = clonedRemainderToSpeak(clonedTextAcc, clonedSpokenUpTo);
          if (remaining) enqueueSpeak(remaining);
        } else if (lastToolSpoken) {
          enqueueSpeak(lastToolSpoken);
          lastToolSpoken = "";
        } else if (text) {
          enqueueSpeak(text);
        }
        clonedTextAcc = "";
        lastUserTranscript = "";
      }
      if (pendingResponseCreate && !responseInFlight) {
        pendingResponseCreate = false;
        requestResponse();
      }
    }
    if (t === "error") {
      const errMsg = msg.error?.message || "realtime_error";
      handlers.onError?.(errMsg);
      if (isOpenAiQuotaError(errMsg)) {
        handlers.onFallback?.("openai_quota");
      }
    }
  };

  return { mode: "realtime", providerLabel: "realtime", stop, resumeAfterTool, speakCue, ready };
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
