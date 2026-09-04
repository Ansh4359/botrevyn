import logging
from typing import Optional, List
from app.github_client.client import get_github_client
from app.models.review import FixSuggestion

logger = logging.getLogger(__name__)


class PRCreator:
    """Creates auto-fix pull requests from FixSuggestion objects."""

    def __init__(self, installation_id: Optional[int] = None):
        self.github_client = get_github_client(installation_id)

    def _apply_fix(self, repo, branch: str, fix: FixSuggestion) -> bool:
        """Apply a single fix by replacing original_code with fixed_code in the file."""
        try:
            content_file = repo.get_contents(fix.file_path, ref=branch)
            if isinstance(content_file, list):
                logger.warning(f"Skipping directory: {fix.file_path}")
                return False

            original_content = content_file.decoded_content.decode("utf-8")

            if fix.original_code and fix.original_code in original_content:
                new_content = original_content.replace(fix.original_code, fix.fixed_code, 1)
            else:
                # Fallback: just use fixed_code as the full content
                new_content = fix.fixed_code

            repo.update_file(
                path=fix.file_path,
                message=f"fix: {fix.description}",
                content=new_content,
                sha=content_file.sha,
                branch=branch,
            )
            return True
        except Exception as e:
            logger.error(f"Error applying fix to {fix.file_path}: {e}")
        return False

    def create_fix_pr(
        self,
        repo_full_name: str,
        original_pr_number: int,
        fixes: List[FixSuggestion],
    ) -> Optional[int]:
        """Create a new PR with auto-generated fixes targeting the original PR's branch."""
        try:
            repo = self.github_client.get_repo(repo_full_name)
            original_pr = repo.get_pull(original_pr_number)

            branch_name = f"ai-fix/{original_pr_number}"
            base_sha = repo.get_branch(original_pr.head.ref).commit.sha

            # Create branch if it doesn't exist
            try:
                repo.get_git_ref(f"heads/{branch_name}")
            except Exception:
                repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)

            success_count = 0
            applied_fixes: list[str] = []
            for fix in fixes:
                if self._apply_fix(repo, branch_name, fix):
                    success_count += 1
                    applied_fixes.append(fix.description)

            if success_count > 0:
                body_lines = [
                    f"🤖 **AI-generated fixes** for #{original_pr_number}\n",
                    f"Applied **{success_count}** fix(es):\n",
                ]
                for desc in applied_fixes:
                    body_lines.append(f"- {desc}")
                body_lines.append(
                    f"\n---\n*This PR was automatically created by the AI Code Reviewer.*"
                )

                new_pr = repo.create_pull(
                    title=f"🔧 AI Fixes for #{original_pr_number}",
                    body="\n".join(body_lines),
                    head=branch_name,
                    base=original_pr.head.ref,
                )
                logger.info(f"Created fix PR #{new_pr.number} for #{original_pr_number}")
                return new_pr.number

            logger.warning(f"No fixes were successfully applied for PR #{original_pr_number}")
            return None
        except Exception as e:
            logger.error(f"Error creating fix PR for #{original_pr_number}: {e}")
            return None
