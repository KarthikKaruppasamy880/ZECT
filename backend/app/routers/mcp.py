"""MCP (Model Context Protocol) support router for ZECT.

Provides endpoints for:
- Listing available MCP servers/tools
- Executing MCP tool calls
- Managing MCP server connections
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth.deps import CurrentUser, get_current_user
from app.database import get_db

router = APIRouter(prefix="/api/mcp", tags=["MCP"])


class MCPServer(BaseModel):
    id: str
    name: str
    description: str
    status: str = "available"
    tools_count: int = 0
    url: Optional[str] = None


class MCPTool(BaseModel):
    name: str
    description: str
    server_id: str
    parameters: dict = {}


class MCPToolCall(BaseModel):
    server_id: str
    tool_name: str
    arguments: dict = {}


class MCPToolResult(BaseModel):
    server_id: str
    tool_name: str
    result: dict
    execution_time_ms: float
    timestamp: str


# Built-in MCP servers that ZECT supports
BUILTIN_SERVERS: list[MCPServer] = [
    MCPServer(
        id="github",
        name="GitHub",
        description="GitHub repository operations — PRs, issues, commits, code search",
        status="available",
        tools_count=12,
    ),
    MCPServer(
        id="jira",
        name="Jira",
        description="Jira project management — create/update issues, search, sprint management",
        status="available",
        tools_count=8,
    ),
    MCPServer(
        id="slack",
        name="Slack",
        description="Slack messaging — send messages, create channels, manage notifications",
        status="available",
        tools_count=6,
    ),
    MCPServer(
        id="filesystem",
        name="Filesystem",
        description="Local filesystem operations — read, write, search files",
        status="available",
        tools_count=5,
    ),
    MCPServer(
        id="confluence",
        name="Confluence",
        description="Confluence pages — search and read for Mentrix Scout/Integrator",
        status="available",
        tools_count=4,
    ),
    MCPServer(
        id="datadog",
        name="Datadog",
        description="Datadog metrics and monitors for Mentrix Ops",
        status="available",
        tools_count=4,
    ),
    MCPServer(
        id="email",
        name="Email",
        description="SMTP outbound email for Mentrix Integrator (Wave 1; inbox poll is Wave 2)",
        status="available",
        tools_count=2,
    ),
]

# Tools for each server
BUILTIN_TOOLS: dict[str, list[MCPTool]] = {
    "github": [
        MCPTool(name="list_repos", description="List repositories for the authenticated user", server_id="github"),
        MCPTool(name="get_repo", description="Get repository details", server_id="github", parameters={"owner": "string", "repo": "string"}),
        MCPTool(name="list_prs", description="List pull requests", server_id="github", parameters={"owner": "string", "repo": "string", "state": "string"}),
        MCPTool(name="create_pr", description="Create a pull request", server_id="github", parameters={"owner": "string", "repo": "string", "title": "string", "body": "string", "head": "string", "base": "string"}),
        MCPTool(name="list_issues", description="List issues", server_id="github", parameters={"owner": "string", "repo": "string"}),
        MCPTool(name="create_issue", description="Create an issue", server_id="github", parameters={"owner": "string", "repo": "string", "title": "string", "body": "string"}),
        MCPTool(name="get_file", description="Get file contents from a repo", server_id="github", parameters={"owner": "string", "repo": "string", "path": "string"}),
        MCPTool(name="search_code", description="Search code across repositories", server_id="github", parameters={"query": "string"}),
        MCPTool(name="list_commits", description="List recent commits", server_id="github", parameters={"owner": "string", "repo": "string"}),
        MCPTool(name="get_diff", description="Get diff for a PR or commit", server_id="github", parameters={"owner": "string", "repo": "string", "ref": "string"}),
        MCPTool(name="list_branches", description="List branches", server_id="github", parameters={"owner": "string", "repo": "string"}),
        MCPTool(name="create_branch", description="Create a new branch", server_id="github", parameters={"owner": "string", "repo": "string", "branch": "string", "from_branch": "string"}),
    ],
    "jira": [
        MCPTool(name="list_projects", description="List Jira projects", server_id="jira"),
        MCPTool(name="create_issue", description="Create a Jira issue", server_id="jira", parameters={"project": "string", "summary": "string", "type": "string"}),
        MCPTool(name="update_issue", description="Update a Jira issue", server_id="jira", parameters={"issue_key": "string", "fields": "object"}),
        MCPTool(name="search_issues", description="Search issues with JQL", server_id="jira", parameters={"jql": "string"}),
        MCPTool(name="get_issue", description="Get issue details", server_id="jira", parameters={"issue_key": "string"}),
        MCPTool(name="add_comment", description="Add comment to an issue", server_id="jira", parameters={"issue_key": "string", "body": "string"}),
        MCPTool(name="list_sprints", description="List sprints for a board", server_id="jira", parameters={"board_id": "string"}),
        MCPTool(name="transition_issue", description="Transition issue status", server_id="jira", parameters={"issue_key": "string", "transition_id": "string"}),
    ],
    "slack": [
        MCPTool(name="send_message", description="Send a message to a channel", server_id="slack", parameters={"channel": "string", "text": "string"}),
        MCPTool(name="list_channels", description="List Slack channels", server_id="slack"),
        MCPTool(name="create_channel", description="Create a Slack channel", server_id="slack", parameters={"name": "string"}),
        MCPTool(name="upload_file", description="Upload a file to a channel", server_id="slack", parameters={"channel": "string", "file_path": "string"}),
        MCPTool(name="list_users", description="List workspace users", server_id="slack"),
        MCPTool(name="send_dm", description="Send a direct message", server_id="slack", parameters={"user_id": "string", "text": "string"}),
    ],
    "filesystem": [
        MCPTool(name="read_file", description="Read file contents", server_id="filesystem", parameters={"path": "string"}),
        MCPTool(name="write_file", description="Write content to a file", server_id="filesystem", parameters={"path": "string", "content": "string"}),
        MCPTool(name="list_directory", description="List directory contents", server_id="filesystem", parameters={"path": "string"}),
        MCPTool(name="search_files", description="Search for files by pattern", server_id="filesystem", parameters={"pattern": "string", "path": "string"}),
        MCPTool(name="file_info", description="Get file metadata", server_id="filesystem", parameters={"path": "string"}),
    ],
    "email": [
        MCPTool(name="send_email", description="Send email via SMTP", server_id="email", parameters={"to": "string", "subject": "string", "body": "string"}),
        MCPTool(name="status", description="SMTP configuration status", server_id="email"),
    ],
    "datadog": [
        MCPTool(name="query_logs", description="Query Datadog logs", server_id="datadog", parameters={"query": "string"}),
        MCPTool(name="query_metrics", description="Query Datadog metrics", server_id="datadog", parameters={"query": "string"}),
    ],
    "confluence": [
        MCPTool(name="search", description="Search Confluence", server_id="confluence", parameters={"query": "string"}),
        MCPTool(name="get_page", description="Get Confluence page", server_id="confluence", parameters={"page_id": "string"}),
    ],
    "postgres": [
        MCPTool(name="query", description="Execute a SQL query", server_id="postgres", parameters={"sql": "string"}),
        MCPTool(name="list_tables", description="List all tables in the database", server_id="postgres"),
        MCPTool(name="describe_table", description="Get table schema", server_id="postgres", parameters={"table": "string"}),
        MCPTool(name="list_indexes", description="List indexes on a table", server_id="postgres", parameters={"table": "string"}),
        MCPTool(name="run_migration", description="Run a database migration", server_id="postgres", parameters={"migration_file": "string"}),
        MCPTool(name="export_data", description="Export table data as CSV", server_id="postgres", parameters={"table": "string", "format": "string"}),
        MCPTool(name="connection_info", description="Get database connection details", server_id="postgres"),
    ],
    # Browser E2E is via frontend Playwright Test / Cursor Playwright MCP — not Mentrix hub adapters.
}


@router.get("/servers")
async def list_servers():
    """List all available MCP servers."""
    return {"servers": [s.model_dump() for s in BUILTIN_SERVERS], "total": len(BUILTIN_SERVERS)}


@router.get("/servers/{server_id}")
async def get_server(server_id: str):
    """Get details of a specific MCP server."""
    server = next((s for s in BUILTIN_SERVERS if s.id == server_id), None)
    if not server:
        raise HTTPException(status_code=404, detail=f"MCP server '{server_id}' not found")
    return server.model_dump()


@router.get("/servers/{server_id}/tools")
async def list_tools(server_id: str):
    """List all tools available on an MCP server."""
    if server_id not in BUILTIN_TOOLS:
        raise HTTPException(status_code=404, detail=f"MCP server '{server_id}' not found")
    tools = BUILTIN_TOOLS[server_id]
    return {"tools": [t.model_dump() for t in tools], "total": len(tools)}


@router.post("/servers/{server_id}/tools/{tool_name}/call")
def call_tool(
    server_id: str,
    tool_name: str,
    body: MCPToolCall,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Execute a Mentrix MCP tool via live adapters (rules-gated + audited)."""
    from app.services.mcp.hub import execute_tool

    if server_id not in BUILTIN_TOOLS and server_id not in {
        "github", "jira", "confluence", "slack", "datadog", "filesystem", "email",
    }:
        raise HTTPException(status_code=404, detail=f"MCP server '{server_id}' not found")

    try:
        out = execute_tool(
            db,
            server_id=server_id,
            tool_name=tool_name,
            arguments=body.arguments or {},
            user_email=user.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return MCPToolResult(
        server_id=server_id,
        tool_name=tool_name,
        result=out.get("result") or {},
        execution_time_ms=float(out.get("execution_time_ms") or 0),
        timestamp=datetime.utcnow().isoformat(),
    ).model_dump() | {"status": out.get("status")}


class MCPConfigBody(BaseModel):
    server_id: str
    name: str
    enabled: bool = False
    base_url: str = ""
    config: dict = {}


@router.get("/configs")
def get_configs(db: Session = Depends(get_db), _user: CurrentUser = Depends(get_current_user)):
    from app.services.mcp.hub import list_server_configs
    return {"configs": list_server_configs(db)}


@router.post("/configs")
def save_config(
    body: MCPConfigBody,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    from app.services.mcp.hub import upsert_server_config
    row = upsert_server_config(
        db,
        server_id=body.server_id,
        name=body.name,
        enabled=body.enabled,
        base_url=body.base_url,
        config=body.config,
    )
    return {"server_id": row.server_id, "enabled": row.enabled, "last_health": row.last_health}


@router.post("/execute")
def execute(
    body: MCPToolCall,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    from app.services.mcp.hub import execute_tool
    try:
        return execute_tool(
            db,
            server_id=body.server_id,
            tool_name=body.tool_name,
            arguments=body.arguments or {},
            user_email=user.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/status")
async def mcp_status():
    """Get overall MCP subsystem status."""
    return {
        "status": "operational",
        "servers_available": len(BUILTIN_SERVERS),
        "total_tools": sum(len(tools) for tools in BUILTIN_TOOLS.values()),
        "version": "2.0.0-mentrix",
        "live_adapters": ["github", "jira", "confluence", "slack", "datadog", "filesystem", "email"],
        "outbound_wave1": ["slack.send_message", "email.send_email", "datadog.query_logs"],
        "wave2": ["slack_events_inbound", "email_inbox_poll"],
    }
