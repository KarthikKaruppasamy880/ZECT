"""Skill Library (a standalone page/router with name/description/category/
template/tags/repo_id/scope/usage_count, no versioning, no trigger matching,
no execution tracking) was a genuine duplicate of the Skills Engine's
SkillDefinition registry — confirmed by reading both implementations, not
just their names. Skills Engine is the more complete system (versioning,
trigger-based matching, execution logs, seed skills) so Skill Library was
merged into it rather than the other way around: its "template" and "tags"
concepts now live in manifest["template"]/manifest["tags"] (no schema
change needed), and its AI pattern-detector moved to
POST /api/skills-engine/detect.
"""

from __future__ import annotations

from unittest.mock import Mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.infrastructure.database import Base
from app.models import SkillDefinition
from app.domains.personal_agent.skills_engine import (
    DetectSkillRequest,
    SkillCreate,
    SkillUpdate,
    _skill_to_dict,
    create_skill,
    detect_patterns,
    update_skill,
)


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


class TestTemplateAndTagsFoldIntoManifest:
    def test_create_with_template_and_tags_stores_them_in_manifest(self):
        db = _session()

        result = create_skill(
            SkillCreate(name="my-skill", template="Do the thing.", tags=["review", "python"]),
            db=db,
        )

        assert result["template"] == "Do the thing."
        assert result["tags"] == ["review", "python"]
        row = db.query(SkillDefinition).filter(SkillDefinition.name == "my-skill").first()
        assert row.manifest["template"] == "Do the thing."
        assert row.manifest["tags"] == ["review", "python"]

    def test_create_without_template_leaves_manifest_untouched(self):
        db = _session()

        result = create_skill(SkillCreate(name="plain-skill", manifest={"inputs": ["x"]}), db=db)

        assert result["template"] == ""
        assert result["manifest"] == {"inputs": ["x"]}

    def test_update_template_preserves_other_manifest_keys(self):
        db = _session()
        create_skill(SkillCreate(name="evolve-skill", manifest={"inputs": ["x"]}), db=db)
        row = db.query(SkillDefinition).filter(SkillDefinition.name == "evolve-skill").first()

        updated = update_skill(row.id, SkillUpdate(template="New template body"), db=db)

        assert updated["template"] == "New template body"
        assert updated["manifest"]["inputs"] == ["x"]

    def test_skill_to_dict_surfaces_template_from_existing_manifest(self):
        skill = SkillDefinition(name="x", manifest={"template": "existing", "tags": ["a"]})
        out = _skill_to_dict(skill)
        assert out["template"] == "existing"
        assert out["tags"] == ["a"]

    def test_skill_to_dict_defaults_when_no_manifest(self):
        skill = SkillDefinition(name="x", manifest=None)
        out = _skill_to_dict(skill)
        assert out["template"] == ""
        assert out["tags"] == []


class TestDetectPatterns:
    def test_detect_returns_suggested_skills(self, monkeypatch):
        fake_message = Mock(content='{"detected_patterns": [], "suggested_skills": [{"name": "s1", "template": "t"}]}')
        fake_choice = Mock(message=fake_message)
        fake_usage = Mock(total_tokens=42, prompt_tokens=30, completion_tokens=12)
        fake_resp = Mock(choices=[fake_choice], usage=fake_usage)
        fake_client = Mock()
        fake_client.chat.completions.create.return_value = fake_resp
        monkeypatch.setattr("app.domains.personal_agent.skills_engine._get_openai_client", lambda: fake_client)
        monkeypatch.setattr("app.token_tracker.log_tokens", lambda **kw: None)

        result = detect_patterns(DetectSkillRequest(code="def foo(): pass"))

        assert result.suggested_skills == [{"name": "s1", "template": "t"}]
        assert result.tokens_used == 42

    def test_detect_requires_openai_key(self, monkeypatch):
        import os

        from fastapi import HTTPException

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        import pytest

        with pytest.raises(HTTPException) as exc:
            detect_patterns(DetectSkillRequest(code="x = 1"))
        assert exc.value.status_code == 503
