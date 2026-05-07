"""Secrets Management — encrypted credential storage."""

import base64
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SecretEntry

router = APIRouter(prefix="/api/secrets", tags=["secrets"])

# Simple encryption using base64 + XOR with a key derived from env
# In production, use Fernet from cryptography package
_ENCRYPT_KEY = os.getenv("ZECT_ENCRYPT_KEY", "zect-default-encrypt-key-change-me")


def _encrypt(value: str) -> str:
    """Simple reversible encryption for secrets."""
    key_bytes = _ENCRYPT_KEY.encode()
    val_bytes = value.encode()
    encrypted = bytes(v ^ key_bytes[i % len(key_bytes)] for i, v in enumerate(val_bytes))
    return base64.b64encode(encrypted).decode()


def _decrypt(encrypted: str) -> str:
    """Decrypt a previously encrypted value."""
    key_bytes = _ENCRYPT_KEY.encode()
    val_bytes = base64.b64decode(encrypted.encode())
    decrypted = bytes(v ^ key_bytes[i % len(key_bytes)] for i, v in enumerate(val_bytes))
    return decrypted.decode()


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


@router.get("")
def list_secrets(
    scope: Optional[str] = None,
    project_id: Optional[int] = None,
    secret_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List secrets (values are masked)."""
    try:
        q = db.query(SecretEntry).filter(SecretEntry.is_active == True)
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
def create_secret(data: SecretCreate, db: Session = Depends(get_db)):
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
        entry = SecretEntry(
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


@router.get("/{secret_id}")
def get_secret(secret_id: int, reveal: bool = False, db: Session = Depends(get_db)):
    """Get a secret (optionally reveal value)."""
    try:
        entry = db.query(SecretEntry).filter(SecretEntry.id == secret_id).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Secret not found")
        return _to_dict(entry, mask=not reveal)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{secret_id}")
def update_secret(secret_id: int, data: SecretUpdate, db: Session = Depends(get_db)):
    """Update a secret."""
    try:
        entry = db.query(SecretEntry).filter(SecretEntry.id == secret_id).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Secret not found")
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
def delete_secret(secret_id: int, db: Session = Depends(get_db)):
    """Delete a secret."""
    try:
        entry = db.query(SecretEntry).filter(SecretEntry.id == secret_id).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Secret not found")
        db.delete(entry)
        db.commit()
        return {"status": "deleted", "id": secret_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{secret_id}/rotate")
def rotate_secret(secret_id: int, new_value: str, db: Session = Depends(get_db)):
    """Rotate a secret's value."""
    try:
        entry = db.query(SecretEntry).filter(SecretEntry.id == secret_id).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Secret not found")
        entry.encrypted_value = _encrypt(new_value)
        entry.last_rotated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(entry)
        return _to_dict(entry, mask=True)
    except HTTPException:
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
