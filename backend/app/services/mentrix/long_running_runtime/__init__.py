"""LongRunningAgentRuntime — durable Mentrix engineering execution (not a product)."""

from app.services.mentrix.long_running_runtime.runtime import (
    STATUS_BLOCKED,
    STATUS_CANCELLED,
    STATUS_FAILED_VERIFICATION,
    STATUS_NEEDS_HUMAN,
    STATUS_PAUSED,
    STATUS_READY_TO_SHIP,
    STATUS_RUNNING,
    LongRunningAgentRuntime,
    build_synthetic_operations,
)

__all__ = [
    "LongRunningAgentRuntime",
    "build_synthetic_operations",
    "STATUS_RUNNING",
    "STATUS_PAUSED",
    "STATUS_BLOCKED",
    "STATUS_NEEDS_HUMAN",
    "STATUS_FAILED_VERIFICATION",
    "STATUS_CANCELLED",
    "STATUS_READY_TO_SHIP",
]
