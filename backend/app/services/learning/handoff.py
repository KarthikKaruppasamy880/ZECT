"""Developer Workspace + Skills graduation handoff (D4). Reuses WorkItem + SkillDefinition."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.domains.work_items.service import create_work_item
from app.models import LearningProject, SkillDefinition, WorkItem
from app.services.learning.mastery import can_graduate_skill


def handoff_to_developer(
    db: Session,
    *,
    project: LearningProject,
    user_email: str = "",
    goal: str = "",
) -> dict[str, Any]:
    """Create/link a WorkItem for Developer Workspace — does not start a parallel agent runtime."""
    progress = {}
    try:
        progress = json.loads(project.progress_json or "{}")
    except Exception:
        progress = {}

    if project.work_item_id:
        wi = db.query(WorkItem).filter(WorkItem.id == project.work_item_id).first()
        if wi:
            return {
                "ok": True,
                "work_item_id": wi.id,
                "navigate": "/workspace",
                "reused": True,
                "title": wi.title,
            }

    title = f"Learning: {project.title}"[:200]
    description = (
        goal
        or f"Continue learning project #{project.id} ({project.mode}) in Developer Workspace. "
        f"Path={progress.get('path_key')} lesson={progress.get('current_lesson_key')}"
    )
    wi = create_work_item(
        db,
        title=title,
        description=description[:4000],
        created_by=user_email or str(project.user_id or ""),
        project_id=None,
    )
    project.work_item_id = wi.id
    progress["work_item_id"] = wi.id
    project.progress_json = json.dumps(progress)
    db.commit()
    db.refresh(project)
    return {
        "ok": True,
        "work_item_id": wi.id,
        "navigate": "/workspace",
        "reused": False,
        "title": wi.title,
        "mode_policy": {
            "GUIDED": "mentor_only_no_auto_code",
            "PAIR": "coding_agent_with_approval",
            "DEMO": "coding_agent_demo",
            "AUTONOMOUS": "coding_agent_under_broker",
        }.get((project.mode or "GUIDED").upper(), "mentor_only_no_auto_code"),
    }


def graduate_skill_draft(
    db: Session,
    *,
    user_id: int,
    skill: str,
    project: LearningProject | None = None,
) -> dict[str, Any]:
    """Draft SkillDefinition only when accumulated verified evidence meets mastery threshold."""
    ok, detail = can_graduate_skill(db, user_id, skill)
    if not ok:
        return {"ok": False, **detail}

    name = f"learned-{(skill or 'skill').strip().lower().replace(' ', '-')}"[:120]
    existing = (
        db.query(SkillDefinition)
        .filter(SkillDefinition.name == name, SkillDefinition.is_active == True)  # noqa: E712
        .first()
    )
    if existing:
        return {
            "ok": True,
            "skill_id": existing.id,
            "name": existing.name,
            "draft": False,
            "reused": True,
            "mastery": detail,
            "approval_required": True,
        }

    now = datetime.now(timezone.utc)
    skill_row = SkillDefinition(
        name=name,
        version="0.1.0-draft",
        description=f"Draft skill from Learning Expansion mastery evidence for '{skill}'.",
        category="learning",
        trigger_pattern="",
        manifest={
            "source": "learning_expansion",
            "skill_label": skill,
            "mastery": {k: v for k, v in detail.items() if k != "threshold"},
            "learning_project_id": project.id if project else None,
        },
        script_body="",
        is_seed=False,
        is_active=True,
        execution_count=0,
        owner=str(user_id),
        provenance="learning_expansion",
        approval_required=True,
        timeout_seconds=60,
        required_capabilities=[],
        allowed_tools=[],
        input_schema={},
        output_schema={},
        test_cases=[],
        created_at=now,
        updated_at=now,
    )
    db.add(skill_row)
    db.flush()
    if project:
        progress = {}
        try:
            progress = json.loads(project.progress_json or "{}")
        except Exception:
            progress = {}
        progress["skill_draft_id"] = skill_row.id
        project.progress_json = json.dumps(progress)
    db.commit()
    db.refresh(skill_row)
    return {
        "ok": True,
        "skill_id": skill_row.id,
        "name": skill_row.name,
        "draft": True,
        "reused": False,
        "mastery": detail,
        "approval_required": True,
        "note": "Skill draft requires Permission Broker / approval — one lesson completion never auto-masters.",
    }
