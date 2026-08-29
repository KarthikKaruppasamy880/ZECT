/** Client-side voice transcript gating — reject echo and ambient fragments. */

const ECHO_PHRASES = [
  "hey mentrix",
  "mentrix engage",
  "wake mentrix",
  "hey matrix",
  "mentrix ready",
  "how can i help",
  "how can i help you",
  "i'm here and ready",
  "good to see you",
];

export function stripEchoPhrases(text: string): string {
  let t = text.trim();
  for (const p of ECHO_PHRASES) {
    const lower = t.toLowerCase();
    if (lower.startsWith(p)) t = t.slice(p.length).trim();
    t = t.replace(new RegExp(p, "gi"), "").trim();
  }
  return t.replace(/^[,.\s-]+|[,.\s-]+$/g, "").trim();
}

const SHORT_GREETINGS = new Set(["hi", "hello", "hey", "yo", "thanks", "thank you", "ok", "okay"]);

export function passesVoiceGate(text: string): boolean {
  const t = stripEchoPhrases(text);
  if (!t) return false;
  const lower = t.toLowerCase();
  if (SHORT_GREETINGS.has(lower)) return true;
  if (t.length < 4) return false;
  const words = t.split(/\s+/).filter(Boolean);
  if (words.length < 2) return false;
  if (words.length === 2 && t.length < 12) return false;
  if (words.length === 3 && t.length < 12) return false;
  if (words.length < 3 && t.length < 16) return false;
  return true;
}

export function stageVoiceText(raw: string): string | null {
  const t = stripEchoPhrases(raw);
  if (!passesVoiceGate(t)) return null;
  return t;
}
