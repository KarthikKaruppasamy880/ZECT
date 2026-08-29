"""Project domain routers."""

from app.domains.project import (
    analytics,
    export_share,
    generated_outputs,
    projects,
    settings,
    token_controls,
)

__all__ = [
    "projects",
    "analytics",
    "export_share",
    "token_controls",
    "generated_outputs",
    "settings",
]
