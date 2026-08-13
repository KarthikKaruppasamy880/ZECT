"""Presentation template registry + canonical Zinnia mapping (R2.5)."""

from __future__ import annotations

from io import BytesIO

from fastapi import UploadFile

from app.services.mentrix.presentation import template_registry as tmpl
from app.services.presenton_client import resolve_presenton_template_id


def test_list_includes_canonical_zinnia(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    monkeypatch.delenv("ZINNIA_PRESENTON_TEMPLATE_ID", raising=False)
    out = tmpl.list_templates("u1")
    assert out["ok"] is True
    ids = {t["id"] for t in out["zinnia"]}
    assert "zinnia-executive-v1" in ids
    assert "zinnia-delivery-v1" in ids
    assert "zinnia-risk-v1" in ids
    org_ids = {t["id"] for t in out["organization"]}
    assert "org-standard" in org_ids
    assert org_ids.isdisjoint(ids)
    assert out["my_templates"] == []
    assert "zinnia-executive-v1" in out["canonical_ids"]
    assert out["lifecycle"] == tmpl.LIFECYCLE_TEMPLATE_NOT_READY


def test_alias_canonical_id():
    assert tmpl.canonical_id("zinnia-exec") == "zinnia-executive-v1"
    assert tmpl.canonical_id("zinnia-executive-v1") == "zinnia-executive-v1"
    assert tmpl.canonical_id("zinnia-delivery") == "zinnia-delivery-v1"


def test_register_and_preview_user_pptx(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))

    async def _run():
        upload = UploadFile(filename="master.pptx", file=BytesIO(b"PK\x03\x04fake-pptx"))
        reg = await tmpl.register_user_pptx("u1", upload, name="My Master")
        assert reg["ok"] is True
        tid = reg["template"]["id"]
        assert tid.startswith("user-")
        listed = tmpl.list_templates("u1")
        assert any(t["id"] == tid for t in listed["my_templates"])
        prev = tmpl.preview_template("u1", tid)
        assert prev["ok"] is True
        assert prev["provider_uuid_hidden"] is True
        assert "provider_template_id" not in prev
        assert prev["lifecycle"] == tmpl.LIFECYCLE_TEMPLATE_NOT_READY
        other = tmpl.list_templates("u2")
        assert other["my_templates"] == []

    import asyncio

    asyncio.run(_run())


def test_org_upload_not_visible_as_user_private(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))

    async def _run():
        upload = UploadFile(filename="org.pptx", file=BytesIO(b"PK\x03\x04fake-pptx"))
        reg = await tmpl.register_user_pptx("admin", upload, name="Org Master", scope="ORG")
        assert reg["ok"] is True
        tid = reg["template"]["id"]
        assert tid.startswith("org-")
        listed = tmpl.list_templates("u1")
        assert any(t["id"] == tid for t in listed["organization"])
        assert listed["my_templates"] == []

    import asyncio

    asyncio.run(_run())


def test_registry_mapping_verifies_zinnia_without_env(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    monkeypatch.delenv("ZINNIA_PRESENTON_TEMPLATE_ID", raising=False)
    unresolved = resolve_presenton_template_id("zinnia-executive-v1")
    assert unresolved["zinnia_verified"] is False
    assert unresolved["lifecycle"] == tmpl.LIFECYCLE_TEMPLATE_NOT_READY
    assert unresolved["template_id"] == "modern"

    out = tmpl.register_provider_mapping(
        "zinnia-executive-v1",
        "presenton-master-uuid-9",
        actor="admin@zect.local",
    )
    assert out["ok"] is True
    resolved = resolve_presenton_template_id("zinnia-exec")  # alias
    assert resolved["canonical_id"] == "zinnia-executive-v1"
    assert resolved["template_id"] == "presenton-master-uuid-9"
    assert resolved["zinnia_verified"] is True
    assert resolved["mapping_source"] == "registry"
    assert resolved["lifecycle"] == tmpl.LIFECYCLE_READY

    delivery = resolve_presenton_template_id("zinnia-delivery-v1")
    assert delivery["zinnia_verified"] is False
    assert delivery["lifecycle"] == tmpl.LIFECYCLE_TEMPLATE_NOT_READY


def test_env_seeds_executive_only_into_registry(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZINNIA_PRESENTON_TEMPLATE_ID", "zinnia-brand-master")
    exec_row = resolve_presenton_template_id("zinnia-executive-v1")
    assert exec_row["zinnia_verified"] is True
    assert exec_row["mapping_source"] == "registry"
    assert exec_row["template_id"] == "zinnia-brand-master"
    delivery = resolve_presenton_template_id("zinnia-delivery")
    assert delivery["zinnia_verified"] is False
    assert delivery["template_id"] == "modern"


def test_fallback_provider_ids_cannot_register_as_zinnia_master(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    bad = tmpl.register_provider_mapping("zinnia-executive-v1", "modern")
    assert bad["ok"] is False
    assert resolve_presenton_template_id("zinnia-executive-v1")["zinnia_verified"] is False


def test_maybe_bind_exact_presenton_match(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    monkeypatch.delenv("ZINNIA_PRESENTON_TEMPLATE_ID", raising=False)
    bound = tmpl.maybe_bind_from_provider_templates(
        [
            {"id": "modern", "name": "Modern"},
            {"id": "zinnia-executive-v1", "name": "Zinnia Executive v1"},
        ]
    )
    assert "zinnia-executive-v1" in bound
    resolved = resolve_presenton_template_id("zinnia-executive-v1")
    assert resolved["zinnia_verified"] is True
    assert resolved["template_id"] == "zinnia-executive-v1"


def test_user_pptx_stays_blocked_until_bound(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZINNIA_PRESENTON_TEMPLATE_ID", "zinnia-brand-master")
    user = resolve_presenton_template_id("user-abc123", user_id="u1")
    assert user["template_id"] == "general"
    assert user.get("blocked_external") is True
    assert user["lifecycle"] == tmpl.LIFECYCLE_TEMPLATE_NOT_READY


def test_org_unmapped_is_not_zinnia_verified(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    monkeypatch.delenv("ZINNIA_PRESENTON_TEMPLATE_ID", raising=False)
    org = resolve_presenton_template_id("org-standard")
    assert org["template_id"] == "standard"
    assert org["zinnia_verified"] is False
    assert org["lifecycle"] == tmpl.LIFECYCLE_TEMPLATE_NOT_READY


def test_provider_lifecycle_states(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    assert (
        tmpl.provider_lifecycle(configured=False, reachable=False)
        == tmpl.LIFECYCLE_PROVIDER_UNAVAILABLE
    )
    assert (
        tmpl.provider_lifecycle(configured=True, reachable=False)
        == tmpl.LIFECYCLE_PROVIDER_UNAVAILABLE
    )
    assert (
        tmpl.provider_lifecycle(configured=True, reachable=None)
        == tmpl.LIFECYCLE_STARTING
    )
    assert (
        tmpl.provider_lifecycle(
            configured=True,
            reachable=True,
            template_id="zinnia-executive-v1",
        )
        == tmpl.LIFECYCLE_TEMPLATE_NOT_READY
    )
    tmpl.register_provider_mapping("zinnia-executive-v1", "master-1")
    assert (
        tmpl.provider_lifecycle(
            configured=True,
            reachable=True,
            template_id="zinnia-executive-v1",
        )
        == tmpl.LIFECYCLE_READY
    )
    assert (
        tmpl.provider_lifecycle(
            configured=True,
            reachable=True,
            template_id="zinnia-executive-v1",
            generation_failed=True,
        )
        == tmpl.LIFECYCLE_GENERATION_FAILED
    )
