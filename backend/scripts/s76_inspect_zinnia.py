"""Inspect candidate Zinnia masters vs synthetic fixture. No secrets."""

from __future__ import annotations

import hashlib
import io
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.fixes_and_phases.pptx_fixtures import make_master_pptx_bytes  # noqa: E402

FILES = [
    Path(r"C:\Users\karuppk\Downloads\ZECT\artifacts\zinnia-master-source.pptx"),
    Path(r"C:\Users\karuppk\Downloads\A1_Zinnia_PPT_Template.pptx"),
    Path(r"C:\Users\karuppk\Downloads\ZECT\.zect\present-templates\masters\zinnia-executive-v1.pptx"),
]


def inspect(path: Path, synth: str) -> None:
    if not path.is_file():
        print("MISSING", path)
        return
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    print("---")
    print(path.name, "bytes", len(data), "sha256", digest, "synthetic_match", digest == synth)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        print(
            "slides",
            sum(1 for n in names if n.startswith("ppt/slides/slide") and n.endswith(".xml")),
            "layouts",
            sum(1 for n in names if "slideLayout" in n and n.endswith(".xml")),
            "media",
            sum(1 for n in names if "/media/" in n),
        )
        theme = next((n for n in names if n.endswith("theme1.xml")), None)
        if theme:
            text = zf.read(theme).decode("utf-8", "ignore")
            fonts = [f.encode("ascii", "replace").decode("ascii") for f in re.findall(r'typeface="([^"]+)"', text)[:12]]
            print("theme_fonts", fonts)


def main() -> None:
    synth = hashlib.sha256(make_master_pptx_bytes()).hexdigest()
    print("synthetic", synth)
    for path in FILES:
        inspect(path, synth)


if __name__ == "__main__":
    main()
