from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class GitHubUser(BaseModel):
    login: str
    id: int
    avatar_url: str

class Repository(BaseModel):
    id: int
    full_name: str
    name: str
    owner: GitHubUser
    private: bool
    default_branch: str
    clone_url: str

class PullRequestHead(BaseModel):
    ref: str
    sha: str
    repo: Repository

class PullRequest(BaseModel):
    number: int
    title: str
    body: Optional[str] = None
    state: str
    user: GitHubUser
    head: PullRequestHead
    base: PullRequestHead
    diff_url: str
    html_url: str
    created_at: datetime
    updated_at: datetime
    merged: Optional[bool] = False
    additions: Optional[int] = 0
    deletions: Optional[int] = 0
    changed_files: Optional[int] = 0

class WebhookPayload(BaseModel):
    action: str
    number: Optional[int] = None
    pull_request: Optional[PullRequest] = None
    repository: Repository
    sender: GitHubUser
    installation: Optional[Dict[str, Any]] = None
