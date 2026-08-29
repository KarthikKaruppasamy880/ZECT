"""Filter junk / echo fragments from Mentrix voice transcripts."""

from __future__ import annotations

import re

ECHO_PHRASES = (
    "hey mentrix",
    "mentrix engage",
    "wake mentrix",
    "hey matrix",
    "mentrix ready",
    "how can i help",
    "how can i help you",
    "i'm here and ready",
    "good to see you",
)


def strip_echo_phrases(text: str) -> str:
    t = str(text or "").strip()
    for phrase in ECHO_PHRASES:
        lower = t.lower()
        if lower.startswith(phrase):
            t = t[len(phrase) :].strip()
        t = re.sub(re.escape(phrase), "", t, flags=re.IGNORECASE).strip()
    return re.sub(r"^[,.\s-]+|[,.\s-]+$", "", t).strip()


_SHORT_GREETINGS = frozenset({"hi", "hello", "hey", "yo", "thanks", "thank you", "ok", "okay"})


def passes_voice_gate(text: str) -> bool:
    t = strip_echo_phrases(text)
    if not t:
        return False
    if t.lower() in _SHORT_GREETINGS:
        return True
    if len(t) < 4:
        return False
    words = [w for w in t.split() if w]
    if len(words) < 2:
        return False
    if len(words) == 2 and len(t) < 12:
        return False
    if len(words) == 3 and len(t) < 12:
        return False
    if len(words) < 3 and len(t) < 16:
        return False
    return True


def stage_voice_text(raw: str) -> str | None:
    t = strip_echo_phrases(raw)
    if not passes_voice_gate(t):
        return None
    return t
