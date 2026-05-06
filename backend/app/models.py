from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, ARRAY
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
    """Reusable skill templates for AI agents — can be global or scoped to a repo."""
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    category = Column(String, default="general")  # general, testing, deployment, review, architecture
    template = Column(Text, default="")  # The actual skill content/template
    trigger_pattern = Column(String, nullable=True)  # Regex or keyword that triggers this skill
    tags = Column(String, default="[]")  # JSON array of tags
    usage_count = Column(Integer, default=0)
    repo_id = Column(Integer, ForeignKey("repos.id"), nullable=True, index=True)  # null = global skill
    scope = Column(String, default="global")  # global, repo
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    repo = relationship("Repo", backref="skills")


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


# ---------------------------------------------------------------------------
# Audit Trail
# ---------------------------------------------------------------------------

class AuditLog(Base):
    """Full audit trail for all CRUD operations."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String, nullable=False)  # create, update, delete, login, logout, export, review
    resource_type = Column(String, nullable=False)  # project, repo, skill, setting, user, review, etc.
    resource_id = Column(Integer, nullable=True)
    resource_name = Column(String, default="")
    details = Column(Text, default="")  # JSON with old/new values or extra context
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Code Review (Ultrareview-style)
# ---------------------------------------------------------------------------

class ReviewSession(Base):
    """A code review session — can review a PR, branch diff, or standalone code."""
    __tablename__ = "review_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    repo_id = Column(Integer, ForeignKey("repos.id"), nullable=True, index=True)
    review_type = Column(String, nullable=False)  # pr, branch, snippet, full_repo
    pr_number = Column(Integer, nullable=True)
    branch_name = Column(String, nullable=True)
    base_branch = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, running, completed, failed
    total_findings = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    info_count = Column(Integer, default=0)
    overall_score = Column(Float, default=0.0)  # 0-100
    review_summary = Column(Text, default="")
    files_reviewed = Column(Integer, default=0)
    lines_reviewed = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    duration_seconds = Column(Integer, default=0)
    model_used = Column(String, default="gpt-4o-mini")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    findings = relationship("ReviewFinding", back_populates="review_session", cascade="all, delete-orphan")
    repo = relationship("Repo", backref="review_sessions")


class ReviewFinding(Base):
    """Individual finding from a code review — bug, security issue, style, etc."""
    __tablename__ = "review_findings"

    id = Column(Integer, primary_key=True, index=True)
    review_session_id = Column(Integer, ForeignKey("review_sessions.id"), nullable=False, index=True)
    category = Column(String, nullable=False)  # bug, security, performance, style, architecture, best_practice
    severity = Column(String, nullable=False)  # critical, high, medium, low, info
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    file_path = Column(String, nullable=True)
    line_start = Column(Integer, nullable=True)
    line_end = Column(Integer, nullable=True)
    code_snippet = Column(Text, nullable=True)
    suggestion = Column(Text, nullable=True)  # recommended fix
    fixed_code = Column(Text, nullable=True)  # auto-generated fix
    cwe_id = Column(String, nullable=True)  # CWE ID for security findings
    owasp_category = Column(String, nullable=True)  # OWASP category
    is_verified = Column(Boolean, default=False)  # independently verified (ultrareview)
    is_false_positive = Column(Boolean, default=False)  # user marked as false positive
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    review_session = relationship("ReviewSession", back_populates="findings")


# ---------------------------------------------------------------------------
# Jira Integration
# ---------------------------------------------------------------------------

class JiraConfig(Base):
    """Jira integration configuration."""
    __tablename__ = "jira_configs"

    id = Column(Integer, primary_key=True, index=True)
    base_url = Column(String, nullable=False)  # https://yourcompany.atlassian.net
    email = Column(String, nullable=False)
    api_token_encrypted = Column(String, nullable=False)  # encrypted Jira API token
    default_project_key = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class JiraTicketLink(Base):
    """Link between ZECT entities and Jira tickets."""
    __tablename__ = "jira_ticket_links"

    id = Column(Integer, primary_key=True, index=True)
    jira_config_id = Column(Integer, ForeignKey("jira_configs.id"), nullable=False)
    ticket_key = Column(String, nullable=False, index=True)  # e.g. PROJ-123
    ticket_url = Column(String, nullable=False)
    ticket_summary = Column(String, default="")
    ticket_status = Column(String, default="")
    ticket_type = Column(String, default="")  # story, bug, task, epic
    resource_type = Column(String, nullable=False)  # project, review_session, generated_output
    resource_id = Column(Integer, nullable=False)
    synced_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Slack Integration
# ---------------------------------------------------------------------------

class SlackConfig(Base):
    """Slack integration configuration."""
    __tablename__ = "slack_configs"

    id = Column(Integer, primary_key=True, index=True)
    workspace_name = Column(String, default="")
    bot_token_encrypted = Column(String, nullable=False)
    default_channel = Column(String, default="")  # e.g. #zect-notifications
    notify_on_review = Column(Boolean, default=True)
    notify_on_deploy = Column(Boolean, default=True)
    notify_on_budget_alert = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# User-Created Rules
# ---------------------------------------------------------------------------

class Rule(Base):
    """User-created rules for code review, quality gates, deployment, etc."""
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repos.id"), nullable=True, index=True)  # null = global rule
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    rule_type = Column(String, nullable=False)  # review, quality_gate, deploy, naming, security
    condition = Column(Text, nullable=False)  # JSON rule condition or regex pattern
    action = Column(String, default="warn")  # warn, block, auto_fix, notify
    severity = Column(String, default="medium")  # critical, high, medium, low, info
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    repo = relationship("Repo", backref="rules")


# ---------------------------------------------------------------------------
# Export Jobs
# ---------------------------------------------------------------------------

class ExportJob(Base):
    """Track export requests for PDF/Markdown generation."""
    __tablename__ = "export_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    export_type = Column(String, nullable=False)  # pdf, markdown
    content_type = Column(String, nullable=False)  # blueprint, plan, review, code, deploy_checklist
    source_id = Column(Integer, nullable=True)  # ID of the source (generated_output, review_session, etc.)
    title = Column(String, default="")
    status = Column(String, default="pending")  # pending, processing, completed, failed
    file_path = Column(String, nullable=True)  # path to generated file
    file_size_bytes = Column(Integer, default=0)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)


# ===========================================================================
# ZINNIA AGENTIC INTELLIGENCE SYSTEM
# Memory (4 layers), Dream Engine, Data Layer, Skills Engine,
# Permissions Protocol, Transfer & Onboarding
# ===========================================================================


# ---------------------------------------------------------------------------
# Layer 1: Working Memory — live task state, auto-archived after 2 days
# ---------------------------------------------------------------------------

class WorkingMemory(Base):
    """Live task state — volatile, auto-archived after inactivity."""
    __tablename__ = "working_memory"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    task_name = Column(String, default="")
    open_files = Column(JSON, default=list)  # list of file paths
    hypotheses = Column(JSON, default=list)  # list of active hypotheses
    checkpoints = Column(JSON, default=list)  # list of checkpoint descriptions
    next_step = Column(Text, default="")
    status = Column(String, default="active")  # active, archived
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    archived_at = Column(DateTime, nullable=True)

    project = relationship("Project", backref="working_memories")
    user = relationship("User", backref="working_memories")


# ---------------------------------------------------------------------------
# Layer 2: Episodic Memory — what happened in prior runs, scored by salience
# ---------------------------------------------------------------------------

class EpisodicMemory(Base):
    """Raw experience log — what happened, scored by salience, decayed over time."""
    __tablename__ = "episodic_memory"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    skill_name = Column(String, default="")  # which skill was used
    action = Column(String, nullable=False)  # what was done
    outcome = Column(Text, default="")  # what happened
    success = Column(Boolean, default=True)
    importance = Column(Integer, default=5)  # 1-10, higher = more important
    salience = Column(Float, default=0.5)  # 0.0-1.0, decayed over time
    confidence = Column(Float, default=0.5)  # 0.0-1.0
    pain_score = Column(Integer, default=2)  # 1-5, how painful was this
    evidence_ids = Column(JSON, default=list)  # related episodic IDs
    reflection = Column(Text, default="")  # post-action reflection
    harness = Column(String, default="zect")  # which AI tool was used
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    cost_estimate_usd = Column(Float, default=0.0)
    is_decayed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", backref="episodic_memories")
    user = relationship("User", backref="episodic_memories")


# ---------------------------------------------------------------------------
# Layer 3: Semantic Memory — distilled patterns (lessons + decisions)
# ---------------------------------------------------------------------------

class Lesson(Base):
    """Graduated lessons — distilled patterns that outlive episodes."""
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    claim = Column(Text, nullable=False)  # what was learned
    conditions = Column(JSON, default=list)  # when this applies (list of strings)
    rationale = Column(Text, default="")  # why this was graduated
    status = Column(String, default="staged")  # staged, accepted, rejected, provisional
    confidence = Column(Float, default=0.5)  # 0.0-1.0
    evidence_count = Column(Integer, default=1)
    cluster_size = Column(Integer, default=1)
    canonical_salience = Column(Float, default=0.5)
    reviewer = Column(String, default="")  # who graduated/rejected
    rejection_reason = Column(Text, nullable=True)
    rejection_count = Column(Integer, default=0)
    decision_history = Column(JSON, default=list)  # [{action, rationale, reviewer, at}]
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    accepted_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)

    project = relationship("Project", backref="lessons")
    user = relationship("User", backref="lessons")


class Decision(Base):
    """Architectural decisions with rationale and status tracking."""
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    title = Column(String, nullable=False)
    decision = Column(Text, nullable=False)
    rationale = Column(Text, default="")
    alternatives = Column(Text, default="")  # what else was considered
    status = Column(String, default="active")  # active, revisited, superseded
    superseded_by = Column(Integer, nullable=True)  # ID of replacing decision
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", backref="decisions")
    user = relationship("User", backref="decisions")


# ---------------------------------------------------------------------------
# Layer 4: Personal Memory — user preferences, never merged into semantic
# ---------------------------------------------------------------------------

class UserPreference(Base):
    """User-specific preferences — never merged into semantic memory."""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    code_style = Column(JSON, default=dict)  # {indent, quotes, semicolons, etc.}
    workflow = Column(JSON, default=dict)  # {prefer_tdd, branch_strategy, etc.}
    constraints = Column(JSON, default=dict)  # {no_force_push, require_tests, etc.}
    communication = Column(JSON, default=dict)  # {verbosity, format, etc.}
    feature_flags = Column(JSON, default=dict)  # {dream_cycle, data_flywheel, etc.}
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="preferences")


# ---------------------------------------------------------------------------
# Dream Engine — automated pattern extraction + candidate staging
# ---------------------------------------------------------------------------

class DreamCycleRun(Base):
    """Track each dream cycle execution and its results."""
    __tablename__ = "dream_cycle_runs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    status = Column(String, default="running")  # running, completed, failed
    episodes_processed = Column(Integer, default=0)
    clusters_found = Column(Integer, default=0)
    candidates_staged = Column(Integer, default=0)
    candidates_prefiltered = Column(Integer, default=0)
    episodes_decayed = Column(Integer, default=0)
    workspaces_archived = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project", backref="dream_cycle_runs")


# ---------------------------------------------------------------------------
# Data Layer — cross-agent monitoring, KPIs, dashboards
# ---------------------------------------------------------------------------

class AgentEvent(Base):
    """Cross-harness agent event tracking for monitoring dashboards."""
    __tablename__ = "agent_events"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    harness = Column(String, default="zect")  # zect, devin, cursor, etc.
    event_type = Column(String, nullable=False)  # task_start, task_end, error, review, deploy, commit, etc.
    category = Column(String, default="general")  # coding, review, deploy, planning, debugging
    description = Column(Text, default="")
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    model = Column(String, default="")
    duration_seconds = Column(Integer, default=0)
    success = Column(Boolean, default=True)
    metadata = Column(JSON, default=dict)  # extra event-specific data
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", backref="agent_events")
    user = relationship("User", backref="agent_events")


class DailyReport(Base):
    """Auto-generated daily summary reports."""
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    report_date = Column(DateTime, nullable=False)
    total_events = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)
    success_rate = Column(Float, default=0.0)  # 0.0-100.0
    harness_breakdown = Column(JSON, default=dict)  # {harness: {count, tokens, cost}}
    category_breakdown = Column(JSON, default=dict)  # {category: {count, tokens, cost}}
    model_breakdown = Column(JSON, default=dict)  # {model: {count, tokens, cost}}
    top_skills = Column(JSON, default=list)  # [{name, count, success_rate}]
    kpi_summary = Column(JSON, default=dict)  # {throughput, reliability, avg_cost, etc.}
    report_markdown = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", backref="daily_reports")


# ---------------------------------------------------------------------------
# Data Flywheel — approved runs → training-ready artifacts
# ---------------------------------------------------------------------------

class FlywheelTrace(Base):
    """Redacted traces from approved runs — first flywheel stage."""
    __tablename__ = "flywheel_traces"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    source_type = Column(String, nullable=False)  # review, build, plan, ask, deploy
    source_id = Column(Integer, nullable=True)  # ID from source table
    input_redacted = Column(Text, default="")  # redacted input
    output_redacted = Column(Text, default="")  # redacted output
    model_used = Column(String, default="")
    tokens_used = Column(Integer, default=0)
    quality_score = Column(Float, nullable=True)  # 1-5 user rating
    is_approved = Column(Boolean, default=False)  # human approved for training
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", backref="flywheel_traces")
    user = relationship("User", backref="flywheel_traces")


class FlywheelContextCard(Base):
    """Context cards generated from clustered traces."""
    __tablename__ = "flywheel_context_cards"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    title = Column(String, nullable=False)
    pattern_description = Column(Text, default="")
    trace_ids = Column(JSON, default=list)  # IDs of source traces
    frequency = Column(Integer, default=1)
    avg_quality = Column(Float, default=0.0)
    status = Column(String, default="draft")  # draft, reviewed, approved
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", backref="flywheel_context_cards")


class FlywheelEvalCase(Base):
    """Eval cases for testing AI quality — input/expected/actual."""
    __tablename__ = "flywheel_eval_cases"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    context_card_id = Column(Integer, ForeignKey("flywheel_context_cards.id"), nullable=True)
    input_text = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=False)
    actual_output = Column(Text, nullable=True)
    pass_fail = Column(String, nullable=True)  # pass, fail, untested
    model_tested = Column(String, default="")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", backref="flywheel_eval_cases")
    context_card = relationship("FlywheelContextCard", backref="eval_cases")


# ---------------------------------------------------------------------------
# Permissions Protocol — allow/require-approval/never-allowed
# ---------------------------------------------------------------------------

class PermissionRule(Base):
    """Permission rules for agent operations — security enforcement."""
    __tablename__ = "permission_rules"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    action_pattern = Column(String, nullable=False)  # regex or exact action name
    permission_level = Column(String, nullable=False)  # allow, require_approval, never
    category = Column(String, default="general")  # git, deploy, file, network, memory, admin
    description = Column(Text, default="")
    requires_mfa = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", backref="permission_rules")


class PermissionAudit(Base):
    """Audit log for every permission check — full traceability."""
    __tablename__ = "permission_audits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    action = Column(String, nullable=False)
    permission_level = Column(String, nullable=False)  # allow, require_approval, never
    result = Column(String, nullable=False)  # granted, denied, pending_approval
    rule_id = Column(Integer, ForeignKey("permission_rules.id"), nullable=True)
    approval_status = Column(String, nullable=True)  # pending, approved, rejected
    approved_by = Column(String, nullable=True)
    reason = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="permission_audits")
    project = relationship("Project", backref="permission_audits")


# ---------------------------------------------------------------------------
# Transfer & Onboarding
# ---------------------------------------------------------------------------

class TransferBundle(Base):
    """Brain state export/import bundles for project transfer."""
    __tablename__ = "transfer_bundles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    source_project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    target_project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    bundle_type = Column(String, default="full")  # full, memory_only, skills_only, lessons_only
    direction = Column(String, nullable=False)  # export, import
    status = Column(String, default="pending")  # pending, processing, completed, failed
    lessons_count = Column(Integer, default=0)
    decisions_count = Column(Integer, default=0)
    episodes_count = Column(Integer, default=0)
    skills_count = Column(Integer, default=0)
    preferences_included = Column(Boolean, default=False)
    checksum = Column(String, nullable=True)  # SHA-256 of bundle content
    bundle_data = Column(JSON, default=dict)  # serialized bundle
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="transfer_bundles")
    source_project = relationship("Project", foreign_keys=[source_project_id], backref="export_bundles")
    target_project = relationship("Project", foreign_keys=[target_project_id], backref="import_bundles")


class OnboardingResponse(Base):
    """User onboarding wizard responses — preferences + feature toggles."""
    __tablename__ = "onboarding_responses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    question_key = Column(String, nullable=False)  # code_style, workflow, constraints, etc.
    answer = Column(JSON, default=dict)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="onboarding_responses")
    project = relationship("Project", backref="onboarding_responses")
