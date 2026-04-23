from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class RepoBase(BaseModel):
    owner: str
    repo_name: str
    default_branch: str = "main"


class RepoCreate(RepoBase):
    pass


class RepoOut(RepoBase):
    id: int
    project_id: int
    ci_status: str
    coverage_percent: float
    last_synced: Optional[datetime]

    class Config:
        from_attributes = True


class ProjectBase(BaseModel):
    name: str
    description: str = ""
    team: str = ""
    current_stage: str = "ask"


class ProjectCreate(ProjectBase):
    repos: list[RepoCreate] = []


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    team: Optional[str] = None
    status: Optional[str] = None
    current_stage: Optional[str] = None
    completion_percent: Optional[float] = None
    token_savings: Optional[float] = None
    risk_alerts: Optional[int] = None


class ProjectOut(ProjectBase):
    id: int
    status: str
    completion_percent: float
    token_savings: float
    risk_alerts: int
    created_at: datetime
    updated_at: datetime
    repos: list[RepoOut] = []

    class Config:
        from_attributes = True


class SettingBase(BaseModel):
    key: str
    value: str
    setting_type: str = "text"
    label: str = ""
    description: str = ""
    options: str = ""


class SettingUpdate(BaseModel):
    value: str


class SettingOut(SettingBase):
    id: int

    class Config:
        from_attributes = True


class GitHubRepoInfo(BaseModel):
    full_name: str
    name: str
    owner: str
    description: Optional[str]
    language: Optional[str]
    stars: int
    forks: int
    open_issues: int
    default_branch: str
    updated_at: str
    html_url: str
    private: bool


class GitHubPR(BaseModel):
    number: int
    title: str
    state: str
    author: str
    created_at: str
    updated_at: str
    merged_at: Optional[str]
    additions: int
    deletions: int
    changed_files: int
    html_url: str
    head_branch: str
    base_branch: str
    body: Optional[str]


class GitHubPRFile(BaseModel):
    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    patch: Optional[str]


class GitHubCommit(BaseModel):
    sha: str
    message: str
    author: str
    date: str
    html_url: str
    additions: int
    deletions: int
    files_changed: int


class GitHubWorkflowRun(BaseModel):
    id: int
    name: str
    status: str
    conclusion: Optional[str]
    head_branch: str
    event: str
    created_at: str
    updated_at: str
    html_url: str


class AnalyticsOverview(BaseModel):
    total_projects: int
    active_projects: int
    completed_projects: int
    avg_completion: float
    avg_token_savings: float
    total_risk_alerts: int
    total_repos: int
    stage_distribution: dict[str, int]
