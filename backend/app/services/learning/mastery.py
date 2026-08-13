"""Skill mastery from accumulated verified evidence — not one completion (D4)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import LearningProject
from app.services.learning.curriculum import CURRICULUM_PATHS, get_path

# Minimum distinct verified lessons (with skill tag) before proficiency draft is allowed
MIN_VERIFIED_LESSONS_FOR_PROFICIENCY = 2
# Minimum verified test_passed events across projects for the skill
MIN_VERIFIED_TESTS_FOR_PROFICIENCY = 2


def _jload(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        import json

        return json.loads(raw)
    except Exception:
        return default


def collect_user_evidence(db: Session, user_id: int) -> dict[str, Any]:
    projects = (
        db.query(LearningProject)
        .filter(LearningProject.user_id == user_id)
        .order_by(LearningProject.id.asc())
        .all()
    )
    verified_tests = 0
    verified_lessons: set[str] = set()
    skill_hits: dict[str, dict[str, Any]] = {}

    for proj in projects:
        progress = _jload(proj.progress_json, {})
        evidence = _jload(proj.evidence_json, [])
        path_key = str(progress.get("path_key") or "")
        path = get_path(path_key) if path_key else None
        for ev in evidence:
            if not isinstance(ev, dict):
                continue
            if ev.get("verified") and ev.get("event") == "test_passed":
                verified_tests += 1
        for lk in progress.get("verified_lesson_keys") or []:
            verified_lessons.add(f"{path_key}:{lk}" if path_key else str(lk))
            lesson_skills: list[str] = []
            if path:
                for les in path["lessons"]:
                    if les["key"] == lk:
                        lesson_skills = list(les.get("skill_tags") or [])
                        break
            for sk in lesson_skills or _jload(proj.skills_json, []):
                key = str(sk).strip()
                if not key:
                    continue
                bucket = skill_hits.setdefault(key, {"verified_lessons": set(), "verified_tests": 0, "projects": set()})
                bucket["verified_lessons"].add(f"{path_key}:{lk}")
                bucket["projects"].add(proj.id)

        for ev in evidence:
            if isinstance(ev, dict) and ev.get("verified") and ev.get("event") == "test_passed":
                for sk in _jload(proj.skills_json, []):
                    key = str(sk).strip()
                    if not key:
                        continue
                    bucket = skill_hits.setdefault(key, {"verified_lessons": set(), "verified_tests": 0, "projects": set()})
                    bucket["verified_tests"] = int(bucket.get("verified_tests") or 0) + 1

    mastery = {}
    for skill, data in skill_hits.items():
        n_lessons = len(data["verified_lessons"])
        n_tests = int(data.get("verified_tests") or 0)
        # Also count lesson-linked tests at least as lesson count
        n_tests = max(n_tests, n_lessons)
        proficient = (
            n_lessons >= MIN_VERIFIED_LESSONS_FOR_PROFICIENCY
            and n_tests >= MIN_VERIFIED_TESTS_FOR_PROFICIENCY
        )
        mastery[skill] = {
            "skill": skill,
            "verified_lessons": n_lessons,
            "verified_tests": n_tests,
            "projects": len(data["projects"]),
            "proficient": proficient,
            "threshold": {
                "min_lessons": MIN_VERIFIED_LESSONS_FOR_PROFICIENCY,
                "min_tests": MIN_VERIFIED_TESTS_FOR_PROFICIENCY,
            },
        }

    return {
        "user_id": user_id,
        "verified_tests_total": verified_tests,
        "verified_lessons_total": len(verified_lessons),
        "mastery": mastery,
        "curriculum_paths": [p["key"] for p in CURRICULUM_PATHS],
    }


def can_graduate_skill(db: Session, user_id: int, skill: str) -> tuple[bool, dict[str, Any]]:
    summary = collect_user_evidence(db, user_id)
    entry = (summary.get("mastery") or {}).get(skill) or (summary.get("mastery") or {}).get(skill.title())
    # case-insensitive lookup
    if not entry:
        for k, v in (summary.get("mastery") or {}).items():
            if k.lower() == (skill or "").lower():
                entry = v
                break
    if not entry:
        return False, {"error": "insufficient_evidence", "skill": skill, "proficient": False}
    if not entry.get("proficient"):
        return False, {"error": "mastery_threshold_not_met", **entry}
    return True, entry
