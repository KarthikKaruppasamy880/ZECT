"""Thin API layer — FastAPI router registration only (no business logic)."""

from app.api.register import register_routers

__all__ = ["register_routers"]
