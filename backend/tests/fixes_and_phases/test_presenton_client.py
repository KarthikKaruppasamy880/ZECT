"""Presenton client readiness helpers (no live Presenton required)."""

from unittest.mock import MagicMock, patch

from app.services.presenton_client import (
    BUILTIN_TEMPLATES,
    generate_presentation,
    list_templates,
    presenton_configured,
    presenton_reachable,
)


def test_presenton_not_configured(monkeypatch):
    monkeypatch.delenv("PRESENTON_BASE_URL", raising=False)
    assert presenton_configured() is False
    out = generate_presentation("hello deck")
    assert out["ok"] is False
    assert out["error"] == "presenton_not_configured"


def test_presenton_empty_content(monkeypatch):
    monkeypatch.setenv("PRESENTON_BASE_URL", "http://127.0.0.1:5000")
    out = generate_presentation("   ")
    assert out["ok"] is False
    assert out["error"] == "empty_content"


def test_list_templates_builtin_when_unset(monkeypatch):
    monkeypatch.delenv("PRESENTON_BASE_URL", raising=False)
    out = list_templates()
    assert out["ok"] is True
    assert out["source"] == "builtin"
    assert out["reachable"] is False
    assert out["configured"] is False
    assert out["templates"] == BUILTIN_TEMPLATES
    assert presenton_reachable() is False


def test_list_templates_from_presenton(monkeypatch):
    monkeypatch.setenv("PRESENTON_BASE_URL", "http://127.0.0.1:5000")
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = [
        {"id": "modern", "name": "Modern"},
        {"name": "swift"},
    ]
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.get.return_value = mock_res

    with patch("app.services.presenton_client.httpx.Client", return_value=mock_client):
        out = list_templates()

    assert out["ok"] is True
    assert out["source"] == "presenton"
    assert out["reachable"] is True
    ids = [t["id"] for t in out["templates"]]
    assert ids == ["modern", "swift"]
    mock_client.get.assert_called_once()
    assert "/api/v1/ppt/template/all" in mock_client.get.call_args.args[0]


def test_list_templates_connect_error_falls_back(monkeypatch):
    import httpx

    monkeypatch.setenv("PRESENTON_BASE_URL", "http://127.0.0.1:5000")
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.get.side_effect = httpx.ConnectError("refused")

    with patch("app.services.presenton_client.httpx.Client", return_value=mock_client):
        out = list_templates()

    assert out["source"] == "builtin"
    assert out["reachable"] is False
    assert out["templates"] == BUILTIN_TEMPLATES


def test_generate_payload_includes_template(monkeypatch, tmp_path):
    monkeypatch.setenv("PRESENTON_BASE_URL", "http://127.0.0.1:5000")
    monkeypatch.setattr(
        "app.services.presenton_client.default_save_dir",
        lambda: tmp_path,
    )

    gen_res = MagicMock()
    gen_res.status_code = 200
    gen_res.json.return_value = {"path": "/static/deck.pptx", "presentation_id": "abc"}

    file_res = MagicMock()
    file_res.status_code = 200
    file_res.content = b"PK-fake-pptx"

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.post.return_value = gen_res
    mock_client.get.return_value = file_res

    with patch("app.services.presenton_client.httpx.Client", return_value=mock_client):
        out = generate_presentation(
            "Q2 delivery brief",
            n_slides=8,
            template="modern",
            filename="mentrix-deck.pptx",
        )

    assert out["ok"] is True
    assert out["path"]
    payload = mock_client.post.call_args.kwargs["json"]
    assert payload["template"] == "modern"
    assert payload["n_slides"] == 8
    assert payload["content"] == "Q2 delivery brief"
