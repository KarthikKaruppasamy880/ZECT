import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Setting
from app.schemas import SettingOut, SettingUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])

DEFAULT_SETTINGS = [
    {"key": "auto-review", "value": "true", "setting_type": "toggle", "label": "Automated Code Review", "description": "Automatically run security and quality checks when a build phase completes."},
    {"key": "token-tracking", "value": "true", "setting_type": "toggle", "label": "Token Usage Tracking", "description": "Track AI token consumption across all projects and sessions."},
    {"key": "deploy-gates", "value": "true", "setting_type": "toggle", "label": "Deployment Gate Enforcement", "description": "Block deployments when critical review findings are unresolved."},
    {"key": "risk-alerts", "value": "false", "setting_type": "toggle", "label": "Risk Alert Notifications", "description": "Send Slack/email notifications when new risk alerts are detected."},
    {"key": "auto-plan", "value": "false", "setting_type": "toggle", "label": "Auto-Generate Plan from Requirements", "description": "Automatically generate architecture and API plans from approved requirements."},
    {"key": "session-context", "value": "true", "setting_type": "toggle", "label": "Session Context Memory", "description": "Persist context across AI sessions using ZEF context management."},
    {"key": "default-stage", "value": "Ask Mode", "setting_type": "select", "label": "Default Starting Stage", "description": "Which stage new projects start in by default.", "options": json.dumps(["Ask Mode", "Plan Mode", "Build Phase"])},
    {"key": "review-severity", "value": "Medium", "setting_type": "select", "label": "Minimum Review Severity", "description": "Only surface findings at or above this severity level.", "options": json.dumps(["Critical", "High", "Medium", "Low", "Info"])},
    {"key": "deploy-approval", "value": "Tech Lead + PM", "setting_type": "select", "label": "Deployment Approval Mode", "description": "Who must approve before a deployment can proceed.", "options": json.dumps(["Anyone", "Tech Lead", "Tech Lead + PM", "VP Engineering"])},
    {"key": "token-budget", "value": "80% of budget", "setting_type": "select", "label": "Monthly Token Budget Alert", "description": "Alert threshold for monthly AI token consumption.", "options": json.dumps(["50% of budget", "70% of budget", "80% of budget", "90% of budget", "No alert"])},
]


def seed_settings(db: Session):
    if db.query(Setting).count() == 0:
        for s in DEFAULT_SETTINGS:
            db.add(Setting(**s))
        db.commit()


@router.get("", response_model=list[SettingOut])
def list_settings(db: Session = Depends(get_db)):
    seed_settings(db)
    return db.query(Setting).all()


@router.put("/{key}", response_model=SettingOut)
def update_setting(key: str, data: SettingUpdate, db: Session = Depends(get_db)):
    setting = db.query(Setting).filter(Setting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    setting.value = data.value
    db.commit()
    db.refresh(setting)
    return setting
