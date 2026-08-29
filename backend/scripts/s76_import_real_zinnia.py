"""Import the real organization Zinnia PPTX into Template Intelligence."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND / ".env", override=True)
sys.path.insert(0, str(BACKEND))

from app.services.mentrix.presentation import template_registry as tmpl
from app.services.mentrix.presentation.template_definition import load_definition, native_ready

_A1 = Path(r"C:\Users\karuppk\Downloads\A1_Zinnia_PPT_Template.pptx")
_ARTIFACT = Path(r"C:\Users\karuppk\Downloads\ZECT\artifacts\zinnia-master-source.pptx")
SRC = _A1 if _A1.is_file() else _ARTIFACT
OUT = Path(__file__).resolve().parents[2] / "test-results" / "s7-parity" / "zinnia-import.json"


def main() -> int:
    if not SRC.is_file():
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({"ok": False, "gate": "BLOCKED_EXTERNAL: REAL_ZINNIA_MASTER_REQUIRED", "path": str(SRC)}), encoding="utf-8")
        print("missing_source")
        return 1
    data = SRC.read_bytes()
    imported = tmpl.import_canonical_master(
        "zinnia-executive-v1",
        data,
        name="A1 Zinnia PPT Template" if SRC == _A1 else "Zinnia Executive",
        filename=SRC.name,
    )
    definition = load_definition("zinnia-executive-v1") or {}
    theme = definition.get("theme") or {}
    payload = {
        "ok": bool(imported.get("ok") and imported.get("native_ready")),
        "source": str(SRC),
        "bytes": len(data),
        "native_ready": native_ready("zinnia-executive-v1"),
        "import": {
            "ok": imported.get("ok"),
            "native_ready": imported.get("native_ready"),
            "error": imported.get("error"),
            "detail": imported.get("detail"),
            "template_id": imported.get("template_id"),
        },
        "definition": {
            "ready": definition.get("ready"),
            "name": definition.get("name"),
            "source_filename": definition.get("source_filename"),
            "source_pptx_sha256": definition.get("source_pptx_sha256"),
            "slide_size": definition.get("slide_size"),
            "theme_colors": (theme.get("colors") if isinstance(theme, dict) else None),
            "theme_fonts": (theme.get("fonts") if isinstance(theme, dict) else None),
            "masters": definition.get("masters"),
            "layout_count": len(list(definition.get("layouts") or [])),
            "layout_names": [str(row.get("name") or "") for row in list(definition.get("layouts") or [])][:24],
        },
        "synthetic_make_master_used": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"ok": payload["ok"], "native_ready": payload["native_ready"], "sha256": payload["definition"].get("source_pptx_sha256"), "layouts": payload["definition"]["layout_count"]}))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
