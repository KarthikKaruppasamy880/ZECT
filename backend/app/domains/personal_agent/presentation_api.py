"""Present Deck analysis API — Flow A/B (PresentationService; Presenton stays default)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field

from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.auth.rbac import require_authentication
from app.services.mentrix.presentation import (
    analyze_existing_deck,
    list_audiences,
    prepare_prompt_deck,
    verify_claim,
)
from app.services.mentrix.presentation import template_registry as tmpl

router = APIRouter(prefix="/api/mentrix/presentation", tags=["mentrix-presentation"])


class AnalyzeDeckIn(BaseModel):
    slides: list[dict[str, Any]] = Field(default_factory=list)
    notes_blob: str = ""
    audience_id: str = "general"
    sensitivity_hint: Optional[str] = None


class PreparePromptIn(BaseModel):
    prompt: str
    audience_id: str = "general"
    sensitivity_hint: Optional[str] = None
    documents: list[str] = Field(default_factory=list)


class VerifyClaimIn(BaseModel):
    claim_id: str
    claims: list[dict[str, Any]]
    source: str
    status: str = "VERIFIED"


class PreviewIn(BaseModel):
    template_id: str


class MappingIn(BaseModel):
    zect_id: str
    provider_template_id: str


class BindUploadIn(BaseModel):
    template_id: str
    provider_template_id: str


@router.get("/audiences")
@require_authentication
def audiences(current_user: CurrentUser = Depends(get_current_user)):
    return {"audiences": list_audiences()}


@router.post("/analyze-deck")
@require_authentication
def analyze_deck(body: AnalyzeDeckIn, current_user: CurrentUser = Depends(get_current_user)):
    return analyze_existing_deck(
        slides=body.slides,
        notes_blob=body.notes_blob,
        audience_id=body.audience_id,
        sensitivity_hint=body.sensitivity_hint,
    )


@router.post("/prepare-prompt")
@require_authentication
def prepare_prompt(body: PreparePromptIn, current_user: CurrentUser = Depends(get_current_user)):
    return prepare_prompt_deck(
        prompt=body.prompt,
        audience_id=body.audience_id,
        sensitivity_hint=body.sensitivity_hint,
        documents=body.documents,
    )


@router.post("/verify-claim")
@require_authentication
def verify_claim_endpoint(body: VerifyClaimIn, current_user: CurrentUser = Depends(get_current_user)):
    claims = verify_claim(body.claim_id, body.claims, source=body.source, status=body.status)
    return {"claims": claims}


@router.get("/templates")
@require_authentication
def presentation_templates(current_user: CurrentUser = Depends(get_current_user)):
    uid = getattr(current_user, "user_id", None) or getattr(current_user, "username", "anon")
    return tmpl.list_templates(uid)


@router.post("/templates/preview")
@require_authentication
def presentation_template_preview(body: PreviewIn, current_user: CurrentUser = Depends(get_current_user)):
    uid = getattr(current_user, "user_id", None) or getattr(current_user, "username", "anon")
    return tmpl.preview_template(uid, body.template_id)


@router.post("/templates/upload")
@require_authentication
async def presentation_template_upload(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    scope: Optional[str] = Form("USER"),
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = getattr(current_user, "user_id", None) or getattr(current_user, "username", "anon")
    want_org = (scope or "USER").strip().upper() in {"ORG", "ORGANIZATION", "ORG_SHARED"}
    if want_org and (current_user.role or "").lower() != "admin":
        return {"ok": False, "error": "org_scope_requires_admin"}
    return await tmpl.register_user_pptx(uid, file, name=name, scope=scope or "USER")


@router.post("/templates/mapping")
@require_authentication
def presentation_template_mapping(body: MappingIn, current_user: CurrentUser = Depends(get_current_user)):
    """Admin/setup: bind a canonical ZECT template id to a real provider master id."""
    if (current_user.role or "").lower() != "admin":
        return {"ok": False, "error": "admin_required"}
    actor = getattr(current_user, "email", None) or getattr(current_user, "username", "") or ""
    return tmpl.register_provider_mapping(
        body.zect_id,
        body.provider_template_id,
        actor=str(actor),
        source="admin",
    )


@router.post("/templates/bind")
@require_authentication
def presentation_template_bind(body: BindUploadIn, current_user: CurrentUser = Depends(get_current_user)):
    uid = getattr(current_user, "user_id", None) or getattr(current_user, "username", "anon")
    return tmpl.bind_uploaded_template_provider(uid, body.template_id, body.provider_template_id)


@router.post("/templates/import-master")
@require_authentication
async def presentation_template_import_master(
    file: UploadFile = File(...),
    zect_id: str = Form(...),
    name: Optional[str] = Form(None),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Admin: import a Zinnia/org PPTX into TemplateDefinition (no Presenton required)."""
    if (current_user.role or "").lower() != "admin":
        return {"ok": False, "error": "admin_required"}
    raw = await file.read()
    return tmpl.import_canonical_master(
        zect_id,
        raw,
        name=name or "",
        filename=file.filename or "",
    )
