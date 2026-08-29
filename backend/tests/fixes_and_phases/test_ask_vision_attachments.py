"""Ask supports pasted/attached screenshots as real vision input (V4 Phase B
composer-attachments slice), not a decorative upload that goes nowhere.

`llm_phase.run_ask(images=[...])` shapes the final user message as OpenAI
content blocks (text + image_url) -- the SDK's chat.completions.create
already accepts that shape natively for vision-capable models, so this is
the one place that needed real wiring. developer_service.ask() threads
`images` through to it and persists only a count (never the image bytes)
in the audit trail.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal
from app.models import Project, Repo
from app.services.phases import llm_phase
from app.services.work_items.developer_service import MentrixDeveloperService

_PIXEL_PNG_DATA_URL = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _seed_project_with_repo(db: Session) -> tuple[Project, Repo]:
    tag = uuid.uuid4().hex[:8]
    p = Project(name=f"ask-vision-{tag}", description="test", status="active")
    db.add(p)
    db.flush()
    r = Repo(project_id=p.id, owner="acme", repo_name="alpha", default_branch="main")
    db.add(r)
    db.commit()
    db.refresh(p)
    db.refresh(r)
    return p, r


class TestRunAskShapesVisionContent:
    def test_no_images_sends_a_plain_string_user_message(self):
        with patch.object(llm_phase, "_chat", return_value={"ok": True, "content": "answer", "model": "m", "tokens_used": 1}) as chat:
            llm_phase.run_ask("What does this do?")
        messages = chat.call_args.args[0]
        assert messages[-1]["content"] == "What does this do?"

    def test_images_shape_the_final_message_as_content_blocks(self):
        with patch.object(llm_phase, "_chat", return_value={"ok": True, "content": "answer", "model": "m", "tokens_used": 1}) as chat:
            llm_phase.run_ask("What does this screenshot show?", images=[_PIXEL_PNG_DATA_URL])
        messages = chat.call_args.args[0]
        last = messages[-1]
        assert isinstance(last["content"], list)
        assert last["content"][0] == {"type": "text", "text": "What does this screenshot show?"}
        assert last["content"][1] == {"type": "image_url", "image_url": {"url": _PIXEL_PNG_DATA_URL}}

    def test_multiple_images_all_get_their_own_content_block(self):
        with patch.object(llm_phase, "_chat", return_value={"ok": True, "content": "answer", "model": "m", "tokens_used": 1}) as chat:
            llm_phase.run_ask("Compare these", images=[_PIXEL_PNG_DATA_URL, _PIXEL_PNG_DATA_URL])
        messages = chat.call_args.args[0]
        image_blocks = [b for b in messages[-1]["content"] if b.get("type") == "image_url"]
        assert len(image_blocks) == 2


class TestDeveloperServiceThreadsImagesThrough:
    def test_ask_passes_images_to_run_ask_and_persists_only_a_count(self, db: Session, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
        monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
        p, r = _seed_project_with_repo(db)
        svc = MentrixDeveloperService(db)

        with patch.object(
            llm_phase,
            "run_ask",
            return_value={"answer": "it's a screenshot", "model": "m", "tokens_used": 1, "offline": False},
        ) as run_ask:
            result = svc.ask(
                question="What's in this screenshot?",
                project_id=p.id,
                repository_id=r.id,
                images=[_PIXEL_PNG_DATA_URL],
            )
        assert run_ask.call_args.kwargs["images"] == [_PIXEL_PNG_DATA_URL]

        history = svc.ask_history(result["work_item_id"])
        assert history[-1]["image_count"] == 1
        # The audit trail stores a count, never the actual image data.
        assert _PIXEL_PNG_DATA_URL not in str(history)

    def test_ask_without_images_records_a_zero_count(self, db: Session, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
        monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
        p, r = _seed_project_with_repo(db)
        svc = MentrixDeveloperService(db)

        result = svc.ask(question="Plain question, no images", project_id=p.id, repository_id=r.id)
        history = svc.ask_history(result["work_item_id"])
        assert history[-1]["image_count"] == 0


class TestAskEndpointValidatesImages:
    def test_rejects_a_non_data_url(self, client, auth_headers, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
        resp = client.post(
            "/api/mentrix/developer/ask",
            headers=auth_headers,
            json={"question": "What is this?", "images": ["https://example.com/evil.png"]},
        )
        assert resp.status_code == 400
        assert "data:image" in resp.text

    def test_rejects_an_oversized_image(self, client, auth_headers, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
        huge = "data:image/png;base64," + ("A" * 12_000_001)
        resp = client.post(
            "/api/mentrix/developer/ask",
            headers=auth_headers,
            json={"question": "What is this?", "images": [huge]},
        )
        assert resp.status_code == 400
        assert "too large" in resp.text

    def test_accepts_a_valid_data_url(self, client, auth_headers, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
        monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
        resp = client.post(
            "/api/mentrix/developer/ask",
            headers=auth_headers,
            json={"question": "What is this?", "images": [_PIXEL_PNG_DATA_URL]},
        )
        assert resp.status_code == 200, resp.text
