import logging
import time
from typing import Any, Optional
import github
from github.GithubException import RateLimitExceededException, GithubException
from app.config import get_settings

logger = logging.getLogger(__name__)

class GitHubClientManager:
    def __init__(self, auth: github.Auth.Auth):
        self.client = github.Github(auth=auth)
        
    def _execute_with_retry(self, func: Any, *args, **kwargs) -> Any:
        max_retries = 3
        backoff = 2
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except RateLimitExceededException:
                logger.warning("Rate limit exceeded")
                if attempt == max_retries - 1:
                    raise
                time.sleep(backoff ** attempt)
            except GithubException as e:
                if e.status >= 500:
                    logger.warning(f"Transient error: {e}")
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(backoff ** attempt)
                else:
                    raise

    def get_repo(self, full_name: str):
        return self._execute_with_retry(self.client.get_repo, full_name)
        
    def get_pull_request(self, repo_full_name: str, pr_number: int):
        repo = self.get_repo(repo_full_name)
        return self._execute_with_retry(repo.get_pull, pr_number)


def get_github_client(installation_id: Optional[int] = None) -> GitHubClientManager:
    """
    Get a GitHub client, using App installation auth if available,
    otherwise falling back to a PAT.
    """
    settings = get_settings()
    
    if settings.github_app_id and settings.github_private_key and installation_id:
        private_key = settings.github_private_key.replace("\\n", "\n")
        
        # Ensure we have valid integers for app_id
        try:
            app_id = int(settings.github_app_id)
        except ValueError:
            logger.error("GITHUB_APP_ID is not a valid integer")
            raise ValueError("GITHUB_APP_ID must be an integer")
            
        app_auth = github.Auth.AppAuth(app_id, private_key)
        inst_auth = app_auth.get_installation_auth(installation_id)
        return GitHubClientManager(inst_auth)
        
    elif settings.github_token:
        # Fallback to PAT
        auth = github.Auth.Token(settings.github_token)
        return GitHubClientManager(auth)
    else:
        raise ValueError("Neither App Auth nor Token Auth is configured properly.")
