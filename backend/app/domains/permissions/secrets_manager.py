"""Secrets Management — encrypted credential storage using Fernet."""

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet, InvalidToken

from app.infrastructure.database import get_db
from app.models import SecretEntry, User
from app.security.vault import vault
from app.infrastructure.auth.deps import get_current_user, CurrentUser
from app.infrastructure.auth.rbac import (
    require_role,
    log_audit,
    can_user_access_resource,
    get_user_from_current_user,
    PermissionDenied,
)

router = APIRouter(prefix="/api/secrets", tags=["secrets"])

# Initialize Fernet cipher with secure key from vault
_cipher = Fernet(vault.get_key())


def _encrypt(value: str) -> str:
    """Encrypt a value using Fernet (AES-128)."""
    try:
        encrypted_bytes = _cipher.encrypt(value.encode())
        return encrypted_bytes.decode()
    except Exception as e:
        raise RuntimeError(f"Encryption failed: {e}")


def _decrypt(encrypted_value: str) -> str:
    """Decrypt a previously encrypted value using Fernet."""
    try:
        decrypted_bytes = _cipher.decrypt(encrypted_value.encode())
        return decrypted_bytes.decode()
    except InvalidToken:
        raise ValueError("Decryption failed: Invalid token. Data may be corrupted or encrypted with different key.")
    except Exception as e:
        raise RuntimeError(f"Decryption failed: {e}")


class SecretCreate(BaseModel):
    name: str
    value: str
    description: str = ""
    secret_type: str = "api_key"
    scope: str = "project"
    project_id: Optional[int] = None
    expires_at: Optional[str] = None

class SecretUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SecretRotate(BaseModel):
    new_value: str


def _require_secret_access(entry: SecretEntry, current_user: CurrentUser, db: Session) -> None:
    """Admin, the secret's own creator, or resource-level (team/project) access
    — anything short of that gets a 403, not silent success."""
    user = get_user_from_current_user(current_user, db)
    if user.role == "admin":
        return
    if entry.user_id is not None and entry.user_id == user.id:
        return
    if can_user_access_resource(user, "secret", entry.id, db):
        return
    raise PermissionDenied("You don't have permission to access this secret")


@router.get("")
def list_secrets(
    scope: Optional[str] = None,
    project_id: Optional[int] = None,
    secret_type: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),  # ✅ RBAC: Authentication required
    db: Session = Depends(get_db),
):
    """List secrets (values are masked). Authentication required."""
    try:
        # ✅ Filter secrets based on user's role and team
        user = get_user_from_current_user(current_user, db)
        q = db.query(SecretEntry).filter(SecretEntry.is_active == True)

        # Admin can see all secrets, others see only their team's secrets
        if user.role != "admin":
            # For non-admins, filter by team
            if user.team:
                q = q.filter(SecretEntry.project.has(project__team=user.team))
            else:
                # If user has no team, they see no secrets
                q = q.filter(False)

        if scope:
            q = q.filter(SecretEntry.scope == scope)
        if project_id:
            q = q.filter(SecretEntry.project_id == project_id)
        if secret_type:
            q = q.filter(SecretEntry.secret_type == secret_type)

        items = q.order_by(SecretEntry.name).all()
        return [_to_dict(s, mask=True) for s in items]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_secret(
    data: SecretCreate,
    current_user: CurrentUser = Depends(get_current_user),  # RBAC: authentication required
    db: Session = Depends(get_db),
):
    """Create a new encrypted secret."""
    try:
        # Check for duplicate name in same scope
        existing = db.query(SecretEntry).filter(
            SecretEntry.name == data.name,
            SecretEntry.scope == data.scope,
            SecretEntry.is_active == True,
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Secret '{data.name}' already exists in scope '{data.scope}'")

        encrypted = _encrypt(data.value)
        user = get_user_from_current_user(current_user, db)
        entry = SecretEntry(
            user_id=user.id,
            name=data.name,
            encrypted_value=encrypted,
            description=data.description,
            secret_type=data.secret_type,
            scope=data.scope,
            project_id=data.project_id,
        )
        if data.expires_at:
            try:
                entry.expires_at = datetime.fromisoformat(data.expires_at)
            except ValueError:
                pass
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return _to_dict(entry, mask=True)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resolve")
def resolve_secret_by_name(
    name: str,
    scope: Optional[str] = None,
    project_id: Optional[int] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resolve secret by name → reference only (no plaintext)."""
    q = db.query(SecretEntry).filter(SecretEntry.name == name, SecretEntry.is_active == True)
    if scope:
        q = q.filter(SecretEntry.scope == scope)
    if project_id is not None:
        q = q.filter(SecretEntry.project_id == project_id)
    entry = q.order_by(SecretEntry.id.desc()).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Secret not found")
    _require_secret_access(entry, current_user, db)
    return {
        "ref": f"zect-secret://{entry.id}",
        "id": entry.id,
        "name": entry.name,
        "secret_type": entry.secret_type,
        "scope": entry.scope,
        "project_id": entry.project_id,
        "is_active": entry.is_active,
        "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
        "value": None,
        "revealed": False,
    }


@router.get("/{secret_id}/resolve")
def resolve_secret_reference(
    secret_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Phase 5 Stage C — return a secret *reference* only (never plaintext).

    Agents and tools should use this path (`secret:use_reference`) instead of
    `?reveal=true`.
    """
    entry = db.query(SecretEntry).filter(SecretEntry.id == secret_id, SecretEntry.is_active == True).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Secret not found")
    _require_secret_access(entry, current_user, db)
    return {
        "ref": f"zect-secret://{entry.id}",
        "id": entry.id,
        "name": entry.name,
        "secret_type": entry.secret_type,
        "scope": entry.scope,
        "project_id": entry.project_id,
        "is_active": entry.is_active,
        "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
        "value": None,
        "revealed": False,
    }


@router.get("/{secret_id}")
def get_secret(
    secret_id: int,
    reveal: bool = False,
    current_user: CurrentUser = Depends(get_current_user),  # RBAC: authentication required
    db: Session = Depends(get_db),
):
    """Get a secret. Revealing the plaintext value requires admin, ownership, or resource access.

    Prefer GET /{id}/resolve for agent/tool use — plaintext reveal is human-gated.
    """
    try:
        entry = db.query(SecretEntry).filter(SecretEntry.id == secret_id).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Secret not found")
        if reveal:
            _require_secret_access(entry, current_user, db)
        return _to_dict(entry, mask=not reveal)
    except (HTTPException, PermissionDenied):
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{secret_id}")
def update_secret(
    secret_id: int,
    data: SecretUpdate,
    current_user: CurrentUser = Depends(get_current_user),  # RBAC: authentication required
    db: Session = Depends(get_db),
):
    """Update a secret. Requires admin, ownership, or resource access."""
    try:
        entry = db.query(SecretEntry).filter(SecretEntry.id == secret_id).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Secret not found")
        _require_secret_access(entry, current_user, db)
        if data.value is not None:
            entry.encrypted_value = _encrypt(data.value)
            entry.last_rotated_at = datetime.now(timezone.utc)
        if data.description is not None:
            entry.description = data.description
        if data.is_active is not None:
            entry.is_active = data.is_active
        db.commit()
        db.refresh(entry)
        return _to_dict(entry, mask=True)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{secret_id}")
@require_role("admin")  # ✅ RBAC: Only admins can delete secrets
def delete_secret(
    secret_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a secret (admin only)."""
    try:
        entry = db.query(SecretEntry).filter(SecretEntry.id == secret_id).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Secret not found")

        # ✅ Extra check: Admin can delete, or user owns the secret's project
        user = get_user_from_current_user(current_user, db)
        if user.role != "admin" and not can_user_access_resource(user, "secret", secret_id, db):
            raise PermissionDenied("You don't have permission to delete this secret")

        db.delete(entry)
        db.commit()

        # ✅ Log to audit trail
        log_audit(
            db=db,
            user_id=current_user.user_id,
            action="delete_secret",
            resource_id=secret_id,
            resource_type="secret",
            details={"name": entry.name}
        )

        return {"status": "deleted", "id": secret_id}
    except (HTTPException, PermissionDenied):
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{secret_id}/rotate")
def rotate_secret(
    secret_id: int,
    data: SecretRotate,
    current_user: CurrentUser = Depends(get_current_user),  # RBAC: authentication required
    db: Session = Depends(get_db),
):
    """Rotate a secret's value. Requires admin, ownership, or resource access.

    new_value travels in the request body, not a query string — a query
    param would land the new secret value in server/proxy access logs.
    """
    try:
        entry = db.query(SecretEntry).filter(SecretEntry.id == secret_id).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Secret not found")
        _require_secret_access(entry, current_user, db)
        entry.encrypted_value = _encrypt(data.new_value)
        entry.last_rotated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(entry)
        return _to_dict(entry, mask=True)
    except (HTTPException, PermissionDenied):
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def _to_dict(s: SecretEntry, mask: bool = True) -> dict:
    value_display = "••••••••"
    if not mask:
        try:
            value_display = _decrypt(s.encrypted_value)
        except Exception:
            value_display = "[decryption error]"
    return {
        "id": s.id,
        "user_id": s.user_id,
        "project_id": s.project_id,
        "name": s.name,
        "description": s.description,
        "value": value_display,
        "secret_type": s.secret_type,
        "scope": s.scope,
        "is_active": s.is_active,
        "last_rotated_at": s.last_rotated_at.isoformat() if s.last_rotated_at else None,
        "expires_at": s.expires_at.isoformat() if s.expires_at else None,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }
