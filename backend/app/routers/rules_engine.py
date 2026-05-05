"""Rules Engine — User-created rules for code review, quality gates, deployment."""

import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import Rule

router = APIRouter(prefix="/api/rules", tags=["rules"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RuleCreate(BaseModel):
    name: str
    description: str = ""
    rule_type: str  # review, quality_gate, deploy, naming, security
    condition: str  # JSON rule condition or regex pattern
    action: str = "warn"  # warn, block, auto_fix, notify
    severity: str = "medium"  # critical, high, medium, low, info
    repo_id: int | None = None
    is_active: bool = True


class RuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    rule_type: str | None = None
    condition: str | None = None
    action: str | None = None
    severity: str | None = None
    is_active: bool | None = None


class RuleOut(BaseModel):
    id: int
    repo_id: int | None
    name: str
    description: str
    rule_type: str
    condition: str
    action: str
    severity: str
    is_active: bool
    created_by: int | None
    created_at: str
    updated_at: str


class RuleEvalRequest(BaseModel):
    code: str
    language: str = "typescript"
    rule_ids: list[int] | None = None  # specific rules to evaluate, or all active


class RuleEvalResult(BaseModel):
    rule_id: int
    rule_name: str
    matched: bool
    severity: str
    action: str
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[RuleOut])
@router.get("/", response_model=list[RuleOut])
def list_rules(
    rule_type: str | None = None,
    is_active: bool | None = None,
    repo_id: int | None = None,
    db: Session = Depends(get_db),
):
    """List all rules with optional filters."""
    query = db.query(Rule)
    if rule_type:
        query = query.filter(Rule.rule_type == rule_type)
    if is_active is not None:
        query = query.filter(Rule.is_active == is_active)
    if repo_id is not None:
        query = query.filter(Rule.repo_id == repo_id)
    rules = query.order_by(Rule.created_at.desc()).all()
    return [
        RuleOut(
            id=r.id, repo_id=r.repo_id, name=r.name, description=r.description or "",
            rule_type=r.rule_type, condition=r.condition, action=r.action,
            severity=r.severity, is_active=r.is_active, created_by=r.created_by,
            created_at=r.created_at.isoformat() if r.created_at else "",
            updated_at=r.updated_at.isoformat() if r.updated_at else "",
        )
        for r in rules
    ]


@router.post("", response_model=RuleOut)
@router.post("/", response_model=RuleOut)
def create_rule(req: RuleCreate, db: Session = Depends(get_db)):
    """Create a new rule."""
    rule = Rule(
        name=req.name,
        description=req.description,
        rule_type=req.rule_type,
        condition=req.condition,
        action=req.action,
        severity=req.severity,
        repo_id=req.repo_id,
        is_active=req.is_active,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return RuleOut(
        id=rule.id, repo_id=rule.repo_id, name=rule.name, description=rule.description or "",
        rule_type=rule.rule_type, condition=rule.condition, action=rule.action,
        severity=rule.severity, is_active=rule.is_active, created_by=rule.created_by,
        created_at=rule.created_at.isoformat() if rule.created_at else "",
        updated_at=rule.updated_at.isoformat() if rule.updated_at else "",
    )


@router.get("/{rule_id}", response_model=RuleOut)
def get_rule(rule_id: int, db: Session = Depends(get_db)):
    """Get a rule by ID."""
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return RuleOut(
        id=rule.id, repo_id=rule.repo_id, name=rule.name, description=rule.description or "",
        rule_type=rule.rule_type, condition=rule.condition, action=rule.action,
        severity=rule.severity, is_active=rule.is_active, created_by=rule.created_by,
        created_at=rule.created_at.isoformat() if rule.created_at else "",
        updated_at=rule.updated_at.isoformat() if rule.updated_at else "",
    )


@router.put("/{rule_id}", response_model=RuleOut)
def update_rule(rule_id: int, req: RuleUpdate, db: Session = Depends(get_db)):
    """Update a rule."""
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    if req.name is not None:
        rule.name = req.name
    if req.description is not None:
        rule.description = req.description
    if req.rule_type is not None:
        rule.rule_type = req.rule_type
    if req.condition is not None:
        rule.condition = req.condition
    if req.action is not None:
        rule.action = req.action
    if req.severity is not None:
        rule.severity = req.severity
    if req.is_active is not None:
        rule.is_active = req.is_active
    rule.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rule)
    return RuleOut(
        id=rule.id, repo_id=rule.repo_id, name=rule.name, description=rule.description or "",
        rule_type=rule.rule_type, condition=rule.condition, action=rule.action,
        severity=rule.severity, is_active=rule.is_active, created_by=rule.created_by,
        created_at=rule.created_at.isoformat() if rule.created_at else "",
        updated_at=rule.updated_at.isoformat() if rule.updated_at else "",
    )


@router.delete("/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    """Delete a rule."""
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
    return {"deleted": True}


@router.post("/evaluate", response_model=list[RuleEvalResult])
def evaluate_rules(req: RuleEvalRequest, db: Session = Depends(get_db)):
    """Evaluate code against active rules (regex-based pattern matching)."""
    import re
    query = db.query(Rule).filter(Rule.is_active == True)
    if req.rule_ids:
        query = query.filter(Rule.id.in_(req.rule_ids))
    rules = query.all()

    results = []
    for rule in rules:
        matched = False
        message = "No match"
        try:
            if re.search(rule.condition, req.code, re.MULTILINE | re.IGNORECASE):
                matched = True
                message = f"Rule '{rule.name}' matched: {rule.description}"
        except re.error:
            message = f"Invalid regex pattern in rule '{rule.name}'"

        results.append(RuleEvalResult(
            rule_id=rule.id,
            rule_name=rule.name,
            matched=matched,
            severity=rule.severity,
            action=rule.action,
            message=message,
        ))
    return results
