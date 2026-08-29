"""Mentrix Learning Mentor — progressive hints; GUIDED never pastes full solutions (D3)."""

from __future__ import annotations

import re
from typing import Any

from app.services.learning.curriculum import get_lesson
from app.services.mentrix.untrusted_content import sanitize_for_prompt, tag_untrusted

_SOLUTION_MARKERS = re.compile(
    r"(?is)(here is the (full )?solution|complete solution|final code:|"
    r"```(?:python|typescript|javascript|ts|js)[\s\S]{80,}```|"
    r"copy[- ]paste this entire)"
)


def _strip_fenced_solutions(text: str) -> str:
    # Remove large fenced code blocks that look like full answers
    return re.sub(r"(?is)```(?:python|typescript|javascript|ts|js)?\n[\s\S]{120,}?```", "[code omitted — write it yourself]", text)


def progressive_hint(
    *,
    path_key: str,
    lesson_key: str,
    mode: str,
    question: str,
    current_hint_level: int = 0,
    study_notes: str = "",
) -> dict[str, Any]:
    """Return next hint rung. GUIDED never returns starter_code filled in or full ladder dump."""
    mode_u = (mode or "GUIDED").upper()
    lesson = get_lesson(path_key, lesson_key)
    if not lesson:
        return {
            "ok": False,
            "error": "lesson_not_found",
            "hint": "",
            "hint_level": current_hint_level,
            "auto_complete_forbidden": True,
        }

    ladder = list(lesson.get("hint_ladder") or [])
    next_level = min(int(current_hint_level or 0) + 1, max(1, len(ladder)))
    hint_text = ladder[next_level - 1] if ladder else "Break the problem into one smaller step and try again."

    notes = ""
    if study_notes.strip():
        notes = sanitize_for_prompt(study_notes[:2000], source="learning_study_notes", max_chars=2000)

    if mode_u == "GUIDED":
        answer = (
            "Mentrix Learning Advisor (GUIDED)\n"
            "I explain and ask questions. I will not paste a complete solution — you own the code.\n\n"
            f"Lesson: {lesson['title']}\n"
            f"Objective: {lesson['objective']}\n"
            f"Your question: {(question or '')[:500]}\n\n"
            f"Progressive hint ({next_level}/{len(ladder) or 1}): {hint_text}\n\n"
            "Next: write 5–10 lines, run tests, then ask for another hint if needed."
        )
        answer = _strip_fenced_solutions(answer)
        if _SOLUTION_MARKERS.search(answer):
            answer = re.sub(_SOLUTION_MARKERS, "[solution withheld in GUIDED]", answer)
        route = {
            "mode": "GUIDED",
            "coding_agent": False,
            "auto_complete_forbidden": True,
            "hint_level": next_level,
        }
    elif mode_u == "PAIR":
        answer = (
            f"PAIR mode hint ({next_level}): {hint_text}\n"
            "We can implement together via Developer / Coding Agent with your approval on edits.\n"
            f"Focus: {(question or lesson['practice_prompt'])[:400]}"
        )
        route = {"mode": "PAIR", "coding_agent": True, "navigate": "/workspace", "hint_level": next_level}
    elif mode_u == "DEMO":
        answer = (
            f"DEMO mode: walkthrough guidance — {hint_text}\n"
            "Coding Agent may demonstrate under policy; learning progress still needs EvidenceVerifier tests.\n"
            f"Goal: {(question or '')[:400]}"
        )
        route = {"mode": "DEMO", "coding_agent": True, "navigate": "/workspace", "hint_level": next_level}
    else:
        answer = (
            f"AUTONOMOUS mode: {hint_text}\n"
            "Coding Agent may execute under Developer policies. Progress requires verified tests — not agent claims.\n"
            f"Goal: {(question or '')[:400]}"
        )
        route = {"mode": "AUTONOMOUS", "coding_agent": True, "navigate": "/workspace", "hint_level": next_level}

    return {
        "ok": True,
        "hint": answer,
        "hint_level": next_level,
        "hint_max": len(ladder),
        "lesson": {
            "key": lesson["key"],
            "title": lesson["title"],
            "objective": lesson["objective"],
            "practice_prompt": lesson["practice_prompt"],
        },
        "route": route,
        "study_notes": tag_untrusted(notes, source="learning_study_notes") if notes else None,
        "auto_complete_forbidden": mode_u == "GUIDED",
    }


def reject_guided_full_solution(mode: str, payload_text: str) -> str | None:
    """If GUIDED mentor/progress tries to smuggle a full solution, return error code."""
    if (mode or "").upper() != "GUIDED":
        return None
    if _SOLUTION_MARKERS.search(payload_text or ""):
        return "guided_full_solution_forbidden"
    # Large single fence resembling a complete file
    if re.search(r"(?is)```(?:python|typescript|javascript).{200,}```", payload_text or ""):
        return "guided_full_solution_forbidden"
    return None
