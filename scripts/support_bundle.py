#!/usr/bin/env python3
"""Phase 11 Stage A — collect a redacted support bundle (no secrets)."""

from __future__ import annotations

import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

try:
    from app.security.redact import redact_secrets
except Exception:  # pragma: no cover
    def redact_secrets(v):  # type: ignore
        return v


def main() -> int:
    out_dir = ROOT / "artifacts" / "support-bundles"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"zect-support-{stamp}.json"

    env_safe = {
        k: ("***" if any(s in k.upper() for s in ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")) else v[:80])
        for k, v in os.environ.items()
        if k.startswith("ZECT_") or k.startswith("MENTRIX_") or k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY")
    }
    # Always mask known secret envs even if truncated above
    for k in list(env_safe):
        if any(s in k.upper() for s in ("KEY", "TOKEN", "SECRET", "PASSWORD")):
            env_safe[k] = "***"

    payload = {
        "generated_at": stamp,
        "platform": platform.platform(),
        "python": sys.version,
        "cwd": str(ROOT),
        "env_redacted": env_safe,
        "notes": "Secrets redacted. Attach logs manually if needed.",
    }
    path.write_text(json.dumps(redact_secrets(payload), indent=2), encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
