"""Mentrix Notes had no browsable page — add_note/list_notes only worked as
an ephemeral, one-conversation Companion tool reply. Verifies the new
list/create/delete endpoints and the delete_note() path-traversal guard.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException


class TestListMentrixNotes:
    def test_returns_notes_from_list_notes(self):
        from app.domains.agent_run.mentrix import list_mentrix_notes

        with patch("app.services.mentrix.notes.list_notes", return_value=[{"id": "1", "text": "hi"}]) as mock_list:
            result = list_mentrix_notes(_user=Mock(user_id=1))

        mock_list.assert_called_once_with(limit=200)
        assert result == {"notes": [{"id": "1", "text": "hi"}]}

    def test_clamps_limit_to_500(self):
        from app.domains.agent_run.mentrix import list_mentrix_notes

        with patch("app.services.mentrix.notes.list_notes", return_value=[]) as mock_list:
            list_mentrix_notes(limit=10_000, _user=Mock(user_id=1))

        mock_list.assert_called_once_with(limit=500)

    def test_clamps_limit_to_at_least_1(self):
        from app.domains.agent_run.mentrix import list_mentrix_notes

        with patch("app.services.mentrix.notes.list_notes", return_value=[]) as mock_list:
            list_mentrix_notes(limit=-5, _user=Mock(user_id=1))

        mock_list.assert_called_once_with(limit=1)


class TestCreateMentrixNote:
    def test_creates_a_note(self):
        from app.domains.agent_run.mentrix import NoteCreate, create_mentrix_note

        with patch("app.services.mentrix.notes.add_note", return_value={"id": "abc", "text": "buy milk"}) as mock_add:
            result = create_mentrix_note(NoteCreate(text="buy milk", tags=["personal"]), _user=Mock(user_id=1))

        mock_add.assert_called_once_with("buy milk", tags=["personal"])
        assert result["id"] == "abc"

    def test_rejects_blank_text(self):
        from app.domains.agent_run.mentrix import NoteCreate, create_mentrix_note

        with pytest.raises(HTTPException) as exc_info:
            create_mentrix_note(NoteCreate(text="   "), _user=Mock(user_id=1))

        assert exc_info.value.status_code == 400


class TestDeleteMentrixNote:
    def test_deletes_an_existing_note(self):
        from app.domains.agent_run.mentrix import delete_mentrix_note

        with patch("app.services.mentrix.notes.delete_note", return_value=True) as mock_delete:
            result = delete_mentrix_note("abc-123", _user=Mock(user_id=1))

        mock_delete.assert_called_once_with("abc-123")
        assert result == {"deleted": True, "id": "abc-123"}

    def test_404_when_note_missing(self):
        from app.domains.agent_run.mentrix import delete_mentrix_note

        with patch("app.services.mentrix.notes.delete_note", return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                delete_mentrix_note("nonexistent", _user=Mock(user_id=1))

        assert exc_info.value.status_code == 404


class TestDeleteNotePathTraversalGuard:
    def test_rejects_path_traversal_id(self, tmp_path, monkeypatch):
        from app.services.mentrix import notes

        monkeypatch.setattr(notes, "NOTES_DIR", tmp_path)
        secret = tmp_path.parent / "secret.json"
        secret.write_text("{}", encoding="utf-8")

        result = notes.delete_note("../secret")

        assert result is False
        assert secret.exists()

    def test_rejects_empty_id(self, tmp_path, monkeypatch):
        from app.services.mentrix import notes

        monkeypatch.setattr(notes, "NOTES_DIR", tmp_path)

        assert notes.delete_note("") is False

    def test_keeps_long_text_up_to_50k(self, tmp_path, monkeypatch):
        from app.services.mentrix import notes

        monkeypatch.setattr(notes, "NOTES_DIR", tmp_path)
        body = "a" * 12_000
        note = notes.add_note(body)
        assert len(note["text"]) == 12_000

        assert notes.delete_note(note["id"]) is True
        assert not (tmp_path / f"{note['id']}.json").exists()

    def test_returns_false_for_nonexistent_valid_looking_id(self, tmp_path, monkeypatch):
        from app.services.mentrix import notes

        monkeypatch.setattr(notes, "NOTES_DIR", tmp_path)

        assert notes.delete_note("00000000-0000-0000-0000-000000000000") is False


def test_add_note_keeps_long_companion_text(tmp_path, monkeypatch):
    from app.services.mentrix import notes

    monkeypatch.setattr(notes, "NOTES_DIR", tmp_path)
    body = "paragraph " * 800
    note = notes.add_note(body)
    assert len(note["text"]) > 4000
    assert len(note["text"]) == len(body.strip())
