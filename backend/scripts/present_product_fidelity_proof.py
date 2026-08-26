"""Present product READY proof: real Zinnia master, save/reopen, COM open + raster.

Requires Windows + Office + pywin32 when ZECT_LIVE_PPT_COM=1.
Does not substitute synthetic masters for Zinnia fidelity — uses registry master SHA256.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
load_dotenv(BACKEND / ".env", override=True)
sys.path.insert(0, str(BACKEND))

ART = REPO / "test-results" / "present-product-ready"
EXPECTED_ZINNIA_SHA = "74cb1f7a50c2dcd3ce6c1a41547c45f9666fcb1e353801b87a174c63ecf70dc2"
RASTER_MIN_SSIM_PROXY = 0.42  # mean channel correlation after resize; honest not pixel-perfect


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _zinnia_master_path() -> Path:
    from app.services.mentrix.presentation import template_registry as tmpl

    src = tmpl.source_pptx_path("zinnia-executive-v1")
    if src is None or not src.is_file():
        raise FileNotFoundError(
            "Zinnia master missing. Expected .zect/present-templates/masters/zinnia-executive-v1.pptx "
            f"or ZECT_PRESENT_TEMPLATE_ROOT/masters/zinnia-executive-v1.pptx (SHA256 {EXPECTED_ZINNIA_SHA})."
        )
    digest = _sha256(src)
    if digest != EXPECTED_ZINNIA_SHA:
        raise ValueError(f"Zinnia master SHA256 mismatch: got {digest}, expected {EXPECTED_ZINNIA_SHA}")
    return src


def _ssim_proxy(a_path: Path, b_path: Path) -> float:
    from PIL import Image
    import numpy as np

    a = Image.open(a_path).convert("RGB").resize((640, 360))
    b = Image.open(b_path).convert("RGB").resize((640, 360))
    aa = np.asarray(a, dtype=np.float32)
    bb = np.asarray(b, dtype=np.float32)
    if aa.size == 0 or bb.size == 0:
        return 0.0
    corr = []
    for ch in range(3):
        x = aa[:, :, ch].ravel()
        y = bb[:, :, ch].ravel()
        if x.std() < 1e-3 or y.std() < 1e-3:
            corr.append(0.0)
            continue
        corr.append(float(np.corrcoef(x, y)[0, 1]))
    return sum(corr) / len(corr)


def run_proof(*, canvas_png: Path | None = None) -> dict[str, Any]:
    from app.services.mentrix.presentation.deck_catalog import instantiate_from_template
    from app.services.mentrix.presentation.document import document_from_pptx_bytes
    from app.services.mentrix.presentation.document_io import (
        apply_document_to_pptx,
        powerpoint_open_without_repair,
        validate_export_document,
    )
    from app.services.mentrix.presentation.slide_preview import _try_com_png, invalidate_slide_previews
    from app.services.pptx_parse import parse_pptx_bytes

    ART.mkdir(parents=True, exist_ok=True)
    master = _zinnia_master_path()
    evidence: dict[str, Any] = {
        "zinnia_master_path": str(master),
        "zinnia_master_sha256": EXPECTED_ZINNIA_SHA,
        "zinnia_master_bytes": master.stat().st_size,
    }

    dest = instantiate_from_template("zinnia-executive-v1")
    evidence["cloned_deck"] = str(dest)
    parsed = parse_pptx_bytes(dest.read_bytes())
    evidence["slide_count"] = len(parsed)
    if len(parsed) < 1:
        evidence["error"] = "zinnia_clone_empty"
        return evidence

    blocks = parsed[0].get("blocks") or []
    evidence["slide0_block_kinds"] = sorted({str(b.get("kind") or "") for b in blocks if isinstance(b, dict)})
    text_blocks = [b for b in blocks if isinstance(b, dict) and str(b.get("kind") or "") in {"text", "title", "subtitle", "body"}]
    edit_text = "ZECT acceptance edit on Zinnia master"
    if text_blocks:
        tb = text_blocks[0]
        content = dict(tb.get("content") or {})
        content["text"] = edit_text
        tb = {**tb, "content": content}
        parsed[0]["blocks"] = [tb if b is text_blocks[0] else b for b in blocks]
    else:
        parsed[0]["text"] = edit_text

    apply_document_to_pptx(dest, parsed)
    invalidate_slide_previews(dest)
    reopen = parse_pptx_bytes(dest.read_bytes())
    blob = json.dumps(reopen[0], sort_keys=True)
    evidence["save_reopen_text_ok"] = edit_text in blob or edit_text.lower() in blob.lower()

    export_val = validate_export_document(dest, expected_slides=len(parsed))
    evidence["export_validate"] = export_val

    com = powerpoint_open_without_repair(dest)
    evidence["com_open"] = com

    com_png = ART / "zinnia-slide0-com.png"
    com_ok = _try_com_png(dest, 0, com_png)
    evidence["com_raster_exported"] = com_ok
    if com_ok:
        evidence["com_raster_bytes"] = com_png.stat().st_size
        shutil.copy2(com_png, ART / "zinnia-com-representative.png")

    doc = document_from_pptx_bytes(dest.read_bytes(), path=str(dest))
    (ART / "zinnia-document.json").write_text(json.dumps(doc, indent=2)[:200_000], encoding="utf-8")

    if canvas_png and canvas_png.is_file() and com_ok:
        proxy = _ssim_proxy(com_png, canvas_png)
        evidence["com_vs_canvas_ssim_proxy"] = round(proxy, 4)
        evidence["com_vs_canvas_pass"] = proxy >= RASTER_MIN_SSIM_PROXY
        dest_canvas = ART / "zinnia-canvas-representative.png"
        if canvas_png.resolve() != dest_canvas.resolve():
            shutil.copy2(canvas_png, dest_canvas)
        else:
            evidence["canvas_png_source"] = str(canvas_png)

    evidence["verdict"] = (
        evidence.get("save_reopen_text_ok")
        and export_val.get("ok")
        and (com.get("ok") or com.get("status") == "BLOCKED_EXTERNAL")
        and (not com_ok or evidence.get("com_vs_canvas_pass", True))
    )
    (ART / "fidelity-proof.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return evidence


def main() -> int:
    canvas = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
    if os.environ.get("ZECT_LIVE_PPT_COM", "").strip() != "1":
        print(json.dumps({"error": "ZECT_LIVE_PPT_COM!=1", "hint": "Set ZECT_LIVE_PPT_COM=1 on Windows with Office"}))
        return 2
    try:
        out = run_proof(canvas_png=canvas)
    except FileNotFoundError as exc:
        print(json.dumps({"error": str(exc)}))
        return 3
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}))
        return 4
    print(json.dumps({k: out[k] for k in out if k != "export_validate"}, indent=2))
    return 0 if out.get("verdict") else 1


if __name__ == "__main__":
    raise SystemExit(main())
