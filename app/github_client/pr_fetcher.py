import httpx
import logging
from datetime import datetime
from typing import List, Dict, Optional
from unidiff import PatchSet
from app.github_client.client import get_github_client
from app.models.pr_context import PRContext, FileDiff, FileContent
from app.models.webhook_payload import GitHubUser
from app.config import get_settings

logger = logging.getLogger(__name__)

class PRFetcher:
    def __init__(self, installation_id: Optional[int] = None):
        self.github_client = get_github_client(installation_id)
        self.settings = get_settings()
        self.installation_id = installation_id

    def _detect_language(self, filename: str) -> str:
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        lang_map = {
            "py": "python", "js": "javascript", "ts": "typescript",
            "java": "java", "go": "go", "rs": "rust", "rb": "ruby",
            "cpp": "cpp", "cc": "cpp", "c": "c", "cs": "csharp",
            "swift": "swift", "kt": "kotlin", "php": "php",
            "html": "html", "css": "css", "json": "json",
            "md": "markdown", "sh": "shell", "yaml": "yaml",
            "yml": "yaml", "sql": "sql", "tsx": "typescript",
            "jsx": "javascript", "scala": "scala", "r": "r",
            "dart": "dart", "lua": "lua", "zig": "zig",
        }
        return lang_map.get(ext, "unknown")

    def fetch_pr_context(self, repo_full_name: str, pr_number: int) -> PRContext:
        pr = self.github_client.get_pull_request(repo_full_name, pr_number)
        
        diff_url = pr.diff_url
        
        # If using app auth, we need to extract the token from the PyGithub Auth object
        token = self.settings.github_token
        if self.installation_id and hasattr(self.github_client.client._Github__requester.auth, 'token'):
            token = self.github_client.client._Github__requester.auth.token
            
        headers = {
            "Accept": "application/vnd.github.v3.diff",
            "Authorization": f"Bearer {token}"
        }
        response = httpx.get(diff_url, headers=headers, follow_redirects=True)
        response.raise_for_status()
        
        patch_set = PatchSet(response.text)
        
        file_diffs: List[FileDiff] = []
        file_contents: List[FileContent] = []
        
        for patched_file in patch_set:
            if patched_file.is_binary_file:
                continue
                
            status = "modified" if patched_file.is_modified_file else ("added" if patched_file.is_added_file else "deleted")
            file_diff = FileDiff(
                filename=patched_file.path,
                status=status,
                additions=patched_file.added,
                deletions=patched_file.removed,
                patch=str(patched_file),
            )
            file_diffs.append(file_diff)
            
            if not patched_file.is_removed_file:
                repo = self.github_client.get_repo(repo_full_name)
                try:
                    content_file = repo.get_contents(patched_file.path, ref=pr.head.sha)
                    if not isinstance(content_file, list):
                        content = content_file.decoded_content.decode("utf-8")
                        language = self._detect_language(patched_file.path)
                        file_contents.append(FileContent(
                            path=patched_file.path,
                            content=content,
                            language=language,
                            size=len(content),
                        ))
                except Exception as e:
                    logger.error(f"Error fetching content for {patched_file.path}: {e}")

        author = GitHubUser(
            login=pr.user.login,
            id=pr.user.id,
            avatar_url=pr.user.avatar_url or "",
        )

        return PRContext(
            pr_number=pr_number,
            repo_full_name=repo_full_name,
            title=pr.title,
            body=pr.body or "",
            author=author,
            base_branch=pr.base.ref,
            head_branch=pr.head.ref,
            head_sha=pr.head.sha,
            diff_files=file_diffs,
            file_contents=file_contents,
            labels=[label.name for label in pr.labels],
            created_at=pr.created_at or datetime.utcnow(),
        )

