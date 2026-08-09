"""WorkItemSourceAdapter — user passthrough + Jira/Camunda ingest (P1)."""

from __future__ import annotations

import os
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class WorkItemSourceAdapter(Protocol):
    """Ingest external tickets/tasks into WorkItem create payloads."""

    source_name: str

    def fetch_raw(self, external_id: str) -> dict[str, Any]:
        """Fetch raw payload from external system (or fixture)."""
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
            "project_id": raw.get("project_id"),
            "repository_id": raw.get("repository_id"),
            "repository_ref": str(raw.get("repository_ref") or ""),
            "base_commit_sha": str(raw.get("base_commit_sha") or ""),
        }


class JiraSourceAdapter:
    """Jira → WorkItem. Uses live Jira when configured; accepts fixture raw otherwise."""

    source_name = "jira"

    def fetch_raw(self, external_id: str) -> dict[str, Any]:
        key = (external_id or "").strip()
        if not key:
            raise ValueError("jira_external_id_required")
        # Allow offline/fixture path for tests and fail-closed CI
        fixture = os.getenv("ZECT_JIRA_INGEST_FIXTURE_JSON", "").strip()
        if fixture:
            import json

            data = json.loads(fixture)
            if isinstance(data, dict) and data.get("key") == key:
                return data
            if isinstance(data, dict) and "fields" in data:
                return data

        from app.adapters import jira as jira_adapter

        try:
            out = jira_adapter.execute(
                "get_issue",
                {"issue_key": key},
                config={},
                enabled=True,
            )
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"jira_fetch_failed:{exc}") from exc
        if out.get("status") in ("not_configured", "disabled"):
            # Fail closed for live fetch — callers may pass raw via ingest API
            raise RuntimeError(
                f"jira_not_configured: cannot fetch {key}; pass raw payload or set JIRA_* env"
            )
        if out.get("error"):
            raise RuntimeError(f"jira_fetch_failed:{out.get('error')}")
        return out

    def to_work_item_fields(self, raw: dict[str, Any]) -> dict[str, Any]:
        fields = raw.get("fields") if isinstance(raw.get("fields"), dict) else {}
        key = str(raw.get("key") or raw.get("external_id") or "")
        summary = str(fields.get("summary") or raw.get("title") or key or "Jira issue")
        description = fields.get("description")
        if isinstance(description, dict):
            # ADF — flatten lightly
            description = str(description)[:4000]
        else:
            description = str(description or raw.get("description") or "")

        project_id = raw.get("project_id")
        repository_id = raw.get("repository_id")
        repository_ref = str(raw.get("repository_ref") or fields.get("branch") or "")
        base_commit_sha = str(raw.get("base_commit_sha") or "")

        # Optional custom fields / labels carry repo hints
        labels = fields.get("labels") if isinstance(fields.get("labels"), list) else []
        for lab in labels:
            s = str(lab)
            if s.startswith("repo:"):
                repository_ref = repository_ref or s.split(":", 1)[-1]

        return {
            "source": "jira",
            "external_id": key,
            "title": summary[:500],
            "description": description[:8000],
            "project_id": project_id,
            "repository_id": repository_id,
            "repository_ref": repository_ref,
            "base_commit_sha": base_commit_sha,
            "requirements": raw.get("requirements") or [{"id": "JIRA", "text": summary}],
            "acceptance": raw.get("acceptance") or [],
        }


class CamundaSourceAdapter:
    """Camunda / Mentrix Process task → WorkItem."""

    source_name = "camunda"

    def fetch_raw(self, external_id: str) -> dict[str, Any]:
        task_id = (external_id or "").strip()
        if not task_id:
            raise ValueError("camunda_task_id_required")
        fixture = os.getenv("ZECT_CAMUNDA_INGEST_FIXTURE_JSON", "").strip()
        if fixture:
            import json

            data = json.loads(fixture)
            if isinstance(data, dict):
                return data

        from app.adapters import camunda_client

        base = camunda_client._base_url()  # noqa: SLF001
        if not base:
            raise RuntimeError(
                f"camunda_not_configured: cannot fetch task {task_id}; pass raw payload or set ZECT_CAMUNDA_BASE_URL"
            )
        import httpx

        with httpx.Client(timeout=30.0, auth=camunda_client._auth()) as client:  # noqa: SLF001
            r = client.get(f"{base}/task/{task_id}")
            if r.status_code >= 400:
                raise RuntimeError(f"camunda_fetch_failed:http_{r.status_code}")
            task = r.json() if r.content else {}
            # variables
            vr = client.get(f"{base}/task/{task_id}/variables")
            variables = vr.json() if vr.status_code < 400 and vr.content else {}
            task["variables"] = variables
            return task

    def to_work_item_fields(self, raw: dict[str, Any]) -> dict[str, Any]:
        task_id = str(raw.get("id") or raw.get("external_id") or "")
        name = str(raw.get("name") or raw.get("title") or f"Camunda task {task_id}")
        variables = raw.get("variables") if isinstance(raw.get("variables"), dict) else {}

        def _var(key: str, default: Any = None) -> Any:
            v = variables.get(key)
            if isinstance(v, dict) and "value" in v:
                return v.get("value")
            return v if v is not None else default

        return {
            "source": "camunda",
            "external_id": task_id,
            "title": name[:500],
            "description": str(raw.get("description") or raw.get("processInstanceId") or "")[:8000],
            "project_id": raw.get("project_id") or _var("project_id"),
            "repository_id": raw.get("repository_id") or _var("repository_id"),
            "repository_ref": str(raw.get("repository_ref") or _var("repository_ref") or ""),
            "base_commit_sha": str(raw.get("base_commit_sha") or _var("base_commit_sha") or ""),
            "requirements": raw.get("requirements") or [{"id": "CAMUNDA", "text": name}],
            "acceptance": raw.get("acceptance") or [],
        }


class _NotImplementedSourceAdapter:
    source_name: str = "stub"

    def __init__(self, source_name: str) -> None:
        self.source_name = source_name

    def fetch_raw(self, external_id: str) -> dict[str, Any]:
        raise NotImplementedError(
            f"WorkItemSourceAdapter[{self.source_name}] not implemented; external_id={external_id}"
        )

    def to_work_item_fields(self, raw: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(f"WorkItemSourceAdapter[{self.source_name}] not implemented")


def get_source_adapter(source: str) -> WorkItemSourceAdapter:
    name = (source or "user").strip().lower() or "user"
    if name == "user":
        return UserSourceAdapter()
    if name == "jira":
        return JiraSourceAdapter()
    if name in ("camunda", "process", "mentrix_process"):
        return CamundaSourceAdapter()
    if name == "github":
        return _NotImplementedSourceAdapter("github")  # type: ignore[return-value]
    return _NotImplementedSourceAdapter(name)  # type: ignore[return-value]
