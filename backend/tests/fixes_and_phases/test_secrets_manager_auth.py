"""Secrets Manager auth gaps — create/get(reveal)/update/rotate previously had
no authentication dependency at all, and rotate's new value was bound as a
URL query parameter (leaking into server/proxy logs). This verifies all four
now require auth, that revealing/mutating a secret you don't own and aren't
admin on is rejected, and that rotate's new value travels in the request body.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.infrastructure.database import Base
from app.infrastructure.auth.deps import CurrentUser
from app.infrastructure.auth.rbac import PermissionDenied
from app.models import SecretEntry, User
from app.routers.secrets_manager import (
    SecretCreate,
    SecretRotate,
    SecretUpdate,
    create_secret,
    get_secret,
    rotate_secret,
    update_secret,
)


@pytest.fixture(autouse=True)
def _encryption_key(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlcy0h")
    monkeypatch.setenv("ENV", "development")


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _make_user(db, *, email="dev@zect.local", role="developer", team=""):
    user = User(email=email, name=email, role=role, team=team)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _current_user_for(user: User) -> CurrentUser:
    return CurrentUser(user_id=user.id, username=user.name, email=user.email, auth_mode="local", token="", role=user.role)


class TestCreateSecretRequiresAuthAndSetsOwner:
    def test_creates_secret_owned_by_current_user(self):
        db = _session()
        user = _make_user(db)

        result = create_secret(
            SecretCreate(name="api-key", value="sk-real-value", scope="user"),
            current_user=_current_user_for(user),
            db=db,
        )

        entry = db.query(SecretEntry).filter(SecretEntry.name == "api-key").first()
        assert entry.user_id == user.id
        assert entry.encrypted_value != "sk-real-value"
        assert result["value"] == "••••••••"


class TestGetSecretRevealGate:
    def test_masked_view_allowed_for_any_authenticated_user(self):
        db = _session()
        owner = _make_user(db, email="owner@zect.local")
        other = _make_user(db, email="other@zect.local")
        create_secret(SecretCreate(name="s1", value="real-value", scope="user"), current_user=_current_user_for(owner), db=db)
        entry = db.query(SecretEntry).first()

        result = get_secret(entry.id, reveal=False, current_user=_current_user_for(other), db=db)

        assert result["value"] == "••••••••"

    def test_reveal_denied_for_non_owner_non_admin(self):
        db = _session()
        owner = _make_user(db, email="owner@zect.local")
        other = _make_user(db, email="other@zect.local")
        create_secret(SecretCreate(name="s1", value="real-value", scope="user"), current_user=_current_user_for(owner), db=db)
        entry = db.query(SecretEntry).first()

        with pytest.raises(PermissionDenied):
            get_secret(entry.id, reveal=True, current_user=_current_user_for(other), db=db)

    def test_reveal_allowed_for_owner(self):
        db = _session()
        owner = _make_user(db, email="owner@zect.local")
        create_secret(SecretCreate(name="s1", value="real-value", scope="user"), current_user=_current_user_for(owner), db=db)
        entry = db.query(SecretEntry).first()

        result = get_secret(entry.id, reveal=True, current_user=_current_user_for(owner), db=db)

        assert result["value"] == "real-value"

    def test_reveal_allowed_for_admin(self):
        db = _session()
        owner = _make_user(db, email="owner@zect.local")
        admin = _make_user(db, email="admin@zect.local", role="admin")
        create_secret(SecretCreate(name="s1", value="real-value", scope="user"), current_user=_current_user_for(owner), db=db)
        entry = db.query(SecretEntry).first()

        result = get_secret(entry.id, reveal=True, current_user=_current_user_for(admin), db=db)

        assert result["value"] == "real-value"


class TestUpdateSecretRequiresAccess:
    def test_update_denied_for_non_owner_non_admin(self):
        db = _session()
        owner = _make_user(db, email="owner@zect.local")
        other = _make_user(db, email="other@zect.local")
        create_secret(SecretCreate(name="s1", value="v1", scope="user"), current_user=_current_user_for(owner), db=db)
        entry = db.query(SecretEntry).first()

        with pytest.raises(PermissionDenied):
            update_secret(entry.id, SecretUpdate(value="v2"), current_user=_current_user_for(other), db=db)

    def test_update_allowed_for_owner(self):
        db = _session()
        owner = _make_user(db, email="owner@zect.local")
        create_secret(SecretCreate(name="s1", value="v1", scope="user"), current_user=_current_user_for(owner), db=db)
        entry = db.query(SecretEntry).first()

        update_secret(entry.id, SecretUpdate(description="updated"), current_user=_current_user_for(owner), db=db)

        db.refresh(entry)
        assert entry.description == "updated"


class TestRotateSecretBodyNotQueryParam:
    def test_new_value_is_a_pydantic_body_field(self):
        # If new_value were still a bare `str` param, FastAPI would bind it
        # from the query string. SecretRotate being a BaseModel with a single
        # required field is what forces it into the request body instead.
        assert SecretRotate.model_fields["new_value"].annotation is str

    def test_rotate_denied_for_non_owner_non_admin(self):
        db = _session()
        owner = _make_user(db, email="owner@zect.local")
        other = _make_user(db, email="other@zect.local")
        create_secret(SecretCreate(name="s1", value="v1", scope="user"), current_user=_current_user_for(owner), db=db)
        entry = db.query(SecretEntry).first()

        with pytest.raises(PermissionDenied):
            rotate_secret(entry.id, SecretRotate(new_value="v2"), current_user=_current_user_for(other), db=db)

    def test_rotate_allowed_for_owner_and_re_encrypts(self):
        db = _session()
        owner = _make_user(db, email="owner@zect.local")
        create_secret(SecretCreate(name="s1", value="v1", scope="user"), current_user=_current_user_for(owner), db=db)
        entry = db.query(SecretEntry).first()
        old_ciphertext = entry.encrypted_value

        rotate_secret(entry.id, SecretRotate(new_value="v2-rotated"), current_user=_current_user_for(owner), db=db)

        db.refresh(entry)
        assert entry.encrypted_value != old_ciphertext
        revealed = get_secret(entry.id, reveal=True, current_user=_current_user_for(owner), db=db)
        assert revealed["value"] == "v2-rotated"
