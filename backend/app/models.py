from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


# ---------------------------------------------------------------------------
# User & Authentication (SSO-ready)
# ---------------------------------------------------------------------------

class User(Base):
    """User accounts — SSO-ready with role-based access."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    role = Column(String, default="developer")  # admin, lead, developer, viewer
    team = Column(String, default="")  # e.g. "Platform", "Claims", "Policy"
    department = Column(String, default="")
    sso_provider = Column(String, nullable=True)  # azure-ad, okta, google, etc.
    sso_id = Column(String, nullable=True, unique=True)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    token_logs = relationship("TokenLog", back_populates="user")
    budgets = relationship("TokenBudget", back_populates="user")
    generated_outputs = relationship("GeneratedOutput", back_populates="user")


# ---------------------------------------------------------------------------
# Token Tracking & Audit
# ---------------------------------------------------------------------------

class TokenLog(Base):
    """Persistent audit log for every token-consuming operation."""
    __tablename__ = "token_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # nullable for pre-SSO usage
    session_id = Column(Integer, ForeignKey("user_sessions.id"), nullable=True)
    action = Column(String, nullable=False)       # e.g. ask, plan, build, review, enhance_blueprint, repo_analysis
    feature = Column(String, default="")           # ask_mode, plan_mode, build_phase, review_phase, blueprint, doc_gen
    model = Column(String, default="")             # e.g. gpt-4o-mini, claude-3.5-sonnet, llama-3.1-8b
    provider = Column(String, default="")          # openai, openrouter, anthropic, local
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    request_payload_size = Column(Integer, default=0)  # size of input in chars
    response_payload_size = Column(Integer, default=0)  # size of output in chars
    latency_ms = Column(Integer, default=0)  # response time in milliseconds
    status = Column(String, default="success")  # success, error, timeout, rate_limited
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="token_logs")


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
    """Token budget configuration and limits — per-user or global."""
    __tablename__ = "token_budgets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # null = global default
    scope = Column(String, default="global")  # global, team, user
    daily_token_limit = Column(Integer, default=0)  # 0 = unlimited
    monthly_token_limit = Column(Integer, default=0)
    daily_cost_limit_usd = Column(Float, default=0.0)
    monthly_cost_limit_usd = Column(Float, default=0.0)
    alert_threshold_percent = Column(Integer, default=80)
    preferred_model = Column(String, default="gpt-4o-mini")
    allowed_models = Column(String, default="gpt-4o-mini,gpt-4o,gpt-3.5-turbo")
    enforce_limits = Column(Boolean, default=False)  # block requests when limit hit
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="budgets")


# ---------------------------------------------------------------------------
# Sessions & Context
# ---------------------------------------------------------------------------

class UserSession(Base):
    """Per-user work sessions — tracks what each user does in each project."""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    session_type = Column(String, default="general")  # ask, plan, build, review, deploy, general
    title = Column(String, default="")  # e.g. "Planning auth microservice"
    status = Column(String, default="active")  # active, completed, abandoned
    total_tokens_used = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)
    models_used = Column(String, default="")  # comma-separated list of models used
    messages_count = Column(Integer, default=0)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="sessions")
    context_files = relationship("ContextFile", back_populates="session", cascade="all, delete-orphan")
    generated_outputs = relationship("GeneratedOutput", back_populates="session")


class ContextFile(Base):
    """Attached files/repos/snippets per session — provides context to AI."""
    __tablename__ = "context_files"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("user_sessions.id"), nullable=False, index=True)
    name = Column(String, nullable=False)  # file path or repo name
    file_type = Column(String, default="file")  # file, repo, snippet
    content = Column(Text, default="")  # actual content
    char_count = Column(Integer, default=0)
    token_estimate = Column(Integer, default=0)  # estimated tokens this file consumes
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    session = relationship("UserSession", back_populates="context_files")


# ---------------------------------------------------------------------------
# Generated Outputs
# ---------------------------------------------------------------------------

class GeneratedOutput(Base):
    """Store all AI-generated code/plans/reviews for history and audit."""
    __tablename__ = "generated_outputs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    session_id = Column(Integer, ForeignKey("user_sessions.id"), nullable=True)
    output_type = Column(String, nullable=False)  # code, plan, review, checklist, runbook, blueprint
    feature = Column(String, default="")  # build_phase, plan_mode, review_phase, etc.
    title = Column(String, default="")  # e.g. "REST API endpoint for auth"
    prompt_used = Column(Text, default="")  # the user's input/prompt
    output_content = Column(Text, default="")  # the generated content
    language = Column(String, default="")  # typescript, python, etc.
    file_path = Column(String, default="")  # target file path if applicable
    model_used = Column(String, default="")
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    quality_score = Column(Float, nullable=True)  # user rating 1-5
    was_accepted = Column(Boolean, nullable=True)  # did user accept/use this output?
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="generated_outputs")
    session = relationship("UserSession", back_populates="generated_outputs")
