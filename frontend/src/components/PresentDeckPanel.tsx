/**
 * Companion Present Deck — Presenton generate + open PPTX/Zoom (Electron) + narrate (ZECT Voicebox).
 * Electron: parse notes → F5 → speak await → Right Arrow.
 * Browser: upload .pptx → parse via API → narrate each slide (no PowerPoint automation).
 */
import { useEffect, useRef, useState } from "react";
import { Presentation, Mic, MonitorPlay, Sparkles, Square, Upload } from "lucide-react";
import {
  mentrixCompanionIntegrations,
  mentrixPresentonGenerate,
  mentrixPresentonStatus,
  mentrixPresentonTemplates,
  mentrixParsePptx,
  mentrixPresentationAudiences,
  mentrixAnalyzeDeck,
  mentrixPreparePromptDeck,
  listMyClonedVoices,
  mentrixVoiceEngineStatus,
  type ClonedVoiceInfo,
  type PresentonTemplate,
  type VoiceEngineStatus,
} from "@/lib/api";
import { cancelMentrixSpeech, isCloneTtsEngine, speakMentrix, speakMentrixStreamedAwait, prefetchMentrixSpeakChunks, playMentrixPrefetch, capPresentSlideScript, type SpeakVoiceOptions, type PrefetchedSpeakChunk } from "@/mentrix/speak";

const STORAGE_KEY = "zect_mentrix_present_deck_path";
const NOTES_KEY = "zect_mentrix_present_deck_notes";
const PROMPT_KEY = "zect_mentrix_present_deck_prompt";
const JOIN_KEY = "zect_mentrix_zoom_join_url";
const VOICE_CHOICE_KEY = "zect_mentrix_present_deck_voice";
const TEMPLATE_KEY = "mentrix_present_template";
const N_SLIDES_KEY = "mentrix_present_n_slides";
const CUSTOM_TEMPLATE_KEY = "mentrix_present_custom_template";
const CUSTOM_TEMPLATE_OPTION = "__custom__";

const AUDIENCE_KEY = "zect_mentrix_present_audience";
const SENS_KEY = "zect_mentrix_present_sensitivity";

const BUILTIN_TEMPLATES: PresentonTemplate[] = [
  { id: "general", name: "General" },
  { id: "modern", name: "Modern" },
  { id: "standard", name: "Standard" },
  { id: "swift", name: "Swift" },
  { id: "zinnia-exec", name: "Zinnia — Executive brief" },
  { id: "zinnia-delivery", name: "Zinnia — Delivery status" },
  { id: "zinnia-risk", name: "Zinnia — Risk & next actions" },
];

const ZINNIA_PROMPT_PRESETS: Record<string, string> = {
  "zinnia-exec":
    "Zinnia executive brief: title slide, status snapshot, decisions needed, owners, next 7 days.",
  "zinnia-delivery":
    "Zinnia delivery status: workstream health, milestones, blockers, dependencies, ask for leadership.",
  "zinnia-risk":
    "Zinnia risk review: top risks, mitigations, owners, timeline impact, recommended actions.",
};

const STOCK_VOICES: { id: string; label: string }[] = [
  { id: "alloy", label: "OpenAI — Alloy (neutral)" },
  { id: "echo", label: "OpenAI — Echo (male)" },
  { id: "fable", label: "OpenAI — Fable (male, British)" },
  { id: "onyx", label: "OpenAI — Onyx (male, deep)" },
  { id: "nova", label: "OpenAI — Nova (female)" },
  { id: "shimmer", label: "OpenAI — Shimmer (female)" },
];

type Props = {
  variant?: "dark" | "light";
  /** Prefill ZECT template id (e.g. zinnia-exec) when mounted from product Present. */
  initialTemplateId?: string;
};

type SlideParsed = { index: number; notes?: string; text?: string };

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

function friendlyDesktopError(code: string): string {
  const c = String(code || "");
  if (c === "unsupported_presentation_type") {
    return "Need a .pptx/.ppt/.pdf path — strip quotes when pasting from Explorer.";
  }
  if (c === "pptx_required_for_present_all") {
    return "Present all slides requires a .pptx file.";
  }
  if (c === "path_outside_allowlist") {
    return "Path must be under Desktop, Documents, or Downloads (OneDrive OK).";
  }
  if (c === "not_found") return "File not found at that path.";
  if (c === "zoom_not_found") {
    return "Zoom.exe not found — set ZOOM_DESKTOP_PATH or a Zoom join URL.";
  }
  if (c === "invalid_zoom_join_url") return "Join URL must be https://*.zoom.us/…";
  if (c === "computer_mode_off") return "Turn on Computer Mode in Electron first.";
  return c;
}

export default function PresentDeckPanel({ variant = "dark", initialTemplateId }: Props) {
  const [path, setPath] = useState("");
  const [notes, setNotes] = useState("");
  const [prompt, setPrompt] = useState("");
  const [joinUrl, setJoinUrl] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [presenting, setPresenting] = useState(false);
  const [presentonReady, setPresentonReady] = useState(false);
  const [templates, setTemplates] = useState<PresentonTemplate[]>(BUILTIN_TEMPLATES);
  const [templateChoice, setTemplateChoice] = useState(
    () => initialTemplateId || localStorage.getItem(TEMPLATE_KEY) || "general",
  );
  const [customTemplateId, setCustomTemplateId] = useState("");
  const [nSlides, setNSlides] = useState(6);
  const [myVoices, setMyVoices] = useState<ClonedVoiceInfo[]>([]);
  const [voiceChoice, setVoiceChoice] = useState("");
  const [pptxFile, setPptxFile] = useState<File | null>(null);
  const [engineStatus, setEngineStatus] = useState<VoiceEngineStatus | null>(null);
  const [shareApproved, setShareApproved] = useState(false);
  const [audienceId, setAudienceId] = useState("general");
  const [audiences, setAudiences] = useState<Array<{ id: string; label: string; slide_count_hint?: number }>>([]);
  const [sensitivityHint, setSensitivityHint] = useState("");
  const [claimsPreview, setClaimsPreview] = useState<
    Array<{ id: string; claim: string; verification_status: string; present_as_fact?: boolean }>
  >([]);
  const [analysisNote, setAnalysisNote] = useState("");
  const [flowBApproved, setFlowBApproved] = useState(false);
  const abortRef = useRef(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const isDesktop = typeof window !== "undefined" && !!window.zectDesktop?.isDesktopApp;
  const dark = variant === "dark";
  const defaultVoice = myVoices.find((v) => v.is_default) || myVoices[0] || null;
  const [zinniaMasterId, setZinniaMasterId] = useState("");
  const [lastTemplateSent, setLastTemplateSent] = useState("");
  const usingStock = voiceChoice.startsWith("stock:");
  const cloneNarrateBlocked = !usingStock && engineStatus !== null && !engineStatus.online;

  useEffect(() => {
    try {
      setPath(localStorage.getItem(STORAGE_KEY) || "");
      setNotes(localStorage.getItem(NOTES_KEY) || "");
      setPrompt(localStorage.getItem(PROMPT_KEY) || "");
      setJoinUrl(localStorage.getItem(JOIN_KEY) || "");
      setVoiceChoice(localStorage.getItem(VOICE_CHOICE_KEY) || "");
      setAudienceId(localStorage.getItem(AUDIENCE_KEY) || "general");
      setSensitivityHint(localStorage.getItem(SENS_KEY) || "");
      const savedTemplate =
        initialTemplateId || localStorage.getItem(TEMPLATE_KEY) || "general";
      setTemplateChoice(savedTemplate);
      if (initialTemplateId) {
        try {
          localStorage.setItem(TEMPLATE_KEY, initialTemplateId);
        } catch {
          /* ignore */
        }
      }
      setCustomTemplateId(localStorage.getItem(CUSTOM_TEMPLATE_KEY) || "");
      const savedSlides = Number(localStorage.getItem(N_SLIDES_KEY) || "6");
      setNSlides(Number.isFinite(savedSlides) ? Math.max(3, Math.min(20, savedSlides)) : 6);
    } catch {
      /* ignore */
    }
    mentrixPresentonStatus()
      .then((s) => setPresentonReady(!!s.configured && !!s.reachable))
      .catch(() => setPresentonReady(false));
    mentrixCompanionIntegrations()
      .then((s) => {
        if (s.zinnia_presenton_template_id) setZinniaMasterId(s.zinnia_presenton_template_id);
        // Prefer status endpoint for ready; integrations is backup if status fails earlier
        if (s.presenton_reachable != null) {
          setPresentonReady(!!s.presenton_configured && !!s.presenton_reachable);
        } else if (s.presenton != null) {
          setPresentonReady(!!s.presenton);
        }
      })
      .catch(() => {});
    mentrixPresentonTemplates()
      .then((res) => {
        if (res.reachable === false) setPresentonReady(false);
        const remote = Array.isArray(res.templates) && res.templates.length ? res.templates : [];
        const byId = new Map<string, PresentonTemplate>();
        for (const t of [...BUILTIN_TEMPLATES, ...remote]) {
          if (t?.id) byId.set(t.id, t);
        }
        const list = Array.from(byId.values());
        setTemplates(list);
        setTemplateChoice((prev) => {
          if (prev === CUSTOM_TEMPLATE_OPTION) return prev;
          if (list.some((t) => t.id === prev)) return prev;
          return list[0]?.id || "general";
        });
      })
      .catch(() => setTemplates(BUILTIN_TEMPLATES));
    listMyClonedVoices()
      .then((v) => setMyVoices(Array.isArray(v) ? v : []))
      .catch(() => setMyVoices([]));
    mentrixPresentationAudiences()
      .then((res) => setAudiences(Array.isArray(res.audiences) ? res.audiences : []))
      .catch(() =>
        setAudiences([
          { id: "general", label: "General" },
          { id: "executive", label: "Executive" },
          { id: "technical", label: "Technical" },
        ]),
      );
  }, []);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      mentrixVoiceEngineStatus()
        .then((s) => {
          if (!cancelled) setEngineStatus(s);
        })
        .catch(() => {
          if (!cancelled) {
            setEngineStatus({
              online: false,
              base_url: "http://localhost:17493",
              default_voice: null,
              hint: "Could not reach ZECT API for engine status.",
            });
          }
        });
    };
    load();
    const iv = window.setInterval(load, 15000);
    return () => {
      cancelled = true;
      window.clearInterval(iv);
    };
  }, []);

  const persistVoiceChoice = (value: string) => {
    setVoiceChoice(value);
    try {
      localStorage.setItem(VOICE_CHOICE_KEY, value);
    } catch {
      /* ignore */
    }
  };

  const voiceOptsFromChoice = (choice: string): SpeakVoiceOptions => {
    if (choice.startsWith("clone:")) {
      return { voiceId: choice.slice("clone:".length), requireClone: true };
    }
    if (choice.startsWith("stock:")) {
      return { stockVoice: choice.slice("stock:".length), requireClone: false };
    }
    return { requireClone: true };
  };

  const formatSpeakStatus = (
    result: { ok: true; engine: string } | { ok: false; error: string },
    fallbackOk: string,
  ) => {
    if (!result.ok) return result.error;
    if (usingStock) {
      return result.engine.startsWith("openai_stock:")
        ? `Narrating with OpenAI stock voice (${result.engine.replace("openai_stock:", "")}).`
        : `Narrating via ${result.engine}.`;
    }
    if (!isCloneTtsEngine(result.engine)) {
      return `Expected clone TTS (ZECT Voicebox), got ${result.engine} — start local ZECT Voicebox.`;
    }
    return fallbackOk;
  };

  const persistPath = (value: string) => {
    setPath(value);
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch {
      /* ignore */
    }
  };

  const persistNotes = (value: string) => {
    setNotes(value);
    try {
      localStorage.setItem(NOTES_KEY, value);
    } catch {
      /* ignore */
    }
  };

  const persistPrompt = (value: string) => {
    setPrompt(value);
    try {
      localStorage.setItem(PROMPT_KEY, value);
    } catch {
      /* ignore */
    }
  };

  const persistCustomTemplate = (value: string) => {
    setCustomTemplateId(value);
    try {
      localStorage.setItem(CUSTOM_TEMPLATE_KEY, value);
    } catch {
      /* ignore */
    }
  };

  const persistNSlides = (value: number) => {
    const n = Math.max(3, Math.min(20, Math.round(value) || 6));
    setNSlides(n);
    try {
      localStorage.setItem(N_SLIDES_KEY, String(n));
    } catch {
      /* ignore */
    }
  };

  const resolveTemplateId = () => {
    if (templateChoice === CUSTOM_TEMPLATE_OPTION) {
      return customTemplateId.trim() || zinniaMasterId || "general";
    }
    const raw = (templateChoice || "general").trim() || "general";
    // Zinnia presets: use env master or custom id — never claim Zinnia PASS when silently mapping to modern.
    if (raw.startsWith("zinnia-")) {
      const master = customTemplateId.trim() || zinniaMasterId;
      return master || "modern";
    }
    return raw;
  };

  const persistTemplateChoice = (value: string) => {
    setTemplateChoice(value);
    try {
      localStorage.setItem(TEMPLATE_KEY, value);
    } catch {
      /* ignore */
    }
    const preset = ZINNIA_PROMPT_PRESETS[value];
    if (preset) {
      persistPrompt(preset);
    }
  };

  const persistJoin = (value: string) => {
    setJoinUrl(value);
    try {
      localStorage.setItem(JOIN_KEY, value);
    } catch {
      /* ignore */
    }
  };

  const ensureComputerMode = async () => {
    const mentrix = window.zectDesktop?.mentrix;
    if (!mentrix?.setComputerMode) return false;
    await mentrix.setComputerMode(true);
    return true;
  };

  const runComputer = async (action: string, args: Record<string, unknown>) => {
    if (!isDesktop) {
      setStatus("Electron desktop app required to open PowerPoint / Zoom.");
      return { ok: false as const, error: "not_desktop_app" };
    }
    await ensureComputerMode();
    const computer = window.zectDesktop?.mentrix?.computer;
    if (!computer) {
      setStatus("Electron desktop app required to open PowerPoint / Zoom.");
      return { ok: false as const, error: "not_desktop_app" };
    }
    const res = (await computer(action, args)) as {
      ok?: boolean;
      error?: string;
      hint?: string;
      note?: string;
      slides?: SlideParsed[];
      count?: number;
    };
    if (res?.ok === false) {
      const msg = friendlyDesktopError(String(res.error || "desktop_failed"));
      setStatus(res.hint ? `${msg} (${res.hint})` : msg);
      return { ok: false as const, error: String(res.error || "desktop_failed") };
    }
    return {
      ok: true as const,
      note: res.note,
      slides: res.slides,
      count: res.count,
    };
  };

  const generateDeck = async () => {
    setBusy(true);
    setStatus("");
    try {
      if (!presentonReady) {
        setStatus("Presenton not configured — set PRESENTON_BASE_URL and run Presenton Docker (see Integrations).");
        return;
      }
      const content = prompt.trim();
      if (!content) {
        setStatus("Enter a deck prompt (topic + key points) for Presenton.");
        return;
      }
      const template = resolveTemplateId();
      if (templateChoice === CUSTOM_TEMPLATE_OPTION && !customTemplateId.trim()) {
        setStatus("Enter a custom template id (from Presenton uploaded master), or pick a built-in template.");
        return;
      }
      // Flow B: classify → audience → claims → user approval gate before Presenton
      const prep = await mentrixPreparePromptDeck({
        prompt: content,
        audience_id: audienceId,
        sensitivity_hint: sensitivityHint || undefined,
      });
      setClaimsPreview(prep.claims || []);
      setAnalysisNote(
        `Sensitivity ${prep.sensitivity?.sensitivity || "?"} · ${prep.claims?.length || 0} claims · outline ready`,
      );
      if (!prep.ok) {
        setStatus(prep.reason || "Blocked by sensitivity / model route — review classification before generating.");
        return;
      }
      const unverified = (prep.claims || []).filter((c) => c.present_as_fact === false);
      if (prep.requires_user_approval && !flowBApproved) {
        setStatus(
          `Review ${prep.claims?.length || 0} claims (${unverified.length} not presentable as fact), then check “Approve generation” and click Generate again.`,
        );
        return;
      }
      let adapted = prep.adapted_prompt || content;
      if (unverified.length) {
        adapted +=
          "\n\nIMPORTANT: Do not present the following as verified facts:\n" +
          unverified.map((c) => `- ${c.claim}`).join("\n");
      }
      const slidesHint = prep.n_slides_hint || nSlides;
      if (prep.n_slides_hint) persistNSlides(Number(prep.n_slides_hint));
      const out = await mentrixPresentonGenerate({
        content: adapted,
        n_slides: slidesHint,
        template,
        filename: "mentrix-deck.pptx",
      });
      setFlowBApproved(false);
      const sent = out?.template_sent || template;
      setLastTemplateSent(sent);
      if (out?.path) {
        persistPath(out.path);
        const zinniaNote =
          templateChoice.startsWith("zinnia-") && out.zinnia_verified === false
            ? ` Zinnia NOT verified (wire template=${sent}; set ZINNIA_PRESENTON_TEMPLATE_ID or Custom master id).`
            : out.zinnia_verified
              ? ` Zinnia verified (wire template=${sent}).`
              : ` Presenton template_sent=${sent}.`;
        setStatus(
          `Deck saved to ${out.path} (audience: ${audienceId}, template_sent: ${sent}, ${slidesHint} slides).${zinniaNote} Review claims, then Open → Zoom → share approve → Narrate.`,
        );
      } else {
        setStatus("Presenton returned no path — check PRESENTON_BASE_URL and that Presenton Docker is running.");
      }
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Generate deck failed");
    } finally {
      setBusy(false);
    }
  };

  const analyzeExisting = async () => {
    setBusy(true);
    setStatus("");
    try {
      let slides: SlideParsed[] = [];
      if (pptxFile) {
        const parsed = await mentrixParsePptx(pptxFile);
        slides = parsed.slides || [];
      }
      const out = await mentrixAnalyzeDeck({
        slides,
        notes_blob: notes,
        audience_id: audienceId,
        sensitivity_hint: sensitivityHint || undefined,
      });
      setClaimsPreview(out.claims || []);
      setAnalysisNote(
        `Flow A · ${out.sensitivity?.sensitivity || "?"} · claims=${out.claims?.length || 0} · rehearse=${!!out.rehearse_ready}`,
      );
      if (out.ok && out.improved_notes?.length && !notes.trim()) {
        const joined = out.improved_notes.map((n) => n.notes).join("\n\n---\n\n");
        persistNotes(joined.slice(0, 8000));
      }
      setStatus(
        out.ok
          ? `Deck analyzed for ${out.audience?.label || audienceId}. Review claims before presenting.`
          : out.reason || "Analysis blocked",
      );
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Analyze failed");
    } finally {
      setBusy(false);
    }
  };

  const openPresentation = async () => {
    setBusy(true);
    setStatus("");
    try {
      const target = path.trim().replace(/^["']+|["']+$/g, "");
      if (!target) {
        setStatus("Enter a .pptx path under Desktop, Documents, or Downloads (OneDrive OK).");
        return;
      }
      persistPath(target);
      const res = await runComputer("open_presentation", { path: target });
      if (res.ok) {
        setStatus("Opened presentation in PowerPoint. Join your meeting, share PowerPoint, then Narrate.");
      }
    } finally {
      setBusy(false);
    }
  };

  const openZoom = async () => {
    setBusy(true);
    setStatus("");
    try {
      const url = joinUrl.trim();
      const res = await runComputer("open_zoom", url ? { join_url: url } : {});
      if (res.ok) {
        setStatus(
          res.note ||
            "Opened Zoom. Join your meeting, share PowerPoint, then Narrate. (Mentrix does not auto-share.)",
        );
      }
    } finally {
      setBusy(false);
    }
  };

  const narrateNotes = async () => {
    setBusy(true);
    setStatus("");
    try {
      if (cloneNarrateBlocked) {
        setStatus(
          `ZECT Voicebox offline at ${engineStatus?.base_url || "local engine"} — start local engine to narrate in your voice.`,
        );
        return;
      }
      if (!defaultVoice && !usingStock) {
        setStatus("No cloned voice saved — open Voice tab → clone a sample, or pick an OpenAI stock voice.");
      }
      const text =
        notes.trim() ||
        "Mentrix Present Deck. Paste talking points, then Narrate again with your default ZECT Voicebox voice.";
      const result = await speakMentrix(text.slice(0, 2000), true, voiceOptsFromChoice(voiceChoice));
      setStatus(
        formatSpeakStatus(
          result,
          defaultVoice
            ? `Narrating with saved voice “${defaultVoice.name}”.`
            : "Narrating talking points with your clone.",
        ),
      );
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Narrate failed");
    } finally {
      setBusy(false);
    }
  };

  const stopPresentAll = () => {
    abortRef.current = true;
    cancelMentrixSpeech();
    setStatus("Stopped presenting.");
    setPresenting(false);
    setBusy(false);
  };

  const narrateSlideList = async (slides: SlideParsed[], modeLabel: string) => {
    const n = slides.length;
    const scriptFor = (idx: number) => {
      const slide = slides[idx];
      const raw = (slide.notes || slide.text || "").trim() || `Slide ${idx + 1} of ${n}.`;
      return capPresentSlideScript(raw);
    };
    const opts = voiceOptsFromChoice(voiceChoice);
    // Warm Voicebox + prefetch slide 0 before first play (cuts cold-start lag).
    setStatus(`${modeLabel}: warming voice engine…`);
    try {
      await mentrixVoiceEngineStatus({ forceRefresh: true });
    } catch {
      /* best-effort */
    }
    let pendingPrefetch: Promise<PrefetchedSpeakChunk[] | null> | null =
      n > 0 ? prefetchMentrixSpeakChunks(scriptFor(0), opts) : null;

    for (let i = 0; i < slides.length; i++) {
      if (abortRef.current) {
        setStatus("Stopped presenting.");
        return;
      }
      const script = scriptFor(i);
      setStatus(
        `${modeLabel}: slide ${i + 1} / ${n}` +
          (script.endsWith("…") ? " (script capped ~500 chars for clone speed)" : ""),
      );

      // Kick off slide N+1 synthesis while current slide audio plays
      const upcoming =
        i + 1 < n && !abortRef.current
          ? prefetchMentrixSpeakChunks(scriptFor(i + 1), opts)
          : null;

      let spoken;
      if (pendingPrefetch) {
        const chunks = await pendingPrefetch;
        pendingPrefetch = null;
        spoken =
          chunks && chunks.length
            ? await playMentrixPrefetch(chunks, opts)
            : await speakMentrixStreamedAwait(script, true, opts);
      } else {
        spoken = await speakMentrixStreamedAwait(script, true, opts);
      }
      pendingPrefetch = upcoming;

      if (abortRef.current) {
        setStatus("Stopped presenting.");
        return;
      }
      if (!spoken.ok && spoken.error !== "cancelled") {
        setStatus(`Slide ${i + 1}: ${spoken.error}`);
        return;
      }
      if (i < slides.length - 1 && isDesktop) {
        const right = await runComputer("powerpoint_key", { key: "right" });
        if (!right.ok || abortRef.current) {
          if (abortRef.current) setStatus("Stopped presenting.");
          return;
        }
        await sleep(400);
      } else if (i < slides.length - 1) {
        await sleep(350);
      }
    }
    setStatus(
      `Finished presenting ${slides.length} slides${
        isDesktop ? "" : " (audio only — advance slides manually in PowerPoint)"
      }.`,
    );
  };

  const presentAllSlides = async () => {
    abortRef.current = false;
    setPresenting(true);
    setBusy(true);
    setStatus("");

    try {
      if (isDesktop && !shareApproved) {
        setStatus(
          "Approve screen-share first — Mentrix will narrate only after you confirm you will share PowerPoint in Zoom yourself.",
        );
        return;
      }
      if (cloneNarrateBlocked) {
        setStatus(
          `ZECT Voicebox offline at ${engineStatus?.base_url || "local engine"} — start local engine to Present in your voice.`,
        );
        return;
      }
      if (!defaultVoice && !usingStock) {
        setStatus("Clone a voice first (Voice tab) or pick an OpenAI stock voice — Present uses your saved clone.");
      }

      // Browser / no Computer Mode: upload .pptx → API parse → narrate
      if (!isDesktop) {
        if (!pptxFile) {
          setStatus("In browser: choose a .pptx file below, then click Present again. (Electron unlocks PowerPoint F5 + auto-advance.)");
          return;
        }
        setStatus("Parsing PPTX…");
        const parsed = await mentrixParsePptx(pptxFile);
        const slides = parsed.slides || [];
        if (!slides.length) {
          setStatus("No slides found in that .pptx.");
          return;
        }
        await narrateSlideList(slides, "Narrating");
        return;
      }

      const target = path.trim().replace(/^["']+|["']+$/g, "");
      if (!target && !pptxFile) {
        setStatus("Enter a .pptx path or upload a .pptx file.");
        return;
      }

      let slides: SlideParsed[] = [];
      if (pptxFile && (!target || !/\.pptx$/i.test(target))) {
        const parsed = await mentrixParsePptx(pptxFile);
        slides = parsed.slides || [];
      } else {
        if (!/\.pptx$/i.test(target)) {
          setStatus("Present all slides requires a .pptx file.");
          return;
        }
        persistPath(target);
        const parsed = await runComputer("parse_presentation_slides", { path: target });
        if (!parsed.ok) return;
        slides = parsed.slides || [];
        const opened = await runComputer("open_presentation", { path: target });
        if (!opened.ok || abortRef.current) return;
        setStatus(`Starting slideshow (F5)… ${slides.length} slides`);
        await sleep(2000);
        if (abortRef.current) return;
        const f5 = await runComputer("powerpoint_key", { key: "f5" });
        if (!f5.ok || abortRef.current) return;
        await sleep(400);
      }

      if (!slides.length) {
        setStatus("No slides found in that .pptx.");
        return;
      }
      await narrateSlideList(slides, "Presenting");
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Present all failed");
    } finally {
      setPresenting(false);
      setBusy(false);
    }
  };

  const voiceStatusText = (() => {
    if (!defaultVoice) return "No cloned voice saved — clone in Voice tab or pick a stock voice below.";
    if (defaultVoice.sample_missing) {
      return `Voice “${defaultVoice.name}” is in DB but sample file is missing — clone again.`;
    }
    if (defaultVoice.has_sample && !defaultVoice.engine_ready) {
      return `Voice “${defaultVoice.name}” saved (sample OK). ZECT Voicebox will provision on first speak.`;
    }
    return `Voice saved: “${defaultVoice.name}”${defaultVoice.engine_ready ? " (engine ready)" : ""}.`;
  })();

  const engineBannerText = (() => {
    if (!engineStatus) return "Checking ZECT Voicebox…";
    if (engineStatus.online) {
      return `ZECT Voicebox online (${engineStatus.base_url}). Present can narrate with your clone.`;
    }
    return `ZECT Voicebox offline (${engineStatus.base_url}). Start local engine to narrate in your voice — sample in ZECT ≠ engine online.`;
  })();

  return (
    <div
      data-testid="present-deck-panel"
      className={
        dark
          ? "rounded-xl border border-teal-800/50 bg-slate-950/70 p-3 space-y-2"
          : "rounded-xl border border-slate-200 bg-white p-3 space-y-2"
      }
    >
      <div className="flex items-center gap-2">
        <Presentation className={`h-4 w-4 ${dark ? "text-teal-400" : "text-teal-700"}`} />
        <p
          className={`text-[10px] uppercase tracking-[0.2em] ${
            dark ? "text-teal-400" : "text-teal-700"
          }`}
        >
          Present Deck — PPTX + Zoom
        </p>
      </div>
      <p className={`text-[11px] ${dark ? "text-slate-400" : "text-slate-600"}`}>
        {isDesktop
          ? "Electron: open PowerPoint + Zoom, then Present & narrate advances slides (F5 / Right). You share the window in Zoom."
          : "Browser: upload a .pptx to narrate every slide with your clone. For PowerPoint auto-advance, use the Electron desktop app."}
      </p>
      <p
        data-testid="present-deck-voice-status"
        className={`text-[11px] rounded border px-2 py-1 ${
          defaultVoice?.has_sample
            ? dark
              ? "border-teal-800 text-teal-200 bg-teal-950/40"
              : "border-teal-200 text-teal-800 bg-teal-50"
            : dark
              ? "border-amber-800 text-amber-200 bg-amber-950/40"
              : "border-amber-200 text-amber-900 bg-amber-50"
        }`}
      >
        {voiceStatusText}
      </p>
      <p
        data-testid="present-deck-engine-status"
        className={`text-[11px] rounded border px-2 py-1 ${
          engineStatus?.online
            ? dark
              ? "border-emerald-800 text-emerald-200 bg-emerald-950/40"
              : "border-emerald-200 text-emerald-800 bg-emerald-50"
            : dark
              ? "border-amber-800 text-amber-200 bg-amber-950/40"
              : "border-amber-200 text-amber-900 bg-amber-50"
        }`}
        title={engineStatus?.hint || undefined}
      >
        {engineBannerText}
      </p>
      <label className={`block text-xs ${dark ? "text-slate-300" : "text-slate-700"}`}>
        Generate deck prompt (Presenton)
        <textarea
          data-testid="present-deck-prompt"
          value={prompt}
          onChange={(e) => persistPrompt(e.target.value)}
          rows={2}
          placeholder="Q2 ZOAS delivery brief: status, risks, next actions…"
          className={
            dark
              ? "mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100"
              : "mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-xs"
          }
        />
      </label>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <label className={`block text-xs ${dark ? "text-slate-300" : "text-slate-700"}`}>
          Template
          <select
            data-testid="present-deck-template"
            value={templateChoice}
            onChange={(e) => persistTemplateChoice(e.target.value)}
            className={
              dark
                ? "mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100"
                : "mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-xs"
            }
          >
            {templates.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
            <option value={CUSTOM_TEMPLATE_OPTION}>Custom template id…</option>
          </select>
        </label>
        <label className={`block text-xs ${dark ? "text-slate-300" : "text-slate-700"}`}>
          Slides (3–20)
          <input
            data-testid="present-deck-n-slides"
            type="number"
            min={3}
            max={20}
            value={nSlides}
            onChange={(e) => persistNSlides(Number(e.target.value))}
            className={
              dark
                ? "mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100"
                : "mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-xs"
            }
          />
        </label>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <label className={`block text-xs ${dark ? "text-slate-300" : "text-slate-700"}`}>
          Audience
          <select
            data-testid="present-deck-audience"
            value={audienceId}
            onChange={(e) => {
              const v = e.target.value;
              setAudienceId(v);
              try {
                localStorage.setItem(AUDIENCE_KEY, v);
              } catch {
                /* ignore */
              }
            }}
            className={
              dark
                ? "mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100"
                : "mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-xs"
            }
          >
            {(audiences.length
              ? audiences
              : [
                  { id: "general", label: "General" },
                  { id: "executive", label: "Executive" },
                  { id: "manager", label: "Manager" },
                  { id: "technical", label: "Technical" },
                ]
            ).map((a) => (
              <option key={a.id} value={a.id}>
                {a.label}
              </option>
            ))}
          </select>
        </label>
        <label className={`block text-xs ${dark ? "text-slate-300" : "text-slate-700"}`}>
          Sensitivity hint
          <select
            data-testid="present-deck-sensitivity"
            value={sensitivityHint}
            onChange={(e) => {
              const v = e.target.value;
              setSensitivityHint(v);
              try {
                localStorage.setItem(SENS_KEY, v);
              } catch {
                /* ignore */
              }
            }}
            className={
              dark
                ? "mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100"
                : "mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-xs"
            }
          >
            <option value="">Auto-detect</option>
            <option value="PUBLIC">PUBLIC</option>
            <option value="INTERNAL">INTERNAL</option>
            <option value="CONFIDENTIAL">CONFIDENTIAL</option>
            <option value="RESTRICTED">RESTRICTED</option>
          </select>
        </label>
      </div>
      {analysisNote && (
        <p className={`text-[11px] ${dark ? "text-slate-400" : "text-slate-600"}`} data-testid="present-deck-analysis-note">
          {analysisNote}
        </p>
      )}
      {claimsPreview.length > 0 && (
        <div
          className={`max-h-28 overflow-auto rounded border px-2 py-1 text-[10px] ${
            dark ? "border-slate-700 text-slate-300" : "border-slate-200 text-slate-700"
          }`}
          data-testid="present-deck-claims"
        >
          {claimsPreview.slice(0, 8).map((c) => (
            <div key={c.id}>
              [{c.verification_status}] {c.claim.slice(0, 120)}
              {c.present_as_fact ? "" : " — not as fact"}
            </div>
          ))}
        </div>
      )}
      <label
        className={`inline-flex items-center gap-1.5 text-xs ${dark ? "text-slate-300" : "text-slate-700"}`}
        data-testid="present-deck-flow-b-approve"
      >
        <input
          type="checkbox"
          checked={flowBApproved}
          onChange={(e) => setFlowBApproved(e.target.checked)}
          className="rounded border-slate-500"
        />
        Approve generation (Flow B — review claims first)
      </label>
      {templateChoice === CUSTOM_TEMPLATE_OPTION && (
        <label className={`block text-xs ${dark ? "text-slate-300" : "text-slate-700"}`}>
          Custom template id (Presenton master)
          <input
            data-testid="present-deck-custom-template"
            value={customTemplateId}
            onChange={(e) => persistCustomTemplate(e.target.value)}
            placeholder="e.g. zinnia-brand-master"
            className={
              dark
                ? "mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100"
                : "mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-xs"
            }
          />
        </label>
      )}
      <button
        type="button"
        data-testid="present-deck-generate"
        disabled={busy || !presentonReady}
        onClick={() => void generateDeck()}
        className="inline-flex items-center gap-1.5 rounded-lg border border-violet-700 px-2.5 py-1.5 text-xs text-violet-200 hover:bg-violet-950 disabled:opacity-40"
        title={
          presentonReady
            ? "Calls PRESENTON_BASE_URL generate API with selected template"
            : "Presenton unreachable — set PRESENTON_BASE_URL and start Presenton Docker"
        }
      >
        <Sparkles className="h-3.5 w-3.5" />
        Generate deck
      </button>
      {lastTemplateSent && (
        <p className={`text-[10px] mt-1 ${dark ? "text-slate-500" : "text-slate-500"}`} data-testid="present-deck-template-sent">
          Last Presenton template_sent: {lastTemplateSent}
          {zinniaMasterId ? ` · ZINNIA_PRESENTON_TEMPLATE_ID=${zinniaMasterId}` : ""}
        </p>
      )}
      <button
        type="button"
        data-testid="present-deck-analyze"
        disabled={busy}
        onClick={() => void analyzeExisting()}
        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 px-2.5 py-1.5 text-xs text-slate-200 hover:bg-slate-800 disabled:opacity-40 ml-2"
        title="Flow A: classify + audience + claims for existing notes/upload"
      >
        Analyze deck
      </button>
      <p className={`text-[11px] ${dark ? "text-slate-500" : "text-slate-500"}`}>
        Pick template + slides, then Generate. Open presentation / Open Zoom need Electron. Clone narrate needs
        ZECT Voicebox online (or pick an OpenAI stock voice).
      </p>
      <label className={`block text-xs ${dark ? "text-slate-300" : "text-slate-700"}`}>
        Presentation path (.pptx){isDesktop ? "" : " — optional in browser; prefer upload below"}
        <input
          data-testid="present-deck-path"
          value={path}
          onChange={(e) => persistPath(e.target.value)}
          placeholder="C:\\Users\\you\\Documents\\deck.pptx"
          className={
            dark
              ? "mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100"
              : "mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-xs"
          }
        />
      </label>
      <label className={`block text-xs ${dark ? "text-slate-300" : "text-slate-700"}`}>
        Upload .pptx (required for Present in browser)
        <input
          ref={fileInputRef}
          data-testid="present-deck-file"
          type="file"
          accept=".pptx,application/vnd.openxmlformats-officedocument.presentationml.presentation"
          className="mt-1 block w-full text-xs file:mr-2 file:rounded file:border-0 file:bg-teal-800 file:px-2 file:py-1 file:text-teal-50"
          onChange={(e) => {
            const f = e.target.files?.[0] || null;
            setPptxFile(f);
            if (f) setStatus(`Ready: ${f.name}`);
          }}
        />
      </label>
      {pptxFile && (
        <p className={`text-[11px] ${dark ? "text-slate-400" : "text-slate-600"}`}>
          Selected: {pptxFile.name}
        </p>
      )}
      <label className={`block text-xs ${dark ? "text-slate-300" : "text-slate-700"}`}>
        Zoom join URL (optional)
        <input
          data-testid="present-deck-zoom-join"
          value={joinUrl}
          onChange={(e) => persistJoin(e.target.value)}
          placeholder="https://zoom.us/j/…"
          className={
            dark
              ? "mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100"
              : "mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-xs"
          }
        />
      </label>
      <label className={`block text-xs ${dark ? "text-slate-300" : "text-slate-700"}`}>
        Manual script (separate from your .pptx — typed here, not read from the file)
        <textarea
          data-testid="present-deck-notes"
          value={notes}
          onChange={(e) => persistNotes(e.target.value)}
          rows={3}
          placeholder="Key points to narrate with your cloned voice — this text is NOT pulled from the PPTX above…"
          className={
            dark
              ? "mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100"
              : "mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-xs"
          }
        />
      </label>
      <label className={`block text-xs ${dark ? "text-slate-300" : "text-slate-700"}`}>
        Narration voice
        <select
          data-testid="present-deck-voice-select"
          value={voiceChoice}
          onChange={(e) => persistVoiceChoice(e.target.value)}
          className={
            dark
              ? "mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100"
              : "mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-xs"
          }
        >
          <option value="">
            {defaultVoice ? `My default — ${defaultVoice.name}` : "My default cloned voice (none saved)"}
          </option>
          {myVoices.map((v) => (
            <option key={v.voice_id} value={`clone:${v.voice_id}`}>
              My voice — {v.name}
              {v.is_default ? " (default)" : ""}
              {!v.has_sample ? " — sample missing" : ""}
            </option>
          ))}
          {STOCK_VOICES.map((v) => (
            <option key={v.id} value={`stock:${v.id}`}>
              {v.label}
            </option>
          ))}
        </select>
      </label>
      <p className={`text-[10px] ${dark ? "text-slate-500" : "text-slate-500"}`} data-testid="present-slide-cap-hint">
        Present uses your clone and caps each slide script (~500 chars). Next-slide audio prefetches while the
        current slide plays. Warm Voicebox (`models_ready: true`) before demos.
      </p>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          data-testid="present-deck-open-pptx"
          disabled={busy || !isDesktop}
          onClick={() => void openPresentation()}
          className="inline-flex items-center gap-1.5 rounded-lg border border-teal-700 px-2.5 py-1.5 text-xs text-teal-200 hover:bg-teal-950 disabled:opacity-40"
          title={isDesktop ? "Open in PowerPoint" : "Electron only"}
        >
          <MonitorPlay className="h-3.5 w-3.5" />
          Open presentation
        </button>
        <button
          type="button"
          data-testid="present-deck-open-zoom"
          disabled={busy || !isDesktop}
          onClick={() => void openZoom()}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 px-2.5 py-1.5 text-xs text-slate-200 hover:bg-slate-800 disabled:opacity-40"
          title={isDesktop ? "Open Zoom" : "Electron only"}
        >
          Open Zoom
        </button>
        {isDesktop && (
          <label
            className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs cursor-pointer ${
              shareApproved
                ? "border-amber-500 bg-amber-900/30 text-amber-100"
                : "border-slate-600 text-slate-300"
            }`}
            data-testid="present-deck-share-approve"
          >
            <input
              type="checkbox"
              checked={shareApproved}
              onChange={(e) => setShareApproved(e.target.checked)}
              className="rounded border-slate-500"
            />
            I will share PowerPoint in Zoom (Mentrix does not auto-share)
          </label>
        )}
        <button
          type="button"
          data-testid="present-deck-narrate"
          disabled={busy || cloneNarrateBlocked}
          onClick={() => void narrateNotes()}
          className="inline-flex items-center gap-1.5 rounded-lg bg-teal-700 px-2.5 py-1.5 text-xs text-white hover:bg-teal-600 disabled:opacity-40"
          title={
            cloneNarrateBlocked
              ? "Start local ZECT Voicebox to narrate with your clone (or pick a stock voice)"
              : "Speaks the Manual script text above — does not read your .pptx file"
          }
        >
          <Mic className="h-3.5 w-3.5" />
          Narrate manual script (not the PPTX)
        </button>
        <button
          type="button"
          data-testid="present-deck-present-all"
          disabled={busy || cloneNarrateBlocked || (isDesktop && !shareApproved)}
          onClick={() => void presentAllSlides()}
          className="inline-flex items-center gap-1.5 rounded-lg border border-amber-500 bg-amber-900/40 px-2.5 py-1.5 text-xs text-amber-50 hover:bg-amber-900 disabled:opacity-40"
          title={
            isDesktop && !shareApproved
              ? "Approve screen-share first"
              : cloneNarrateBlocked
                ? "Start local ZECT Voicebox to Present with your clone (or pick a stock voice)"
                : isDesktop
                  ? "Reads slide text + speaker notes, opens PowerPoint, F5, narrates, advances with Right Arrow"
                  : "Upload a .pptx then narrate every slide with your clone (advance slides yourself in PowerPoint)"
          }
        >
          <Presentation className="h-3.5 w-3.5" />
          Present &amp; narrate my PPTX (all slides)
        </button>
        {!pptxFile && !isDesktop && (
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 px-2.5 py-1.5 text-xs text-slate-200 hover:bg-slate-800"
          >
            <Upload className="h-3.5 w-3.5" />
            Choose PPTX
          </button>
        )}
        {presenting && (
          <button
            type="button"
            data-testid="present-deck-stop"
            onClick={stopPresentAll}
            className="inline-flex items-center gap-1.5 rounded-lg border border-red-700 px-2.5 py-1.5 text-xs text-red-200 hover:bg-red-950"
          >
            <Square className="h-3.5 w-3.5" />
            Stop presenting
          </button>
        )}
      </div>
      {status && (
        <p
          data-testid="present-deck-status"
          className={`text-[11px] ${dark ? "text-amber-300/90" : "text-amber-800"}`}
        >
          {status}
        </p>
      )}
    </div>
  );
}
