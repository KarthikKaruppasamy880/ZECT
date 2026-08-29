"""R1.5 sidecar packaging — userData sqlite, vault key, no installer secrets."""

from __future__ import annotations

from pathlib import Path


def test_run_api_launcher_has_no_baked_secrets():
    root = Path(__file__).resolve().parents[3]
    launcher = (root / "electron" / "resources" / "backend" / "run-api.ps1").read_text(encoding="utf-8")
    for needle in ("zect-dev-local", "sk-", "ghp_", "ENCRYPTION_KEY=", "OPENAI_API_KEY=sk"):
        assert needle not in launcher
    assert "ZECT_USER_DATA" in launcher
    assert "python-runtime" in launcher


def test_userdata_vault_key_generated(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_USER_DATA", str(tmp_path))
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    from app.security.vault import VaultManager

    vm = VaultManager()
    key = vm.get_key()
    assert key
    key_file = tmp_path / "config" / "encryption.key"
    assert key_file.is_file()
    assert key_file.read_text(encoding="utf-8").strip()
    # Do not print key; just ensure file is not empty and not world-documented
    assert "ENCRYPTION_KEY not set" not in key_file.read_text(encoding="utf-8")
