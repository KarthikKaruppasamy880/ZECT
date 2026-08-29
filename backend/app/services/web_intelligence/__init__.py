"""Web Intelligence package."""

from app.services.web_intelligence.service import (
    ingest_external,
    retrieve_web_context,
    serialize_artifact,
)

__all__ = ["ingest_external", "retrieve_web_context", "serialize_artifact"]
