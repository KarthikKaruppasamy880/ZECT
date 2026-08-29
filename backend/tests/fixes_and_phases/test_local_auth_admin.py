"""Local auth: configured ZECT_USERNAME logs in as admin; stray ZECT_PYTEST must not block .env."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.infrastructure.auth.session_store import upsert_local_user
from app.models import User
from app.services.presenton_client import resolve_presenton_template_id


def test_upsert_promotes_configured_local_user_to_admin(monkeypatch):
    monkeypatch.setenv("ZECT_USERNAME", "karthik.karuppasamy@zinnia.com")
    existing = User(
        id=1,
        email="karthik.karuppasamy@zinnia.com",
        name="karthik",
        role="developer",
    )
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value.first.return_value = existing
    db.query.return_value = q

    out = upsert_local_user(db, "Karthik.karuppasamy@Zinnia.com")
    assert out.role == "admin"
    db.commit.assert_called()


def test_resolve_zinnia_without_master_is_not_verified(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    monkeypatch.delenv("ZINNIA_PRESENTON_TEMPLATE_ID", raising=False)
    resolved = resolve_presenton_template_id("zinnia-exec")
    assert resolved["template_id"] == "modern"
    assert resolved["zinnia_verified"] is False


def test_resolve_zinnia_env_seeds_executive_registry_only(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZINNIA_PRESENTON_TEMPLATE_ID", "zinnia-brand-master")
    resolved = resolve_presenton_template_id("zinnia-executive-v1")
    assert resolved["template_id"] == "zinnia-brand-master"
    assert resolved["zinnia_verified"] is True
    assert resolved["mapping_source"] == "registry"
    delivery = resolve_presenton_template_id("zinnia-delivery")
    assert delivery["zinnia_verified"] is False
