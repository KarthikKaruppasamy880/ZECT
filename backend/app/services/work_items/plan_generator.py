"""CP-05 -- grounded PLAN.md generator + typed file-impact schema.

Built exclusively on CP-04's ContextPackage/EvidenceLedger -- this module
does not retrieve or re-derive repository evidence itself; it only
classifies, validates, and renders what the ContextPackage already proved.

Root cause this replaces: llm_phase.run_plan()'s system prompt literally
contained the instruction text "port module N", which the model echoed back
verbatim as a real phase heading (finding B1), and nothing in the pipeline
asked for -- or validated -- concrete file paths at all. The file-impact
list here is deterministically seeded from VERIFIED evidence and
deterministically validated before it ever reaches the rendered plan; the
model's own proposals (via llm_phase.run_grounded_plan) are treated as
untrusted candidates, never facts.
"""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.services.work_items.context_package import ContextPackage, STATUS_NOT_FOUND, STATUS_VERIFIED

ACTION_MODIFY_EXISTING = "MODIFY_EXISTING"
ACTION_CREATE_NEW = "CREATE_NEW"
ACTION_DELETE_EXISTING = "DELETE_EXISTING"
ACTION_REFERENCE_ONLY = "REFERENCE_ONLY"
ACTION_NO_CHANGE = "NO_CHANGE"
FILE_IMPACT_ACTIONS = (
    ACTION_MODIFY_EXISTING,
    ACTION_CREATE_NEW,
    ACTION_DELETE_EXISTING,
    ACTION_REFERENCE_ONLY,
    ACTION_NO_CHANGE,
)
_EXISTENCE_REQUIRED = frozenset({ACTION_MODIFY_EXISTING, ACTION_DELETE_EXISTING})

# Known placeholder/template leftovers -- the exact class of defect that
# already reached a real generated plan once ("Port Module N", finding B1).
# Matching a real, legitimate identifier here is intentionally not a
# concern: these patterns are meaningless as actual paths/module names.
_PLACEHOLDER_PATTERNS = [
    re.compile(r"port module\s*n\b", re.IGNORECASE),
    re.compile(r"\bmodule\s+n\b", re.IGNORECASE),
    re.compile(r"example[/\\]file\.\w+", re.IGNORECASE),
    re.compile(r"\bfoo\.py\b|\bbar\.py\b|\bbaz\.py\b", re.IGNORECASE),
    re.compile(r"\bTBD\b"),
    re.compile(r"<[a-z_]+>"),  # generic angle-bracket placeholder e.g. <module_name>
    re.compile(r"\{\{.*?\}\}"),  # unresolved template syntax
]

# Extension -> language, and language -> the build markers that identify a
# repo as primarily that language. Order matters only for display.
_EXT_LANGUAGE = {
    ".java": "java", ".py": "python", ".ts": "typescript", ".tsx": "typescript",
    ".js": "javascript", ".jsx": "javascript", ".go": "go", ".rs": "rust",
    ".cs": "csharp", ".rb": "ruby", ".php": "php", ".kt": "kotlin",
    ".jsp": "java", ".xml": "xml", ".sql": "sql",
}
_BUILD_MARKERS = {
    "pom.xml": ("java", "maven"),
    "build.gradle": ("java", "gradle"),
    "build.gradle.kts": ("java", "gradle"),
    "package.json": ("javascript", "npm"),
    "requirements.txt": ("python", "pip"),
    "pyproject.toml": ("python", "poetry_or_pip"),
    "setup.py": ("python", "setuptools"),
    "go.mod": ("go", "go_modules"),
    "Cargo.toml": ("rust", "cargo"),
    "Gemfile": ("ruby", "bundler"),
}
_SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build", ".zect"}


@dataclass
class RepoArchitecture:
    primary_language: str
    build_system: str
    extension_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def detect_repo_architecture(repo_root: str | Path, *, max_files: int = 4000) -> RepoArchitecture:
    """Deterministic, filesystem-only detection -- no LLM guess. A CMS/Java
    repo must be recognized as Java *before* any new file is proposed, so a
    later validation step can reject an arbitrary .py target (finding C1's
    root cause: nothing checked language consistency at all)."""
    root = Path(repo_root)
    if not root.is_dir():
        return RepoArchitecture(primary_language="unknown", build_system="unknown")
    for marker, (lang, build) in _BUILD_MARKERS.items():
        if (root / marker).is_file():
            return RepoArchitecture(primary_language=lang, build_system=build, extension_counts={})
    counts: dict[str, int] = {}
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            ext = Path(name).suffix.lower()
            if ext in _EXT_LANGUAGE:
                counts[ext] = counts.get(ext, 0) + 1
            scanned += 1
            if scanned >= max_files:
                break
        if scanned >= max_files:
            break
    if not counts:
        return RepoArchitecture(primary_language="unknown", build_system="unknown", extension_counts={})
    top_ext = max(counts, key=lambda e: counts[e])
    return RepoArchitecture(primary_language=_EXT_LANGUAGE[top_ext], build_system="unknown", extension_counts=counts)


@dataclass
class FileImpact:
    path: str
    action: str
    language: str
    requirement_ids: list[str] = field(default_factory=list)
    rationale: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    verification: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "FileImpact":
        return FileImpact(
            path=str(d.get("path") or ""),
            action=str(d.get("action") or ""),
            language=str(d.get("language") or ""),
            requirement_ids=list(d.get("requirement_ids") or []),
            rationale=str(d.get("rationale") or ""),
            evidence_refs=list(d.get("evidence_refs") or []),
            dependencies=list(d.get("dependencies") or []),
            verification=str(d.get("verification") or ""),
        )


# Companion to the CMS regression: ASK's ledger marks
# CampaignManagement.java / POST /campaigns/initiate NOT_FOUND, and PLAN's
# free-text narrative must not describe them as already existing. Shared by
# developer_service.py::plan() (which prepends a warning banner for this at
# generation time) and plan_validator.py (which hard-blocks approval for
# the exact same condition, re-checked against whatever text is actually
# about to be approved) -- one implementation, not two that could drift.
_NEW_FILE_QUALIFIERS = ("create_new", "new file", "proposed", "does not exist", "to be created", "not found")


def find_not_found_leaks(plan_text: str, not_found_entities: set[str]) -> set[str]:
    """Flags an entity if ANY of its mentions in the text lack a nearby
    qualifier -- checking only the first occurrence would let a single
    qualified mention (e.g. a warning banner that itself names the entity
    with "...unless explicitly justified as CREATE_NEW: X") mask a later,
    genuinely unqualified claim elsewhere in the same text that a
    first-occurrence-only check would never even look at."""
    text_lower = (plan_text or "").lower()
    leaked: set[str] = set()
    for entity in not_found_entities:
        needle = entity.lower()
        if not needle:
            continue
        start = 0
        while True:
            idx = text_lower.find(needle, start)
            if idx == -1:
                break
            window = text_lower[max(0, idx - 60) : idx + len(needle) + 60]
            if not any(q in window for q in _NEW_FILE_QUALIFIERS):
                leaked.add(entity)
                break
            start = idx + len(needle)
    return leaked


def find_placeholder_violations(text: str) -> list[str]:
    """Every literal placeholder pattern found in `text` -- used to reject
    a candidate plan outright rather than let one through with a warning,
    since (unlike a prose hallucination) a placeholder path has no
    legitimate reading at all."""
    found: list[str] = []
    for pattern in _PLACEHOLDER_PATTERNS:
        for m in pattern.finditer(text):
            found.append(m.group(0))
    return found


def seed_file_impacts_from_ledger(pkg: ContextPackage, *, requirement_ids: list[str] | None = None) -> list[FileImpact]:
    """The only auto-included impacts: VERIFIED file entities from ASK's
    Evidence Ledger, as MODIFY_EXISTING candidates. NOT_FOUND entities are
    deliberately never seeded here -- they can only enter the plan through
    an explicit, separately-justified CREATE_NEW proposal (finding B1/C1)."""
    req_ids = requirement_ids or []
    impacts: list[FileImpact] = []
    for entry in pkg.evidence_ledger:
        if entry.status == STATUS_VERIFIED and entry.entity_type == "file":
            impacts.append(
                FileImpact(
                    path=entry.entity,
                    action=ACTION_MODIFY_EXISTING,
                    language=_language_for_path(entry.entity),
                    requirement_ids=req_ids,
                    rationale=f"Verified to exist in the repository (evidence: {', '.join(entry.evidence_refs[:2]) or 'n/a'}); relevant to the requirement.",
                    evidence_refs=list(entry.evidence_refs),
                    dependencies=[],
                    verification="Run the existing test suite covering this file after the change.",
                )
            )
    return impacts


def _language_for_path(path: str) -> str:
    return _EXT_LANGUAGE.get(Path(path).suffix.lower(), "unknown")


def validate_file_impacts(
    impacts: list[FileImpact],
    *,
    context_package: ContextPackage,
    repo_root: str | Path,
    architecture: RepoArchitecture,
) -> tuple[list[FileImpact], list[str]]:
    """Deterministic gate -- the model's own claims (via
    llm_phase.run_grounded_plan's proposed impacts) are never trusted
    without this. Returns (accepted, rejected_reasons)."""
    root = Path(repo_root)
    not_found = context_package.not_found_entities()
    accepted: list[FileImpact] = []
    rejected: list[str] = []
    seen_paths: set[str] = set()
    for impact in impacts:
        # Deliberately NOT lstrip("/")-ing a leading slash here: that would
        # silently rewrite an attempted absolute-path escape (e.g.
        # "/etc/passwd") into a harmless-looking relative one instead of
        # rejecting it (CP-06 finding) -- path_escapes_root() below is what
        # must catch this, not silent normalization.
        path = (impact.path or "").strip().replace("\\", "/")
        reason = _reject_reason(impact, path, root, not_found, architecture)
        if reason:
            rejected.append(f"{impact.path or '(empty path)'}: {reason}")
            continue
        if path in seen_paths:
            rejected.append(f"{path}: duplicate path in the same plan")
            continue
        seen_paths.add(path)
        impact.path = path
        accepted.append(impact)
    return accepted, rejected


def path_escapes_root(path: str, root: str | Path) -> bool:
    """True if `path` (already relativized) would resolve outside `root` --
    a literal '..' segment, an absolute path, or (belt-and-suspenders) a
    resolved path that lands outside root on disk. CP-06 (finding: no prior
    check existed at all) requires this never silently pass."""
    if not path:
        return False
    # A leading "/" is POSIX-absolute but pathlib's WindowsPath treats it as
    # merely "relative to the current drive" (is_absolute() == False) --
    # checking the raw string first closes that platform gap.
    if path.startswith("/") or path.startswith("\\"):
        return True
    if Path(path).is_absolute():
        return True
    if any(seg == ".." for seg in Path(path).parts):
        return True
    try:
        resolved_root = Path(root).resolve()
        resolved_target = (Path(root) / path).resolve()
        return resolved_root not in resolved_target.parents and resolved_target != resolved_root
    except OSError:
        return True


def _reject_reason(
    impact: FileImpact, path: str, root: Path, not_found: set[str], architecture: RepoArchitecture
) -> str | None:
    if not path:
        return "empty path"
    if impact.action not in FILE_IMPACT_ACTIONS:
        return f"unknown action {impact.action!r}"
    if path_escapes_root(path, root):
        return "path escapes the authorized repository root"
    if find_placeholder_violations(path) or find_placeholder_violations(impact.rationale or ""):
        return "unresolved placeholder content"
    if path in not_found and impact.action in _EXISTENCE_REQUIRED:
        return "NOT_FOUND in the Evidence Ledger -- cannot be MODIFY_EXISTING/DELETE_EXISTING"
    if impact.action in _EXISTENCE_REQUIRED:
        if not (root / path).is_file():
            return f"{impact.action} requires the path to exist in the primary repo right now; it does not"
    if impact.action == ACTION_CREATE_NEW:
        if not (impact.rationale or "").strip():
            return "CREATE_NEW requires an explicit rationale"
        if (root / path).exists():
            return "CREATE_NEW target already exists on disk -- use MODIFY_EXISTING instead"
        lang = _language_for_path(path)
        if (
            architecture.primary_language not in ("unknown", "")
            and lang not in ("unknown", "")
            and lang != architecture.primary_language
            and Path(path).suffix.lower() not in (".md", ".json", ".yaml", ".yml", ".sql", ".xml", ".txt")
        ):
            return (
                f"CREATE_NEW proposes a .{Path(path).suffix.lstrip('.')} ({lang}) file in a "
                f"{architecture.primary_language} repository -- language mismatch"
            )
    return None


_SECTION_ORDER = (
    "Goal",
    "Requirement mapping",
    "Current implementation",
    "Missing implementation",
    "Future/excluded scope",
    "Architecture",
    "Existing files to modify",
    "New files",
    "API impact",
    "DB/migration impact",
    "UI impact",
    "Security",
    "Tests",
    "Runtime/App Runner",
    "Browser/Playwright verification",
    "Risks",
    "Delivery",
    "Acceptance criteria",
)


_SECTION_HEADER_RE = re.compile(r"^#{1,3}\s+(.+?)\s*$", re.MULTILINE)


def parse_narrative_sections(narrative: str) -> dict[str, str]:
    """Splits the model's prose response on its own '## <Header>' lines
    into {header: body}, matched case-insensitively against the mandated
    section names so minor model formatting drift (extra '#', trailing
    punctuation) doesn't lose a whole section's content."""
    text = narrative or ""
    matches = list(_SECTION_HEADER_RE.finditer(text))
    if not matches:
        return {}
    known_lower = {s.lower(): s for s in _SECTION_ORDER}
    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        header = m.group(1).strip().rstrip(":").lower()
        canonical = known_lower.get(header)
        if not canonical:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[canonical] = text[start:end].strip()
    return sections


def render_file_impact_table(impacts: list[FileImpact]) -> str:
    if not impacts:
        return "_None._"
    lines = ["| Path | Action | Language | Requirement(s) | Rationale | Evidence | Dependencies | Verification |",
             "|---|---|---|---|---|---|---|---|"]
    for i in impacts:
        lines.append(
            "| {path} | {action} | {lang} | {reqs} | {rationale} | {evidence} | {deps} | {verification} |".format(
                path=i.path,
                action=i.action,
                lang=i.language or "unknown",
                reqs=", ".join(i.requirement_ids) or "-",
                rationale=(i.rationale or "").replace("\n", " ")[:200],
                evidence=", ".join(i.evidence_refs[:3]) or "-",
                deps=", ".join(i.dependencies) or "-",
                verification=(i.verification or "-").replace("\n", " ")[:150],
            )
        )
    return "\n".join(lines)


def render_grounded_plan_markdown(
    *,
    goal: str,
    context_package: ContextPackage | None,
    architecture: RepoArchitecture,
    accepted_impacts: list[FileImpact],
    rejected_reasons: list[str],
    narrative_sections: dict[str, str],
) -> str:
    """Assembles the mandated section order. `narrative_sections` supplies
    prose for every section except the two file-impact sections, which are
    always rendered from `accepted_impacts` -- the model's narrative can
    never override what was deterministically validated."""
    modify_impacts = [i for i in accepted_impacts if i.action in (ACTION_MODIFY_EXISTING, ACTION_DELETE_EXISTING, ACTION_REFERENCE_ONLY, ACTION_NO_CHANGE)]
    new_impacts = [i for i in accepted_impacts if i.action == ACTION_CREATE_NEW]
    sections: dict[str, str] = dict(narrative_sections)
    sections["Existing files to modify"] = render_file_impact_table(modify_impacts)
    sections["New files"] = render_file_impact_table(new_impacts)

    parts = [f"# Plan: {goal.strip()[:200]}\n"]
    if context_package:
        parts.append(
            f"_Primary repo: {context_package.primary_repo_id} @ "
            f"{(context_package.repo_sha or 'unknown')[:12]} -- "
            f"detected architecture: {architecture.primary_language}/{architecture.build_system}_\n"
        )
    if rejected_reasons:
        parts.append(
            "> ⚠️ **Rejected file-impact proposals** (placeholder, unverified, or "
            "language-mismatched -- excluded from this plan, not silently accepted):\n"
            + "\n".join(f"> - {r}" for r in rejected_reasons)
            + "\n"
        )
    for name in _SECTION_ORDER:
        body = sections.get(name, "").strip() or "_Not yet determined._"
        parts.append(f"## {name}\n\n{body}\n")
    return "\n".join(parts)
