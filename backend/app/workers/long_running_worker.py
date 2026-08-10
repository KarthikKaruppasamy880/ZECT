"""Background worker for LongRunningAgentRuntime — open own DB session (like mentrix_worker)."""

from __future__ import annotations

import logging

from app.infrastructure.database import SessionLocal
from app.services.mentrix.long_running_runtime.runtime import LongRunningAgentRuntime

logger = logging.getLogger(__name__)


def run_long_running_batch_in_background(
    run_id: str,
    *,
    worker_id: str,
    max_ops: int = 25,
) -> None:
    """Claim lease and process a batch of operations outside the HTTP request."""
    db = SessionLocal()
    try:
        rt = LongRunningAgentRuntime(db)
        rt.tick(run_id, worker_id=worker_id, max_ops=max_ops)
    except Exception as exc:  # noqa: BLE001
        logger.exception("long_running_batch_failed run_id=%s worker_id=%s", run_id, worker_id)
        try:
            db.rollback()
            row = LongRunningAgentRuntime(db).get(run_id)
            row.status = "NEEDS_HUMAN_DECISION"
            row.error_message = str(exc)[:500]
            db.commit()
        except Exception:
            logger.exception("long_running_failure_persist_failed run_id=%s", run_id)
            db.rollback()
    finally:
        db.close()
