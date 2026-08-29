"""Discover run/build/test recipes from authorized roots. Manifests are untrusted evidence."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

_UNSAFE = re.compile(r"(\.\.|[;&|`$]|rm\s+-rf|curl\s+|wget\s+|powershell\s+-enc)", re.I)

ALLOWED_KINDS = ("full", "frontend", "backend", "tests")

RUN_PROFILES_DIR = ".zect/run-profiles"

# Common Makefile targets worth offering as recipes -- deliberately small
# and specific rather than every target, since Makefiles routinely define
# targets (clean, lint, deploy, publish) that are not "run/start this app".
_MAKE_TARGET_KINDS = {
    "run": "full",
    "start": "full",
    "dev": "frontend",
    "serve": "full",
    "test": "tests",
    "build": "full",
}


def _safe_command(cmd: str) -> bool:
    c = (cmd or "").strip()
    if not c or len(c) > 240:
        return False
    if _UNSAFE.search(c):
        return False
    return True


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return path.name


def discover_runtime_recipes(workspace_root: str) -> dict[str, Any]:
    root = Path(workspace_root).expanduser().resolve()
    if not root.is_dir():
        return {"ok": False, "error": "root_not_found", "recipes": []}

    recipes: list[dict[str, Any]] = []

    zm = root / "zinnia-modern"
    if zm.is_dir() and (zm / "package.json").is_file():
        recipes.append(
            {
                "id": "zoas-full",
                "kind": "full",
                "label": "ZOAS full stack",
                "command": "npm run start:all",
                "cwdRel": "zinnia-modern",
                "port": 3000,
                "confirmRequired": True,
                "evidence": "zinnia-modern/package.json scripts.start:all",
            }
        )
        fe = zm / "frontend" / "package.json"
        if fe.is_file():
            recipes.append(
                {
                    "id": "zoas-frontend",
                    "kind": "frontend",
                    "label": "ZOAS frontend",
                    "command": "npm run dev",
                    "cwdRel": "zinnia-modern/frontend",
                    "port": 3000,
                    "confirmRequired": True,
                    "evidence": "zinnia-modern/frontend/package.json",
                }
            )
        be = zm / "backend"
        if be.is_dir() and ((be / "main.py").is_file() or (be / "requirements.txt").is_file()):
            recipes.append(
                {
                    "id": "zoas-backend",
                    "kind": "backend",
                    "label": "ZOAS backend",
                    "command": "uvicorn main:app --reload --port 8000 --host 127.0.0.1",
                    "cwdRel": "zinnia-modern/backend",
                    "port": 8000,
                    "confirmRequired": True,
                    "evidence": "zinnia-modern/backend (uvicorn) — uses local DATABASE_URL; Postgres is not started by ZECT",
                }
            )
            recipes.append(
                {
                    "id": "zoas-tests",
                    "kind": "tests",
                    "label": "ZOAS pytest",
                    "command": "pytest -q",
                    "cwdRel": "zinnia-modern/backend",
                    "confirmRequired": True,
                    "evidence": "zinnia-modern/backend tests/",
                }
            )

    fe_pkg = root / "frontend" / "package.json"
    pom = root / "backend" / "pom.xml"
    if fe_pkg.is_file() and pom.is_file() and not any(str(r.get("id") or "").startswith("zoas-") for r in recipes):
        recipes.append(
            {
                "id": "zaf-frontend",
                "kind": "frontend",
                "label": "ZAF frontend",
                "command": "npm run dev",
                "cwdRel": "frontend",
                "port": 5173,
                "confirmRequired": True,
                "evidence": "frontend/package.json + backend/pom.xml",
            }
        )

    if (root / "zect.ps1").is_file() and (root / "frontend").is_dir() and (root / "backend").is_dir():
        recipes.append(
            {
                "id": "zect-restart",
                "kind": "full",
                "label": "ZECT stack restart",
                "command": "pwsh -File zect.ps1 restart",
                "cwdRel": ".",
                "confirmRequired": True,
                "evidence": "zect.ps1 in this checkout — host stack control, not Companion arbitrary shell",
            }
        )

    pkg = root / "package.json"
    if pkg.is_file() and not any(r["id"] == "zoas-full" for r in recipes):
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
        for name, kind in (("start:all", "full"), ("dev", "frontend"), ("start", "frontend"), ("test", "tests")):
            cmd = scripts.get(name)
            if isinstance(cmd, str) and _safe_command(f"npm run {name}"):
                recipes.append(
                    {
                        "id": f"pkg-{name}",
                        "kind": kind,
                        "label": f"npm run {name}",
                        "command": f"npm run {name}",
                        "cwdRel": ".",
                        "confirmRequired": True,
                        "evidence": f"package.json scripts.{name}",
                    }
                )

    if (root / "requirements.txt").is_file() or (root / "pyproject.toml").is_file():
        if not any(r["kind"] == "backend" for r in recipes):
            recipes.append(
                {
                    "id": "py-backend",
                    "kind": "backend",
                    "label": "Python API",
                    "command": "uvicorn app.main:app --reload --port 8000 --host 127.0.0.1",
                    "cwdRel": ".",
                    "port": 8000,
                    "confirmRequired": True,
                    "evidence": "requirements.txt or pyproject.toml — DB is operator .env, not invented",
                }
            )
        if not any(r["kind"] == "tests" for r in recipes):
            recipes.append(
                {
                    "id": "py-tests",
                    "kind": "tests",
                    "label": "pytest",
                    "command": "pytest -q",
                    "cwdRel": ".",
                    "confirmRequired": True,
                    "evidence": "Python project tests",
                }
            )

    for compose_name in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
        compose_path = root / compose_name
        if compose_path.is_file() and not any(r["id"] == "docker-compose-up" for r in recipes):
            recipes.append(
                {
                    "id": "docker-compose-up",
                    "kind": "full",
                    "label": "docker compose up",
                    "command": "docker compose up",
                    "cwdRel": ".",
                    "confirmRequired": True,
                    "evidence": compose_name,
                }
            )
            break

    pom = root / "pom.xml"
    if pom.is_file():
        if not any(r["kind"] == "backend" for r in recipes):
            recipes.append(
                {
                    "id": "maven-run",
                    "kind": "backend",
                    "label": "mvn spring-boot:run",
                    "command": "mvn spring-boot:run",
                    "cwdRel": ".",
                    "confirmRequired": True,
                    "evidence": "pom.xml",
                }
            )
        if not any(r["kind"] == "tests" for r in recipes):
            recipes.append(
                {
                    "id": "maven-test",
                    "kind": "tests",
                    "label": "mvn test",
                    "command": "mvn test",
                    "cwdRel": ".",
                    "confirmRequired": True,
                    "evidence": "pom.xml",
                }
            )

    gradle_file = next((root / n for n in ("build.gradle", "build.gradle.kts") if (root / n).is_file()), None)
    if gradle_file is not None:
        gradlew = "gradlew.bat" if (root / "gradlew.bat").is_file() else "./gradlew"
        if not any(r["kind"] == "backend" for r in recipes):
            recipes.append(
                {
                    "id": "gradle-run",
                    "kind": "backend",
                    "label": f"{gradlew} bootRun",
                    "command": f"{gradlew} bootRun",
                    "cwdRel": ".",
                    "confirmRequired": True,
                    "evidence": gradle_file.name,
                }
            )
        if not any(r["kind"] == "tests" for r in recipes):
            recipes.append(
                {
                    "id": "gradle-test",
                    "kind": "tests",
                    "label": f"{gradlew} test",
                    "command": f"{gradlew} test",
                    "cwdRel": ".",
                    "confirmRequired": True,
                    "evidence": gradle_file.name,
                }
            )

    makefile = next((root / n for n in ("Makefile", "makefile") if (root / n).is_file()), None)
    if makefile is not None:
        try:
            make_text = makefile.read_text(encoding="utf-8", errors="replace")
        except OSError:
            make_text = ""
        targets = set(re.findall(r"^([a-zA-Z0-9_-]+):(?!=)", make_text, re.MULTILINE))
        for target, kind in _MAKE_TARGET_KINDS.items():
            if target in targets and not any(r["id"] == f"make-{target}" for r in recipes):
                recipes.append(
                    {
                        "id": f"make-{target}",
                        "kind": kind,
                        "label": f"make {target}",
                        "command": f"make {target}",
                        "cwdRel": ".",
                        "confirmRequired": True,
                        "evidence": f"{makefile.name} target '{target}'",
                    }
                )

    # Nested package.json (one level) — never follow ..
    if not recipes:
        for child in sorted(root.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            nested = child / "package.json"
            if not nested.is_file():
                continue
            rel = _rel(root, child)
            recipes.append(
                {
                    "id": f"nested-{slug_id(rel)}-dev",
                    "kind": "frontend",
                    "label": f"{rel} npm run dev",
                    "command": "npm run dev",
                    "cwdRel": rel,
                    "confirmRequired": True,
                    "evidence": f"{rel}/package.json",
                }
            )
            break

    safe = [r for r in recipes if _safe_command(str(r.get("command") or ""))]
    confirmed = load_confirmed_profile(str(root))
    confirmed_id = str((confirmed or {}).get("recipe_id") or "")
    if confirmed_id and any(r["id"] == confirmed_id for r in safe):
        default_id = confirmed_id
    else:
        default_id = next((r["id"] for r in safe if r["kind"] == "full"), safe[0]["id"] if safe else "")
    return {
        "ok": True,
        "root": str(root),
        "default_id": default_id,
        "confirmed_profile": confirmed,
        "recipes": safe,
        "postgres_note": "ZECT does not start PostgreSQL. Use the project's local DATABASE_URL.",
    }


def slug_id(rel: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", rel).strip("-").lower()[:32]


def _profile_path(root: Path) -> Path:
    return root / RUN_PROFILES_DIR / "profile.json"


def save_confirmed_profile(workspace_root: str, recipe: dict[str, Any]) -> dict[str, Any]:
    """Persist the human/agent-confirmed recipe for this repo to
    .zect/run-profiles/profile.json, so start_app doesn't have to
    re-discover/re-disambiguate every single call -- the next
    discover_runtime_recipes() returns it as default_id directly."""
    root = Path(workspace_root).expanduser().resolve()
    path = _profile_path(root)
    payload = {"recipe_id": recipe.get("id"), "recipe": recipe, "confirmed_at": time.time()}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {"ok": True, "path": str(path)}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}


def load_confirmed_profile(workspace_root: str) -> dict[str, Any] | None:
    root = Path(workspace_root).expanduser().resolve()
    path = _profile_path(root)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def resolve_recipe(workspace_root: str, recipe_id: str) -> dict[str, Any]:
    discovered = discover_runtime_recipes(workspace_root)
    for row in discovered.get("recipes") or []:
        if row.get("id") == recipe_id:
            cwd = Path(workspace_root).resolve() / str(row.get("cwdRel") or ".")
            if ".." in Path(str(row.get("cwdRel") or ".")).parts:
                return {"ok": False, "error": "path_escape"}
            return {**row, "ok": True, "cwd": str(cwd)}
    return {"ok": False, "error": "recipe_not_found"}
