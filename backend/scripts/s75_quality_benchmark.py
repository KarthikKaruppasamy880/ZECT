"""S7.5 live quality benchmark — Model Gateway planner required. Not pytest.

Loads backend/.env (so OPENAI_API_KEY / Presenton are real). Heuristic native
output is recorded as a quality failure. Writes blinded A/B packs; does not
invent human scores.

Usage (from repo root or backend/):
  python scripts/s75_quality_benchmark.py
"""

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

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
load_dotenv(BACKEND / ".env", override=True)
sys.path.insert(0, str(BACKEND))

from app.adapters.presentation.presenton_provider import PresentonProvider  # noqa: E402
from app.services.mentrix.presentation import template_registry as tmpl  # noqa: E402
from app.services.mentrix.presentation.document import document_from_pptx_bytes  # noqa: E402
from app.services.mentrix.presentation.document_io import apply_document_to_pptx  # noqa: E402
from app.services.mentrix.presentation.native_provider import ZectNativePresentationProvider  # noqa: E402
from app.services.mentrix.presentation.provider import PresentationGenerateRequest  # noqa: E402
from app.services.mentrix.presentation.service import PresentationService  # noqa: E402
from app.services.presenton_client import list_templates, presenton_base_url, presenton_configured  # noqa: E402
from tests.fixes_and_phases.pptx_fixtures import make_master_pptx_bytes  # noqa: E402
from tests.fixes_and_phases.test_s7_parity_benchmark import CORPUS, _measure  # noqa: E402

OUT = REPO / "test-results" / "s75-parity"
AB = OUT / "ab"
ZINNIA_UUID = "e7ac06b6-36e7-4460-b476-00bcaa98207d"
SCORE_DIMS = [
    "narrative_coherence",
    "prompt_relevance",
    "titles",
    "visual_hierarchy",
    "template_fidelity",
    "layout",
    "density_readability",
    "image_relevance",
    "chart_table_quality",
    "executive_usefulness",
    "technical_usefulness",
    "notes",
    "overall_quality",
]


def _try_download_presenton_master() -> dict:
    """Attempt to fetch the org Zinnia PPTX master from Presenton. Never invent bytes."""
    base = presenton_base_url()
    result: dict = {
        "ok": False,
        "gate": "BLOCKED_EXTERNAL",
        "reason": "presenton_not_configured",
        "paths_tried": [],
    }
    if not base:
        return result
    import httpx
    from app.services.presenton_client import _client_kwargs, _session_headers

    uuid = ZINNIA_UUID
    candidates = [
        f"{base}/api/v1/ppt/template/{uuid}",
        f"{base}/api/v1/ppt/template/{uuid}/download",
        f"{base}/api/v1/ppt/templates/{uuid}",
        f"{base}/api/v1/ppt/templates/{uuid}/download",
        f"{base}/api/v1/ppt/template-management/get-templates/{uuid}",
        f"{base}/api/v1/ppt/template/get/{uuid}",
    ]
    result["paths_tried"] = candidates
    try:
        with httpx.Client(**_client_kwargs()) as client:
            headers = _session_headers(client)
            listed = list_templates()
            result["presenton_reachable"] = bool(listed.get("reachable"))
            result["presenton_template_ids"] = [t.get("id") for t in list(listed.get("templates") or [])][:30]
            has_uuid = uuid in {str(i) for i in result["presenton_template_ids"]}
            result["uuid_listed"] = has_uuid
            for url in candidates:
                try:
                    res = client.get(url, headers=headers, timeout=20.0)
                except Exception as exc:  # noqa: BLE001
                    result.setdefault("errors", []).append(f"{url}: {exc}"[:200])
                    continue
                ctype = (res.headers.get("content-type") or "").lower()
                body = res.content or b""
                result.setdefault("http", []).append({"url": url, "status": res.status_code, "ctype": ctype, "bytes": len(body)})
                if res.status_code >= 400 or not body:
                    continue
                if body[:4] == b"PK\x03\x04" or "presentation" in ctype or url.endswith(".pptx"):
                    dest = OUT / "zinnia-presenton-master.pptx"
                    dest.write_bytes(body)
                    result.update({"ok": True, "gate": "DOWNLOADED", "path": str(dest), "sha256": hashlib.sha256(body).hexdigest()})
                    return result
    except Exception as exc:  # noqa: BLE001
        result["reason"] = str(exc)[:300]
        return result
    result["reason"] = "presenton_has_no_downloadable_pptx_master"
    return result


def _synthetic_sha() -> str:
    return hashlib.sha256(make_master_pptx_bytes()).hexdigest()


def _existing_master_sha() -> str:
    path = REPO / ".zect" / "present-templates" / "masters" / "zinnia-executive-v1.pptx"
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    return ""


def _register_user_template(user_id: str) -> str:
    import asyncio

    async def _register():
        upload = UploadFile(
            filename="user.pptx",
            file=BytesIO(make_master_pptx_bytes()),
            headers=Headers(
                {"content-type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}
            ),
        )
        return await tmpl.register_user_pptx(user_id, upload, name="User Exec", scope="USER")

    row = asyncio.run(_register())
    return str(row["template"]["id"])


def _write_scorecard() -> None:
    lines = [
        "# S7.5 blinded Presenton vs ZECT human A/B scorecard",
        "",
        "Do **not** look at `ab/KEY_DO_NOT_SHARE.json` before scoring.",
        "Each case folder contains `Deck_A.pptx` and `Deck_B.pptx` only.",
        "Score 1–5 (1=poor, 5=excellent). Winner: A, B, or Tie.",
        "Prefer two independent raters. The generator/model is not a substitute.",
        "",
        "| Case | " + " | ".join(SCORE_DIMS) + " | Winner | Comments |",
        "|------|" + "|".join(["---"] * (len(SCORE_DIMS) + 2)) + "|",
    ]
    for case in CORPUS:
        lines.append(f"| {case['id']} | " + " | ".join([""] * (len(SCORE_DIMS) + 2)) + "|")
    lines.extend(
        [
            "",
            "## Rater",
            "- Name:",
            "- Date:",
            "- Notes:",
            "",
            "Copy completed scores into `SCORECARD_RESULTS.json` (see template).",
        ]
    )
    (OUT / "SCORECARD.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    template = {
        "raters": [],
        "instruction": "Fill scores 1-5 per dimension, winner A|B|Tie. Do not consult KEY_DO_NOT_SHARE.json first.",
        "dimensions": SCORE_DIMS,
        "cases": {c["id"]: {"A": {}, "B": {}, "winner": "", "comments": ""} for c in CORPUS},
    }
    (OUT / "SCORECARD_RESULTS.json").write_text(json.dumps(template, indent=2), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    AB.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("PRESENTON_GENERATE_RETRIES", "1")
    os.environ["ZECT_PRESENT_TEMPLATE_ROOT"] = str(OUT / "templates")
    os.environ["ZECT_PRESENT_ASSET_ROOT"] = str(OUT / "assets")
    native_out_dir = OUT / "native-out"
    presenton_out_dir = OUT / "presenton-out"
    native_out_dir.mkdir(parents=True, exist_ok=True)
    presenton_out_dir.mkdir(parents=True, exist_ok=True)

    zinnia_probe = _try_download_presenton_master()
    synth = _synthetic_sha()
    existing = _existing_master_sha()
    real_bytes: bytes | None = None
    if zinnia_probe.get("ok") and Path(str(zinnia_probe.get("path") or "")).is_file():
        real_bytes = Path(str(zinnia_probe["path"])).read_bytes()
    zinnia_gate = "BLOCKED_EXTERNAL"
    zinnia_note = "No downloadable organization Zinnia PPTX master; synthetic make_master_pptx_bytes cannot prove brand fidelity."
    if real_bytes and hashlib.sha256(real_bytes).hexdigest() != synth:
        imported = tmpl.import_canonical_master(
            "zinnia-executive-v1",
            real_bytes,
            name="Zinnia Executive",
            filename="zinnia-org.pptx",
        )
        zinnia_gate = "REAL_MASTER" if imported.get("native_ready") else "IMPORT_FAILED"
        zinnia_note = f"Imported Presenton-downloaded master native_ready={imported.get('native_ready')}"
    else:
        tmpl.import_canonical_master(
            "zinnia-executive-v1",
            make_master_pptx_bytes(),
            name="Zinnia Executive",
            filename="exec.pptx",
        )
        if existing and existing == synth:
            zinnia_note = "Repo .zect master hash matches synthetic test fixture."
        zinnia_probe["existing_master_sha256"] = existing
        zinnia_probe["synthetic_sha256"] = synth

    user_tid = _register_user_template("u-s75")
    listed = list_templates() if presenton_configured() else {}
    presenton_reachable = bool(listed.get("reachable"))

    native_svc = PresentationService(provider=ZectNativePresentationProvider())
    presenton_svc = PresentationService(provider=PresentonProvider())

    def _native_save():
        return native_out_dir

    def _presenton_save():
        return presenton_out_dir

    rows: list[dict] = []
    native_presenton_calls = 0
    rng = random.Random(20260814)
    mapping: dict[str, dict] = {}

    def _count_presenton(*_a, **_k):
        nonlocal native_presenton_calls
        native_presenton_calls += 1
        raise AssertionError("native generate called Presenton")

    with patch("app.services.mentrix.presentation.native_provider.default_pptx_save_dir", _native_save):
        with patch("app.services.presenton_client.default_save_dir", _presenton_save):
            for case in CORPUS:
                template_id = user_tid if case["template"] == "USER" else case["template"]
                req_kwargs = dict(
                    content=case["prompt"],
                    n_slides=int(case["n"]),
                    ui_template_choice=template_id,
                    audience_id=case["audience"],
                    filename=f"s75-{case['id']}.pptx",
                    user_id="u-s75",
                    context_items=list(case.get("context") or []),
                    require_llm=True,
                )
                native_t0 = time.perf_counter()
                with patch("app.services.presenton_client.generate_presentation", side_effect=_count_presenton):
                    native_out = native_svc.generate(PresentationGenerateRequest(**req_kwargs))
                native_ms = int((time.perf_counter() - native_t0) * 1000)
                native_path = Path(str(native_out.get("path") or "")) if native_out.get("ok") else None
                native_measure = _measure(native_path, expected_slides=int(case["n"]))
                editor_ok = False
                if native_path and native_path.is_file():
                    doc = document_from_pptx_bytes(native_path.read_bytes(), path=str(native_path), provider="zect_native")
                    if doc.get("slides"):
                        doc["slides"][0]["notes"] = "S7.5 editor notes round-trip."
                    applied = apply_document_to_pptx(native_path, doc["slides"], user_id="u-s75")
                    editor_ok = bool(applied.get("ooxml_roundtrip"))

                presenton_out: dict = {"ok": False, "error": "presenton_unreachable"}
                presenton_ms = 0
                presenton_measure = _measure(None, expected_slides=int(case["n"]))
                if presenton_reachable:
                    p_template = "general" if case["template"] == "USER" else case["template"]
                    p_req = dict(req_kwargs)
                    p_req["ui_template_choice"] = p_template
                    p_req.pop("require_llm", None)
                    p_req["filename"] = f"s75-presenton-{case['id']}.pptx"
                    p0 = time.perf_counter()
                    presenton_out = presenton_svc.generate(PresentationGenerateRequest(**p_req))
                    presenton_ms = int((time.perf_counter() - p0) * 1000)
                    p_path = Path(str(presenton_out.get("path") or "")) if presenton_out.get("ok") else None
                    presenton_measure = _measure(p_path, expected_slides=int(case["n"]))
                else:
                    p_path = None

                quality_ok = bool(native_out.get("ok")) and native_out.get("planner_mode") == "LLM"
                print(
                    f"[s75] {case['id']} native ok={native_out.get('ok')} mode={native_out.get('planner_mode')} "
                    f"{native_ms}ms presenton ok={presenton_out.get('ok')} {presenton_ms}ms",
                    flush=True,
                )
                row = {
                    "id": case["id"],
                    "n_slides": case["n"],
                    "native": {
                        "ok": bool(native_out.get("ok")),
                        "quality_ok": quality_ok,
                        "error": native_out.get("error"),
                        "provider": native_out.get("provider"),
                        "zinnia_verified": native_out.get("zinnia_verified"),
                        "planner_mode": native_out.get("planner_mode"),
                        "model": native_out.get("model"),
                        "degraded": bool(native_out.get("degraded")),
                        "fallback_reason": native_out.get("fallback_reason"),
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
                        "skipped": not presenton_reachable,
                    },
                }
                rows.append(row)

                case_dir = AB / case["id"]
                case_dir.mkdir(parents=True, exist_ok=True)
                assign_native_a = bool(rng.getrandbits(1))
                native_label = "A" if assign_native_a else "B"
                presenton_label = "B" if assign_native_a else "A"
                mapping[case["id"]] = {
                    "A": "zect_native" if assign_native_a else "presenton",
                    "B": "presenton" if assign_native_a else "zect_native",
                    "native_quality_ok": quality_ok,
                    "presenton_ok": bool(presenton_out.get("ok")),
                }
                if native_path and native_path.is_file():
                    shutil.copy2(native_path, case_dir / f"Deck_{native_label}.pptx")
                if p_path and Path(str(p_path)).is_file():
                    shutil.copy2(p_path, case_dir / f"Deck_{presenton_label}.pptx")
                (case_dir / "README.txt").write_text(
                    "Score Deck_A.pptx vs Deck_B.pptx. Do not ask which engine produced which file.\n",
                    encoding="utf-8",
                )

    native_quality = sum(1 for r in rows if r["native"].get("quality_ok"))
    presenton_success = sum(1 for r in rows if r["presenton"]["ok"])
    latencies = [r["native"]["latency"] for r in rows if r["native"].get("quality_ok")]
    profile = {
        "n_llm_success": native_quality,
        "mean_total_generate_ms": int(sum(int(x.get("total_generate_ms") or 0) for x in latencies) / max(len(latencies), 1)),
        "mean_llm_ms": int(sum(int(x.get("llm_ms") or 0) for x in latencies) / max(len(latencies), 1)),
        "mean_visual_plan_ms": int(sum(int(x.get("visual_plan_ms") or 0) for x in latencies) / max(len(latencies), 1)),
        "mean_render_ms": int(sum(int(x.get("render_ms") or 0) for x in latencies) / max(len(latencies), 1)),
        "mean_presenton_ms": int(
            sum(r["presenton"]["latency_ms"] for r in rows if r["presenton"]["ok"]) / max(presenton_success, 1)
        ),
        "product_latency_target": "Native LLM plan+render should complete in well under 3 minutes per typical 5-slide deck; unexplained multi-minute waits after the PPTX exists are a UX bug, not planning time.",
    }
    payload = {
        "presenton_configured": presenton_configured(),
        "presenton_base_url": presenton_base_url() or "",
        "presenton_reachable": presenton_reachable,
        "native_presenton_generation_calls": native_presenton_calls,
        "native_llm_quality_success": native_quality,
        "presenton_success": presenton_success,
        "corpus": len(CORPUS),
        "blinded_human_ab": False,
        "blinded_human_ab_packs": True,
        "zinnia_gate": zinnia_gate,
        "zinnia_note": zinnia_note,
        "zinnia_probe": {k: v for k, v in zinnia_probe.items() if k != "http" or True},
        "latency_profile": profile,
        "rows": rows,
    }
    (OUT / "evidence.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (OUT / "latency_profile.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
    (AB / "KEY_DO_NOT_SHARE.json").write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    _write_scorecard()
    print(json.dumps({"native_llm_quality_success": native_quality, "presenton_success": presenton_success, "zinnia_gate": zinnia_gate}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
