from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from .webhook_payload import GitHubUser

class FileDiff(BaseModel):
    filename: str
    status: str
    additions: int
    deletions: int
    patch: Optional[str] = None
    previous_filename: Optional[str] = None

class FileContent(BaseModel):
    path: str
    content: str
    language: str
    size: int

class PRContext(BaseModel):
    repo_full_name: str
    pr_number: int
    title: str
    body: Optional[str] = None
    author: GitHubUser
    base_branch: str
    head_branch: str
    head_sha: str
    diff_files: List[FileDiff]
    file_contents: List[FileContent]
    labels: List[str] = []
    created_at: datetime
    
    @property
    def added_files(self) -> List[FileDiff]:
        return [f for f in self.diff_files if f.status == "added"]
        
    @property
    def modified_files(self) -> List[FileDiff]:
        return [f for f in self.diff_files if f.status == "modified"]
        
    @property
    def deleted_files(self) -> List[FileDiff]:
        return [f for f in self.diff_files if f.status == "removed"]
        
    @property
    def all_changed_paths(self) -> List[str]:
        return [f.filename for f in self.diff_files]
        
    def get_file_content(self, path: str) -> Optional[FileContent]:
        for f in self.file_contents:
            if f.path == path:
                return f
        return None
        
    def get_diff_for_file(self, path: str) -> Optional[FileDiff]:
        for f in self.diff_files:
            if f.filename == path:
                return f
        return None
