from fastapi import APIRouter, HTTPException
from github import GithubException
from app import github_service
from app.schemas import (
    GitHubRepoInfo, GitHubPR, GitHubPRFile,
    GitHubCommit, GitHubWorkflowRun,
)

router = APIRouter(prefix="/api/github", tags=["github"])


@router.get("/repos/{owner}", response_model=list[GitHubRepoInfo])
def list_repos(owner: str, limit: int = 30):
    try:
        return github_service.list_org_repos(owner, limit)
    except GithubException as e:
        raise HTTPException(status_code=e.status, detail=str(e.data))


@router.get("/repos/{owner}/{repo}", response_model=GitHubRepoInfo)
def get_repo(owner: str, repo: str):
    try:
        return github_service.get_repo_info(owner, repo)
    except GithubException as e:
        raise HTTPException(status_code=e.status, detail=str(e.data))


@router.get("/repos/{owner}/{repo}/pulls", response_model=list[GitHubPR])
def list_pulls(owner: str, repo: str, state: str = "all", limit: int = 20):
    try:
        return github_service.list_pulls(owner, repo, state, limit)
    except GithubException as e:
        raise HTTPException(status_code=e.status, detail=str(e.data))


@router.get("/repos/{owner}/{repo}/pulls/{number}", response_model=GitHubPR)
def get_pull(owner: str, repo: str, number: int):
    try:
        return github_service.get_pull(owner, repo, number)
    except GithubException as e:
        raise HTTPException(status_code=e.status, detail=str(e.data))


@router.get("/repos/{owner}/{repo}/pulls/{number}/files", response_model=list[GitHubPRFile])
def get_pull_files(owner: str, repo: str, number: int):
    try:
        return github_service.get_pull_files(owner, repo, number)
    except GithubException as e:
        raise HTTPException(status_code=e.status, detail=str(e.data))


@router.get("/repos/{owner}/{repo}/commits", response_model=list[GitHubCommit])
def list_commits(owner: str, repo: str, limit: int = 20):
    try:
        return github_service.list_commits(owner, repo, limit)
    except GithubException as e:
        raise HTTPException(status_code=e.status, detail=str(e.data))


@router.get("/repos/{owner}/{repo}/actions/runs", response_model=list[GitHubWorkflowRun])
def list_workflow_runs(owner: str, repo: str, limit: int = 10):
    try:
        return github_service.list_workflow_runs(owner, repo, limit)
    except GithubException as e:
        raise HTTPException(status_code=e.status, detail=str(e.data))
