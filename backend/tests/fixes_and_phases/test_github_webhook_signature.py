"""GitHub webhook signature verification was opt-in — X-Hub-Signature-256 was
only checked if an admin had previously set a webhook_secret for that repo.
Any repo where the secret was never configured accepted unauthenticated
POSTs that triggered a real code-review run under a synthetic identity.
Verifies a secret is now mandatory before the webhook accepts anything.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.infrastructure.database import Base
from app.models import ReviewWebhookConfig
from app.domains.pr_review.code_review import github_webhook


class _FakeRequest:
    def __init__(self, body: bytes, headers: dict[str, str] | None = None):
        self._body = body
        self.headers = headers or {}

    async def body(self) -> bytes:
        return self._body


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _configure_webhook(db, *, owner="acme", repo="widgets", secret="", enabled=True, auto_review=True):
    row = ReviewWebhookConfig(
        owner=owner, repo=repo, enabled=enabled, auto_review=auto_review, webhook_secret=secret,
    )
    db.add(row)
    db.commit()
    return row


def _pr_payload(owner="acme", repo="widgets", number=42, action="opened"):
    return json.dumps(
        {
            "action": action,
            "pull_request": {"number": number},
            "repository": {"full_name": f"{owner}/{repo}"},
        }
    ).encode()


class TestWebhookRequiresSecret:
    def test_no_secret_configured_is_rejected(self):
        db = _session()
        _configure_webhook(db, secret="")
        req = _FakeRequest(_pr_payload(), headers={"X-GitHub-Event": "pull_request"})

        with pytest.raises(HTTPException) as exc:
            asyncio.run(github_webhook(req, db=db))

        assert exc.value.status_code == 403
        assert "secret" in exc.value.detail.lower()

    def test_secret_configured_but_signature_missing_is_rejected(self):
        db = _session()
        _configure_webhook(db, secret="s3cr3t")
        req = _FakeRequest(_pr_payload(), headers={"X-GitHub-Event": "pull_request"})

        with pytest.raises(HTTPException) as exc:
            asyncio.run(github_webhook(req, db=db))

        assert exc.value.status_code == 403
        assert "signature" in exc.value.detail.lower()

    def test_secret_configured_with_wrong_signature_is_rejected(self):
        db = _session()
        _configure_webhook(db, secret="s3cr3t")
        req = _FakeRequest(
            _pr_payload(),
            headers={"X-GitHub-Event": "pull_request", "X-Hub-Signature-256": "sha256=deadbeef"},
        )

        with pytest.raises(HTTPException) as exc:
            asyncio.run(github_webhook(req, db=db))

        assert exc.value.status_code == 403

    def test_secret_configured_with_correct_signature_is_accepted(self, monkeypatch):
        db = _session()
        _configure_webhook(db, secret="s3cr3t")
        body = _pr_payload()
        sig = "sha256=" + hmac.new(b"s3cr3t", body, hashlib.sha256).hexdigest()
        req = _FakeRequest(body, headers={"X-GitHub-Event": "pull_request", "X-Hub-Signature-256": sig})

        monkeypatch.setattr(
            "app.domains.pr_review.code_review.review_pull_request",
            lambda req, current_user, db: {"status": "completed", "score": 90, "findings": []},
        )

        result = asyncio.run(github_webhook(req, db=db))

        assert result["status"] != "skipped"

    def test_disabled_repo_is_skipped_before_signature_check(self):
        """A repo that's never been configured for auto-review at all should
        short-circuit to 'skipped', not 403 — the secret requirement only
        applies once a repo has opted in."""
        db = _session()
        req = _FakeRequest(_pr_payload(owner="someone", repo="unrelated"), headers={"X-GitHub-Event": "pull_request"})

        result = asyncio.run(github_webhook(req, db=db))

        assert result["status"] == "skipped"
