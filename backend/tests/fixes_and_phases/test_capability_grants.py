"""Phase 5 Stage B — capability grant evaluation unit tests."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.domains.permissions.capability_grants import (
    apply_grant_override,
    capabilities_covering_action,
    is_grant_active,
)


def test_capabilities_covering_pr_create():
    caps = capabilities_covering_action("companion_create_pr")
    assert "pull_request:create" in caps
    assert "companion_create_pr" in caps


def test_capabilities_covering_merge():
    caps = capabilities_covering_action("merge_pr")
    assert "pull_request:merge" in caps


def test_is_grant_active_expiry():
    now = datetime.now(timezone.utc)
    active = SimpleNamespace(revoked_at=None, expires_at=now + timedelta(hours=1))
    expired = SimpleNamespace(revoked_at=None, expires_at=now - timedelta(minutes=1))
    revoked = SimpleNamespace(revoked_at=now, expires_at=now + timedelta(hours=1))
    assert is_grant_active(active, now=now) is True
    assert is_grant_active(expired, now=now) is False
    assert is_grant_active(revoked, now=now) is False


def test_apply_grant_allow_overrides_pending():
    grant = SimpleNamespace(id=1, permission_level="allow")
    result, level, g = apply_grant_override("pending_approval", "require_approval", [grant])
    assert result == "granted"
    assert level == "allow"
    assert g is grant


def test_apply_grant_never_wins():
    grants = [
        SimpleNamespace(id=1, permission_level="allow"),
        SimpleNamespace(id=2, permission_level="never"),
    ]
    result, level, g = apply_grant_override("granted", "allow", grants)
    assert result == "denied"
    assert level == "never"
    assert g.id == 2
