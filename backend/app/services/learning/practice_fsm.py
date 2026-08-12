"""Practice / lesson FSM helpers for Learning Expansion (D2)."""

from __future__ import annotations

from typing import Any

LESSON_STATES = (
    "not_started",
    "lesson_started",
    "practicing",
    "hint_used",
    "tests_failed",
    "tests_passed",
    "lesson_verified",
)

PROGRESS_EVENTS = (
    "started",
    "lesson_started",
    "practice_attempt",
    "hint_used",
    "test_passed",
    "user_confirmed",
    "milestone",
    "completed",
)


def lesson_progress_blob(progress: dict[str, Any] | None) -> dict[str, Any]:
    p = dict(progress or {})
    lessons = dict(p.get("lessons") or {})
    return {
        "path_key": p.get("path_key") or "",
        "current_lesson_key": p.get("current_lesson_key") or "",
        "lessons": lessons,
        "verified_lesson_keys": list(p.get("verified_lesson_keys") or []),
        "hints_used_total": int(p.get("hints_used_total") or 0),
        "tests_passed": int(p.get("tests_passed") or 0),
        "milestones_done": list(p.get("milestones_done") or []),
        "started": bool(p.get("started")),
        "user_confirmed": bool(p.get("user_confirmed")),
        "completed": bool(p.get("completed")),
        "verified_complete": bool(p.get("verified_complete")),
        "work_item_id": p.get("work_item_id"),
        "skill_draft_id": p.get("skill_draft_id"),
    }


def start_lesson(progress: dict[str, Any], *, path_key: str, lesson_key: str) -> dict[str, Any]:
    p = lesson_progress_blob(progress)
    p["path_key"] = path_key
    p["current_lesson_key"] = lesson_key
    lessons = dict(p["lessons"])
    cur = dict(lessons.get(lesson_key) or {})
    cur.update(
        {
            "state": "lesson_started",
            "hint_level": int(cur.get("hint_level") or 0),
            "attempts": int(cur.get("attempts") or 0),
            "verified": bool(cur.get("verified")),
        }
    )
    lessons[lesson_key] = cur
    p["lessons"] = lessons
    return p


def record_hint(progress: dict[str, Any], *, lesson_key: str, level: int) -> dict[str, Any]:
    p = lesson_progress_blob(progress)
    lessons = dict(p["lessons"])
    cur = dict(lessons.get(lesson_key) or {"state": "practicing", "hint_level": 0, "attempts": 0})
    cur["hint_level"] = max(int(cur.get("hint_level") or 0), level)
    cur["state"] = "hint_used"
    lessons[lesson_key] = cur
    p["lessons"] = lessons
    p["hints_used_total"] = int(p.get("hints_used_total") or 0) + 1
    p["current_lesson_key"] = lesson_key or p.get("current_lesson_key") or ""
    return p


def record_practice_attempt(progress: dict[str, Any], *, lesson_key: str, passed: bool) -> dict[str, Any]:
    p = lesson_progress_blob(progress)
    lessons = dict(p["lessons"])
    cur = dict(lessons.get(lesson_key) or {"state": "practicing", "hint_level": 0, "attempts": 0})
    cur["attempts"] = int(cur.get("attempts") or 0) + 1
    cur["state"] = "tests_passed" if passed else "tests_failed"
    lessons[lesson_key] = cur
    p["lessons"] = lessons
    return p


def mark_lesson_verified(progress: dict[str, Any], *, lesson_key: str) -> dict[str, Any]:
    p = lesson_progress_blob(progress)
    lessons = dict(p["lessons"])
    cur = dict(lessons.get(lesson_key) or {})
    cur["verified"] = True
    cur["state"] = "lesson_verified"
    lessons[lesson_key] = cur
    p["lessons"] = lessons
    verified = list(p.get("verified_lesson_keys") or [])
    if lesson_key and lesson_key not in verified:
        verified.append(lesson_key)
    p["verified_lesson_keys"] = verified
    return p
