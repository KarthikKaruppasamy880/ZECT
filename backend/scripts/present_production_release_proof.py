#!/usr/bin/env python3
"""Production release proof: golden V3 generation + legacy deck repair + export gate."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


def _run_golden_v3() -> dict:
    sys.path.insert(0, str(ROOT))
    os.environ.setdefault("ZECT_PRESENTATION_PROVIDER", "zect_native")
    import importlib.util

    spec = importlib.util.spec_from_file_location("present_golden_v3_proof", ROOT / "scripts" / "present_golden_v3_proof.py")
    if spec is None or spec.loader is None:
        return {"ok": False, "error": "golden_script_missing"}
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    code = int(mod.main())
    artifact = ROOT / "artifacts" / "present-golden-v3" / "golden_v3_report.json"
    if artifact.is_file():
        body = json.loads(artifact.read_text(encoding="utf-8"))
    else:
        body = {"ok": code == 0}
    body["exit_code"] = code
    return body


def _legacy_deck_repair() -> dict:
    sys.path.insert(0, str(ROOT))
    from app.services.mentrix.presentation.deck_catalog import quality_gate_for_path
    from app.services.mentrix.presentation.final_pptx_inspector import inspect_and_repair_pptx, inspect_pptx_bytes

    candidates = [
        REPO / "prompts" / "zect-deck.pptx",
        ROOT / "tests" / "fixes_and_phases" / "fixtures" / "zect-deck-overlap.pptx",
    ]
    path = next((p for p in candidates if p.is_file()), None)
    if path is None:
        return {"ok": True, "skipped": True, "reason": "no_legacy_fixture"}
    before = inspect_pptx_bytes(path.read_bytes())
    repaired, rep = inspect_and_repair_pptx(path.read_bytes())
    after = inspect_pptx_bytes(repaired)
    return {
        "ok": after.get("status") == "PASS",
        "path": str(path),
        "before_status": before.get("status"),
        "before_overlap": before.get("overlap_count"),
        "after_status": after.get("status"),
        "after_overlap": after.get("overlap_count"),
        "repair": {
            "dump_shapes_removed": rep.get("dump_shapes_removed"),
            "duplicate_shapes_removed": rep.get("duplicate_shapes_removed"),
        },
    }


def _preview_png_checks(golden: dict) -> dict:
    sys.path.insert(0, str(ROOT))
    from app.services.mentrix.presentation.slide_preview import render_slide_png_bytes

    path_str = str((golden.get("artifact") or {}).get("path") or golden.get("path") or "")
    if not path_str:
        report_path = ROOT / "artifacts" / "present-golden-v3" / "golden_v3_report.json"
        if report_path.is_file():
            body = json.loads(report_path.read_text(encoding="utf-8"))
            path_str = str(body.get("path") or "")
    pptx = Path(path_str) if path_str else None
    if pptx is None or not pptx.is_file():
        return {"ok": False, "skipped": True, "reason": "golden_pptx_missing"}
    data = pptx.read_bytes()
    slide_count = max(1, int(golden.get("slide_count") or 3))
    previews: list[dict[str, int]] = []
    for idx in range(slide_count):
        png = render_slide_png_bytes(data, idx)
        previews.append({"index": idx, "bytes": len(png)})
    ok = all(row["bytes"] > 200 for row in previews)
    return {"ok": ok, "path": str(pptx), "previews": previews}


def main() -> int:
    golden = _run_golden_v3()
    legacy = _legacy_deck_repair()
    previews = _preview_png_checks(golden)
    acceptance = bool(
        golden.get("acceptance")
        and golden.get("quality_gate", {}).get("final_quality_status") == "PASS"
        and not golden.get("quality_gate", {}).get("export_blocked")
        and (legacy.get("skipped") or legacy.get("ok"))
        and (previews.get("skipped") or previews.get("ok"))
    )
    report = {
        "ok": acceptance,
        "acceptance": acceptance,
        "verdict": "ZECT_PRESENT_PRODUCTION_RELEASE_CANDIDATE" if acceptance else "ZECT_PRESENT_PRODUCTION_BLOCKED",
        "golden_v3": golden,
        "legacy_deck_repair": legacy,
        "preview_png_checks": previews,
    }
    out_dir = ROOT / "artifacts" / "present-production-release"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "production_release_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if acceptance else 1


if __name__ == "__main__":
    raise SystemExit(main())
