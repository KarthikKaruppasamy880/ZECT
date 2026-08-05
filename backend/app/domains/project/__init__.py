"""Project domain routers."""

from app.domains.project import projects
from app.domains.project import analytics
from app.domains.project import export_share
from app.domains.project import token_controls
from app.domains.project import generated_outputs

__all__ = ['projects', 'analytics', 'export_share', 'token_controls', 'generated_outputs']
