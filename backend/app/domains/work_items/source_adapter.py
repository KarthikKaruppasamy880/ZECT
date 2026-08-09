"""WorkItemSourceAdapter — contract for future Jira/Camunda/GitHub ingest (stubs in P0)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class WorkItemSourceAdapter(Protocol):
    """Ingest external tickets/tasks into WorkItem create payloads."""

    source_name: str

    def fetch_raw(self, external_id: str) -> dict[str, Any]:
        """Fetch raw payload from external system."""
        ...

    def to_work_item_fields(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Map external payload → WorkItem create fields."""
        ...


class UserSourceAdapter:
    """Passthrough adapter for manually created work items."""

    source_name = "user"

    def fetch_raw(self, external_id: str) -> dict[str, Any]:
        return {"external_id": external_id, "source": "user"}

    def to_work_item_fields(self, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "source": "user",
            "external_id": str(raw.get("external_id") or ""),
            "title": str(raw.get("title") or "Untitled"),
            "description": str(raw.get("description") or ""),
        }


class _NotImplementedSourceAdapter:
    """Stub for P1 sources — contract only."""

    source_name: str = "stub"

    def __init__(self, source_name: str) -> None:
        self.source_name = source_name

    def fetch_raw(self, external_id: str) -> dict[str, Any]:
        raise NotImplementedError(
            f"WorkItemSourceAdapter[{self.source_name}] full ingest is P1; external_id={external_id}"
        )

    def to_work_item_fields(self, raw: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(
            f"WorkItemSourceAdapter[{self.source_name}] full ingest is P1"
        )


def get_source_adapter(source: str) -> WorkItemSourceAdapter:
    name = (source or "user").strip().lower() or "user"
    if name == "user":
        return UserSourceAdapter()
    if name in ("jira", "camunda", "github"):
        return _NotImplementedSourceAdapter(name)  # type: ignore[return-value]
    return _NotImplementedSourceAdapter(name)  # type: ignore[return-value]
