"""Copy pinned backend sources + create a venv runtime under electron/resources/backend.

Does not copy .env or secrets. Runtime is gitignored; installer build includes it via extraResources.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

SKIP_DIR_NAMES = {".venv", "__pycache__", "tests", ".pytest_cache", "data"}


def _copy_app(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name in SKIP_DIR_NAMES or item.suffix == ".pyc":
            continue
        target = dest / item.name
        if item.is_dir():
            shutil.copytree(
                item,
                target,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".env", "*.db", "*.sqlite3"),
            )
        else:
            if item.name in {".env"} or item.suffix in {".db", ".sqlite3"}:
                continue
            shutil.copy2(item, target)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-venv", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    backend = root / "backend"
    dest = root / "electron" / "resources" / "backend"
    src_out = dest / "src"
    runtime = dest / "python-runtime"
    req = backend / "requirements.txt"
    if not req.is_file():
        print("requirements.txt missing", file=sys.stderr)
        return 2

    _copy_app(backend, src_out)
    # Drop tests from the packaged tree (copied if skip list missed nested).
    tests = src_out / "tests"
    if tests.exists():
        shutil.rmtree(tests, ignore_errors=True)
    print(f"copied backend sources -> {src_out}")

    if args.skip_venv:
        return 0

    if sys.platform != "win32":
        print("Windows python-runtime is produced on win32 only; skipping venv on this host")
        return 0

    if runtime.exists():
        shutil.rmtree(runtime)
    subprocess.check_call([sys.executable, "-m", "venv", str(runtime)])
    py = runtime / "Scripts" / "python.exe"
    if not py.is_file():
        py = runtime / "bin" / "python"
    subprocess.check_call([str(py), "-m", "pip", "install", "--upgrade", "pip", "wheel"])
    subprocess.check_call([str(py), "-m", "pip", "install", "-r", str(req)])
    print(f"python-runtime ready -> {runtime}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
