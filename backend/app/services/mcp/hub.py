"""Mentrix MCP hub — live adapters + audit + rules gate."""

from __future__ import annotations

import json
import re
import time
from typing import Any

from sqlalchemy.orm import Session

from app.models import MCPServerConfig, MCPToolAudit, Rule
from app.adapters import (
    confluence,
    datadog,
    email_adapter,
    filesystem,
    github,
    jira,
    playwright_adapter,
    slack,
)

ADAPTERS = {
    "github": github,
    "jira": jira,
    "confluence": confluence,
    "slack": slack,
    "datadog": datadog,
    "filesystem": filesystem,
    "email": email_adapter,
    "playwright": playwright_adapter,
}


def _rules_block(db: Session, server_id: str, tool_name: str, arguments: dict) -> str | None:
    rules = (
        db.query(Rule)
        .filter(Rule.is_active == True, Rule.rule_type.in_(["review", "security", "deploy"]))  # noqa: E712
        .all()
    )
    blob = json.dumps({"server": server_id, "tool": tool_name, **arguments})
    for rule in rules:
        if rule.action != "block":
            continue
        try:
            if re.search(rule.condition or "", blob, re.IGNORECASE):
                return f"Blocked by rule '{rule.name}'"
        except re.error:
            continue
    return None


def upsert_server_config(
    db: Session,
    *,
    server_id: str,
    name: str,
    enabled: bool = False,
    base_url: str = "",
    config: dict | None = None,
) -> MCPServerConfig:
    row = db.query(MCPServerConfig).filter(MCPServerConfig.server_id == server_id).first()
    if not row:
        row = MCPServerConfig(server_id=server_id, name=name)
        db.add(row)
    row.name = name
    row.enabled = enabled
    row.base_url = base_url
    row.config_json = json.dumps(config or {})
    row.last_health = "configured" if enabled else "disabled"
    db.commit()
    db.refresh(row)
    return row


def list_server_configs(db: Session) -> list[dict[str, Any]]:
    rows = db.query(MCPServerConfig).all()
    return [
        {
            "server_id": r.server_id,
            "name": r.name,
            "enabled": r.enabled,
            "base_url": r.base_url,
            "last_health": r.last_health,
            "config": json.loads(r.config_json or "{}"),
        }
        for r in rows
    ]


def execute_tool(
    db: Session,
    *,
    server_id: str,
    tool_name: str,
    arguments: dict,
    user_email: str = "",
) -> dict[str, Any]:
    start = time.time()
    block = _rules_block(db, server_id, tool_name, arguments)
    if block:
        audit = MCPToolAudit(
            server_id=server_id,
            tool_name=tool_name,
            arguments_json=json.dumps(arguments),
            result_json=json.dumps({"error": block}),
            status="blocked",
            user_email=user_email,
        )
        db.add(audit)
        db.commit()
        return {
            "server_id": server_id,
            "tool_name": tool_name,
            "status": "blocked",
            "result": {"error": block},
            "execution_time_ms": 0,
        }

    cfg = db.query(MCPServerConfig).filter(MCPServerConfig.server_id == server_id).first()
    adapter = ADAPTERS.get(server_id)
    if not adapter:
        raise ValueError(f"No adapter for server '{server_id}'")

    config = json.loads(cfg.config_json) if cfg and cfg.config_json else {}
    if cfg and cfg.base_url:
        config.setdefault("base_url", cfg.base_url)
    enabled = cfg.enabled if cfg else True

    try:
        result = adapter.execute(tool_name, arguments, config=config, enabled=enabled)
        status = "success"
    except Exception as exc:  # noqa: BLE001
        result = {"error": str(exc)}
        status = "error"

    ms = (time.time() - start) * 1000
    audit = MCPToolAudit(
        server_id=server_id,
        tool_name=tool_name,
        arguments_json=json.dumps(arguments),
        result_json=json.dumps(result)[:20000],
        status=status,
        user_email=user_email,
    )
    db.add(audit)
    if cfg:
        cfg.last_health = status
    db.commit()
    return {
        "server_id": server_id,
        "tool_name": tool_name,
        "status": status,
        "result": result,
        "execution_time_ms": round(ms, 2),
    }
