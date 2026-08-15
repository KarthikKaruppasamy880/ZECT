"""S7.6 Presenton smoke + equal corpus + blinded A/B packs. Does not score humans."""

from __future__ import annotations

import hashlib
import json
import os
import random
import shutil
import sys
import time
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from dotenv import load_dotenv
from starlette.datastructures import Headers, UploadFile

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
load_dotenv(BACKEND / ".env", override=True)
sys.path.insert(0, str(BACKEND))

from app.adapters.presentation.presenton_provider import PresentonProvider  # noqa: E402
from app.services.mentrix.presentation import template_registry as tmpl  # noqa: E402
from app.services.mentrix.presentation.document import document_from_pptx_bytes  # noqa: E402
from app.services.mentrix.presentation.document_io import apply_document_to_pptx  # noqa: E402
from app.services.mentrix.presentation.native_provider import ZectNativePresentationProvider  # noqa: E402
from app.services.mentrix.presentation.provider import PresentationGenerateRequest  # noqa: E402
from app.services.mentrix.presentation.service import PresentationService  # noqa: E402
from app.services.mentrix.presentation.template_definition import native_ready  # noqa: E402
from app.services.pptx_parse import parse_pptx_bytes  # noqa: E402
from app.services.presenton_client import list_templates, presenton_base_url, presenton_configured  # noqa: E402
from tests.fixes_and_phases.test_s7_parity_benchmark import CORPUS, _measure  # noqa: E402

OUT = REPO / "test-results" / "s7-parity"
AB = OUT / "human-ab"
NATIVE_DIR = OUT / "s76-native-out"
PRESENTON_DIR = OUT / "s76-presenton-out"
REAL_SHA = "74cb1f7a50c2dcd3ce6c1a41547c45f9666fcb1e353801b87a174c63ecf70dc2"


def _preview(path: Path | None) -> dict:
    if not path or not path.is_file():
        return {"ok": False, "titles": []}
    try:
        slides = parse_pptx_bytes(path.read_bytes())
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200], "titles": []}
    titles = []
    for slide in slides:
        text = (slide.get("text") or "").strip().split("\n")[0][:120]
        titles.append(text)
    return {
        "ok": True,
        "slide_count": len(slides),
        "titles": titles,
        "notes_slides": sum(1 for s in slides if (s.get("notes") or "").strip()),
    }


def _register_user_template(user_id: str) -> str:
    import asyncio

    src = REPO / "artifacts" / "zinnia-master-source.pptx"
    data = src.read_bytes() if src.is_file() else b""
    if len(data) < 1000:
        from tests.fixes_and_phases.pptx_fixtures import make_master_pptx_bytes

        data = make_master_pptx_bytes()

    async def _register():
        upload = UploadFile(
            filename="user-org.pptx",
            file=BytesIO(data),
            headers=Headers(
                {"content-type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}
            ),
        )
        return await tmpl.register_user_pptx(user_id, upload, name="User Org Template", scope="USER")

    row = asyncio.run(_register())
    return str(row["template"]["id"])


def _runtime_record() -> dict:
    return {
        "image": "ghcr.io/presenton/presenton:latest",
        "image_id": "eede239c987b",
        "container": "presenton",
        "ports": "127.0.0.1:5000->80/tcp",
        "llm_provider": "openai",
        "openai_model": "gpt-4o-mini",
        "disable_image_generation": True,
        "auth": "PRESENTON_USERNAME/PASSWORD (not recorded)",
        "note": "Secrets omitted. Standalone Presenton UI is comparison reference only.",
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    AB.mkdir(parents=True, exist_ok=True)
    NATIVE_DIR.mkdir(parents=True, exist_ok=True)
    PRESENTON_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("PRESENTON_GENERATE_RETRIES", "1")

    zinnia_ok = native_ready("zinnia-executive-v1")
    master = tmpl.source_pptx_path("zinnia-executive-v1")
    master_sha = hashlib.sha256(Path(master).read_bytes()).hexdigest() if master and Path(master).is_file() else ""
    if not zinnia_ok or master_sha != REAL_SHA:
        payload = {
            "ok": False,
            "gate": "BLOCKED_EXTERNAL: REAL_ZINNIA_MASTER_REQUIRED",
            "native_ready": zinnia_ok,
            "master_sha": master_sha,
            "expected_sha": REAL_SHA,
        }
        (OUT / "s76-evidence.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload))
        return 2

    listed = list_templates() if presenton_configured() else {}
    presenton_reachable = bool(listed.get("reachable"))
    runtime = _runtime_record()
    (OUT / "presenton-runtime.json").write_text(
        json.dumps({"reachable": presenton_reachable, "base_url": presenton_base_url(), "listed_hint": listed.get("hint"), "runtime": runtime, "template_count": len(list(listed.get("templates") or []))}, indent=2),
        encoding="utf-8",
    )
    if not presenton_reachable:
        payload = {"ok": False, "gate": "BLOCKED_EXTERNAL: PRESENTON_COMPARISON_ENVIRONMENT", "listed": listed.get("hint")}
        (OUT / "s76-evidence.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload))
        return 3

    user_tid = _register_user_template("u-s76")
    native_svc = PresentationService(provider=ZectNativePresentationProvider())
    presenton_svc = PresentationService(provider=PresentonProvider())
    native_presenton_calls = 0

    def _forbid(*_a, **_k):
        nonlocal native_presenton_calls
        native_presenton_calls += 1
        raise AssertionError("native generate called Presenton")

    # Smoke: one Presenton generate through ZECT adapter.
    smoke_t0 = time.perf_counter()
    smoke = presenton_svc.generate(
        PresentationGenerateRequest(
            content="One-slide smoke: confirm Presenton generate through ZECT PresentationService.",
            n_slides=3,
            ui_template_choice="zinnia-executive-v1",
            audience_id="executive",
            filename="s76-presenton-smoke.pptx",
            user_id="u-s76",
        )
    )
    smoke_ms = int((time.perf_counter() - smoke_t0) * 1000)
    (OUT / "presenton-smoke.json").write_text(
        json.dumps(
            {
                "ok": bool(smoke.get("ok")),
                "error": smoke.get("error"),
                "provider": smoke.get("provider"),
                "template_sent": smoke.get("template_sent"),
                "zinnia_verified": smoke.get("zinnia_verified"),
                "path": smoke.get("path"),
                "latency_ms": smoke_ms,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    if not smoke.get("ok"):
        payload = {
            "ok": False,
            "gate": "BLOCKED_EXTERNAL: PRESENTON_COMPARISON_ENVIRONMENT",
            "smoke": smoke.get("error") or smoke.get("block_code"),
        }
        (OUT / "s76-evidence.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload))
        return 3

    rng = random.Random(int(os.environ.get("ZECT_AB_SEED", "202608147")))
    mapping: dict[str, dict] = {}
    rows: list[dict] = []

    with patch("app.services.mentrix.presentation.native_provider.default_pptx_save_dir", lambda: NATIVE_DIR):
        with patch("app.services.presenton_client.default_save_dir", lambda: PRESENTON_DIR):
            for case in CORPUS:
                template_id = user_tid if case["template"] == "USER" else case["template"]
                req_kwargs = dict(
                    content=case["prompt"],
                    n_slides=int(case["n"]),
                    ui_template_choice=template_id,
                    audience_id=case["audience"],
                    filename=f"s76-{case['id']}.pptx",
                    user_id="u-s76",
                    context_items=list(case.get("context") or []),
                    require_llm=True,
                )
                native_t0 = time.perf_counter()
                with patch("app.services.presenton_client.generate_presentation", side_effect=_forbid):
                    native_out = native_svc.generate(PresentationGenerateRequest(**req_kwargs))
                native_ms = int((time.perf_counter() - native_t0) * 1000)
                native_path = Path(str(native_out.get("path") or "")) if native_out.get("ok") else None
                native_measure = _measure(native_path, expected_slides=int(case["n"]))
                editor_ok = False
                if native_path and native_path.is_file():
                    doc = document_from_pptx_bytes(native_path.read_bytes(), path=str(native_path), provider="zect_native")
                    if doc.get("slides"):
                        doc["slides"][0]["notes"] = "S7.6 editor notes round-trip."
                    applied = apply_document_to_pptx(native_path, doc["slides"], user_id="u-s76")
                    editor_ok = bool(applied.get("ooxml_roundtrip"))

                p_req = dict(req_kwargs)
                p_req.pop("require_llm", None)
                if case["template"] == "USER":
                    p_req["ui_template_choice"] = "zinnia-executive-v1"
                p_req["filename"] = f"s76-presenton-{case['id']}.pptx"
                p0 = time.perf_counter()
                presenton_out = presenton_svc.generate(PresentationGenerateRequest(**p_req))
                presenton_ms = int((time.perf_counter() - p0) * 1000)
                p_path = Path(str(presenton_out.get("path") or "")) if presenton_out.get("ok") else None
                presenton_measure = _measure(p_path, expected_slides=int(case["n"]))

                quality_ok = bool(native_out.get("ok")) and native_out.get("planner_mode") == "LLM"
                print(
                    f"[s76] {case['id']} native ok={native_out.get('ok')} mode={native_out.get('planner_mode')} "
                    f"{native_ms}ms presenton ok={presenton_out.get('ok')} {presenton_ms}ms",
                    flush=True,
                )
                rows.append(
                    {
                        "id": case["id"],
                        "prompt": case["prompt"],
                        "audience": case["audience"],
                        "n_slides": case["n"],
                        "template_intent": case["template"],
                        "native": {
                            "ok": bool(native_out.get("ok")),
                            "quality_ok": quality_ok,
                            "error": native_out.get("error"),
                            "provider": native_out.get("provider"),
                            "planner_mode": native_out.get("planner_mode"),
                            "model": native_out.get("model"),
                            "zinnia_verified": native_out.get("zinnia_verified"),
                            "latency_ms": native_ms,
                            "latency": native_out.get("latency") or {},
                            "visual_inventory": native_out.get("visual_inventory"),
                            "measure": native_measure,
                            "editor_roundtrip": editor_ok,
                            "path": str(native_path or ""),
                        },
                        "presenton": {
                            "ok": bool(presenton_out.get("ok")),
                            "error": presenton_out.get("error"),
                            "provider": presenton_out.get("provider"),
                            "zinnia_verified": presenton_out.get("zinnia_verified"),
                            "template_sent": presenton_out.get("template_sent"),
                            "latency_ms": presenton_ms,
                            "measure": presenton_measure,
                            "path": str(p_path or ""),
                        },
                    }
                )

                case_dir = AB / case["id"]
                case_dir.mkdir(parents=True, exist_ok=True)
                native_is_a = bool(rng.getrandbits(1))
                native_label = "A" if native_is_a else "B"
                presenton_label = "B" if native_is_a else "A"
                mapping[case["id"]] = {
                    "A": "zect_native" if native_is_a else "presenton",
                    "B": "presenton" if native_is_a else "zect_native",
                    "native_quality_ok": quality_ok,
                    "presenton_ok": bool(presenton_out.get("ok")),
                }
                if native_path and native_path.is_file():
                    shutil.copy2(native_path, case_dir / f"Deck_{native_label}.pptx")
                if p_path and Path(str(p_path)).is_file():
                    shutil.copy2(p_path, case_dir / f"Deck_{presenton_label}.pptx")
                prev_a = _preview(case_dir / "Deck_A.pptx")
                prev_b = _preview(case_dir / "Deck_B.pptx")
                (case_dir / "prompt.txt").write_text(
                    (
                        f"Goal: {case['id']}\n"
                        f"Audience: {case['audience']}\n"
                        f"Slide count: {case['n']}\n"
                        f"Template intent: {case['template']} (Zinnia Executive unless USER)\n\n"
                        f"Prompt:\n{case['prompt']}\n"
                    ),
                    encoding="utf-8",
                )
                (case_dir / "preview.txt").write_text(
                    "Deck A titles:\n"
                    + "\n".join(f"  {i+1}. {t}" for i, t in enumerate(prev_a.get("titles") or []))
                    + "\n\nDeck B titles:\n"
                    + "\n".join(f"  {i+1}. {t}" for i, t in enumerate(prev_b.get("titles") or []))
                    + "\n",
                    encoding="utf-8",
                )
                (case_dir / "README.txt").write_text(
                    "Review Deck_A.pptx and Deck_B.pptx only. Do not try to infer which engine produced which file.\n"
                    "Score with ZECT_NATIVE_PRESENTATION_HUMAN_AB_SCORECARD.md at the repo root.\n",
                    encoding="utf-8",
                )

    native_quality = sum(1 for r in rows if r["native"].get("quality_ok"))
    presenton_success = sum(1 for r in rows if r["presenton"]["ok"])
    comparable = [
        r["id"]
        for r in rows
        if r["native"].get("quality_ok") and r["presenton"]["ok"]
    ]
    payload = {
        "presenton_reachable": True,
        "presenton_runtime": runtime,
        "real_zinnia_sha256": master_sha,
        "native_presenton_generation_calls": native_presenton_calls,
        "native_llm_quality_success": native_quality,
        "presenton_success": presenton_success,
        "comparable_pairs": comparable,
        "corpus": len(CORPUS),
        "blinded_human_ab_packs": True,
        "blinded_human_ab_scored": False,
        "rows": rows,
    }
    (OUT / "s76-evidence.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (AB / "PRIVATE_MAPPING.json").write_text(
        json.dumps({"DO_NOT_SHARE_BEFORE_SCORING": True, "pairs": mapping}, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "native_llm_quality_success": native_quality,
                "presenton_success": presenton_success,
                "comparable_pairs": comparable,
                "native_presenton_calls": native_presenton_calls,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
