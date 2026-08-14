"""Present Deck analysis API — Flow A/B (PresentationService; Presenton stays default)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
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


class PresentationPlanIn(BaseModel):
    prompt: str
    n_slides: int = 6
    template_id: str = ""
    audience_id: str = "general"
    sensitivity_hint: Optional[str] = None
    documents: list[str] = Field(default_factory=list)
    asset_ids: list[str] = Field(default_factory=list)


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
    from app.services.mentrix.presentation.template_importer import MAX_ARCHIVE_BYTES

    raw = await file.read(MAX_ARCHIVE_BYTES + 1)
    if len(raw) > MAX_ARCHIVE_BYTES:
        return {"ok": False, "error": "invalid_or_too_large"}
    return tmpl.import_canonical_master(
        zect_id,
        raw,
        name=name or "",
        filename=file.filename or "",
    )


@router.post("/plan")
@require_authentication
def presentation_plan(body: PresentationPlanIn, current_user: CurrentUser = Depends(get_current_user)):
    """Structured PresentationPlan via Model Gateway. Does not call Presenton."""
    from app.services.mentrix.presentation.provider import PresentationGenerateRequest
    from app.services.mentrix.presentation.service import PresentationService

    context_items = [
        {"source_type": "document", "source_id": f"doc-{i}", "content": text}
        for i, text in enumerate(body.documents or [])
        if str(text or "").strip()
    ]
    return PresentationService().plan(
        PresentationGenerateRequest(
            content=body.prompt,
            n_slides=body.n_slides,
            template=body.template_id,
            ui_template_choice=body.template_id,
            audience_id=body.audience_id,
            sensitivity_hint=body.sensitivity_hint or "",
            context_items=context_items,
            user_id=str(getattr(current_user, "user_id", None) or getattr(current_user, "username", "anon")),
            asset_ids=list(body.asset_ids or []),
        )
    )


@router.post("/assets")
@require_authentication
async def presentation_asset_upload(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Store an authorized PNG/JPEG/GIF/WEBP for ImageBlocks. No URL fetch. SVG rejected."""
    from app.services.mentrix.presentation.asset_resolver import MAX_BYTES, UnsafeImageError, store_image

    uid = str(getattr(current_user, "user_id", None) or getattr(current_user, "username", "anon"))
    raw = await file.read(MAX_BYTES + 1)
    if not raw:
        return {"ok": False, "error": "image_empty"}
    if len(raw) > MAX_BYTES:
        return {"ok": False, "error": "image_too_large"}
    try:
        meta = store_image(raw, user_id=uid, filename=file.filename or "", mime=file.content_type or "")
    except UnsafeImageError as exc:
        return {"ok": False, "error": str(exc)}
    return meta


@router.get("/assets/{asset_id}")
@require_authentication
def presentation_asset_get(asset_id: str, current_user: CurrentUser = Depends(get_current_user)):
    from fastapi.responses import FileResponse

    from app.services.mentrix.presentation.asset_resolver import UnsafeImageError, load_image

    uid = str(getattr(current_user, "user_id", None) or getattr(current_user, "username", "anon"))
    try:
        asset = load_image(asset_id, user_id=uid)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="asset_not_found") from exc
    except UnsafeImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FileResponse(path=str(asset["path"]), media_type=str(asset["mime"]), filename=f"{asset['asset_id']}{asset['path'].suffix}")
