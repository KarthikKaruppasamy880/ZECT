"""Phase 5 Stage C/D — redact, emergency stop, secret resolve helpers."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.security.redact import redact_mapping, redact_secrets, redact_text
from app.security.emergency_stop import (
    EMERGENCY_STOP_KEY,
    clear_emergency_stop,
    engage_emergency_stop,
    is_emergency_stop_active,
    set_emergency_stop,
)
from app.models import Setting


def test_redact_mapping_sensitive_keys():
    out = redact_mapping({"api_key": "sk-live-abc", "path": "/tmp", "nested": {"password": "x"}})
    assert out["api_key"] == "***"
    assert out["path"] == "/tmp"
    assert out["nested"]["password"] == "***"


def test_redact_text_patterns():
    text = "Authorization: Bearer abcdefghijklmnop token=secretvalue"
    red = redact_text(text)
    assert "abcdefghijklmnop" not in red
    assert "***" in red


def test_redact_secrets_json_string():
    raw = '{"token": "super-secret", "ok": true}'
    out = redact_secrets(raw)
    assert "super-secret" not in out
    assert "***" in out


def test_emergency_stop_toggle():
    db = MagicMock()
    setting = Setting(
        key=EMERGENCY_STOP_KEY,
        value="false",
        setting_type="toggle",
        label="Global Emergency Stop",
        description="",
    )
    q = MagicMock()
    q.filter.return_value.first.return_value = setting
    # Mentrix cancel query path
    mq = MagicMock()
    mq.filter.return_value.all.return_value = []

    def query_side(model):
        if model is Setting:
            return q
        return mq

    db.query.side_effect = query_side

    assert is_emergency_stop_active(db) is False
    set_emergency_stop(db, True)
    assert setting.value == "true"
    assert is_emergency_stop_active(db) is True
    result = engage_emergency_stop(db)
    assert result["active"] is True
    cleared = clear_emergency_stop(db)
    assert cleared["active"] is False
    assert setting.value == "false"


def test_audit_log_redacts_and_hashes():
    from app.domains.audit.audit_trail import log_audit
    from app.models import AuditLog

    db = MagicMock()
    # No previous entry
    prev_q = MagicMock()
    prev_q.order_by.return_value.limit.return_value.first.return_value = None
    db.query.return_value = prev_q

    entry = log_audit(
        db,
        action="test",
        resource_type="secret",
        details={"api_token": "should-not-persist", "note": "ok"},
        user_id=1,
    )
    assert db.add.called
    added = db.add.call_args[0][0]
    assert isinstance(added, AuditLog)
    assert "should-not-persist" not in (added.details or "")
    assert "***" in (added.details or "")
    assert added.entry_hash
    assert added.prev_hash
    assert entry is added
