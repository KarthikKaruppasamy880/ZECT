from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class TokenLog(Base):
    """Persistent audit log for every token-consuming operation."""
    __tablename__ = "token_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False)       # e.g. ask, plan, enhance_blueprint, repo_analysis, etc.
    feature = Column(String, default="")           # ask_mode, plan_mode, blueprint, doc_gen, repo_analysis
    model = Column(String, default="")             # e.g. gpt-4o-mini, github-api
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)  # estimated cost in USD
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    team = Column(String, default="")
    status = Column(String, default="active")  # active, completed, on-hold
    current_stage = Column(String, default="ask")  # ask, plan, build, review, deploy
    completion_percent = Column(Float, default=0.0)
    token_savings = Column(Float, default=0.0)
    risk_alerts = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    repos = relationship("Repo", back_populates="project", cascade="all, delete-orphan")


class Repo(Base):
    __tablename__ = "repos"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    owner = Column(String, nullable=False)
    repo_name = Column(String, nullable=False)
    default_branch = Column(String, default="main")
    ci_status = Column(String, default="unknown")  # passing, failing, pending, unknown
    coverage_percent = Column(Float, default=0.0)
    last_synced = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="repos")


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(String, default="")
    setting_type = Column(String, default="text")  # toggle, select, text
    label = Column(String, default="")
    description = Column(String, default="")
    options = Column(String, default="")  # JSON array for select options


class Skill(Base):
    """Reusable skill templates for AI agents."""
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    category = Column(String, default="general")  # general, testing, deployment, review, architecture
    template = Column(Text, default="")  # The actual skill content/template
    trigger_pattern = Column(String, nullable=True)  # Regex or keyword that triggers this skill
    tags = Column(String, default="[]")  # JSON array of tags
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class TokenBudget(Base):
    """Token budget configuration and limits."""
    __tablename__ = "token_budgets"

    id = Column(Integer, primary_key=True, index=True)
    daily_token_limit = Column(Integer, default=0)  # 0 = unlimited
    monthly_token_limit = Column(Integer, default=0)
    daily_cost_limit_usd = Column(Float, default=0.0)
    monthly_cost_limit_usd = Column(Float, default=0.0)
    alert_threshold_percent = Column(Integer, default=80)
    preferred_model = Column(String, default="gpt-4o-mini")
    allowed_models = Column(String, default="gpt-4o-mini,gpt-4o,gpt-3.5-turbo")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
