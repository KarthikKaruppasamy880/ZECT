"""Grounded Presenter Intelligence — explain a slide from notes/text/visuals. No invented numbers."""

from __future__ import annotations

from typing import Any

MAX_WORDS = 220


def _words(text: str) -> list[str]:
    return [w for w in (text or "").split() if w]


def grounded_slide_script(slide: dict[str, Any], *, deck_context: str = "", slide_index: int = 0, slide_count: int = 1) -> str:
    notes = str(slide.get("notes") or "").strip()
    text = str(slide.get("text") or "").strip()
    visuals = [str(v) for v in (slide.get("visuals") or []) if str(v).strip()]
    n = slide_index + 1
    parts: list[str] = [f"Slide {n} of {slide_count}."]
    if deck_context.strip():
        parts.append(f"This deck is about {deck_context.strip()[:180]}.")
    body = notes or text
    if body:
        parts.append(body)
    else:
        parts.append("This slide has no speaker notes or extracted text.")
    if visuals:
        labels = ", ".join(sorted(set(visuals)))
        parts.append(
            f"On screen there is a {labels}. I will only describe what the labels say — I will not invent values that are not on the slide."
        )
    script = " ".join(parts)
    words = _words(script)
    if len(words) > MAX_WORDS:
        script = " ".join(words[:MAX_WORDS])
    return script.strip()


def narrate_slides(slides: list[dict[str, Any]], *, deck_context: str = "") -> dict[str, Any]:
    out: list[dict[str, Any]] = []
    total = len(slides)
    for i, slide in enumerate(slides):
        script = grounded_slide_script(slide, deck_context=deck_context, slide_index=i, slide_count=total)
        out.append(
            {
                "index": int(slide.get("index") or i),
                "script": script,
                "word_count": len(_words(script)),
                "visuals": slide.get("visuals") or [],
            }
        )
    return {"ok": True, "count": len(out), "slides": out, "max_words": MAX_WORDS}
