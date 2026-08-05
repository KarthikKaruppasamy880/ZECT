"""Audit domain — trail API and log_audit helper."""

from app.domains.audit.audit_trail import log_audit, router

__all__ = ["log_audit", "router"]
