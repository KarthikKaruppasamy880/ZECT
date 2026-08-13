"""Learning Expansion services package (extends Phase 9 Learning — no parallel system)."""

from app.services.learning.curriculum import get_lesson, get_path, list_path_summaries

__all__ = ["list_path_summaries", "get_path", "get_lesson"]
