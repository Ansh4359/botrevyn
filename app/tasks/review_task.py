import logging
import time
from datetime import datetime, timezone
from typing import Optional
from celery import shared_task

from app.config import get_settings
from app.github_client.pr_fetcher import PRFetcher
from app.github_client.commenter import PRCommenter
from app.github_client.pr_creator import PRCreator
from app.agents.graph import run_review
from app.vectordb.indexer import CodebaseIndexer
from app.tasks import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def review_pull_request(self, repo_full_name: str, pr_number: int, action: str, installation_id: Optional[int] = None):
    """Main Celery task that orchestrates the full PR review pipeline."""
    logger.info(f"Starting review for PR {repo_full_name}#{pr_number}, action: {action}")
    start_time = time.time()
    settings = get_settings()

    try:
        # 1. Fetch full PR context
        pr_fetcher = PRFetcher(installation_id)
        pr_context = pr_fetcher.fetch_pr_context(repo_full_name, pr_number)

        # 2. Update vector DB index (best-effort)
        try:
            indexer = CodebaseIndexer(
                collection_name=repo_full_name.replace("/", "_"),
                persist_directory=settings.chromadb_path,
            )
            indexer.update_from_pr(pr_context)
        except Exception as e:
            logger.warning(f"Failed to update vector DB index: {e}")

        # 3. Run the multi-agent review workflow
        review_result = run_review(pr_context)

        # 4. Patch in metadata the graph doesn't know about
        duration = time.time() - start_time
        review_result.pr_number = pr_number
        review_result.repo_full_name = repo_full_name
        review_result.reviewed_at = datetime.now(timezone.utc)
        review_result.review_duration_seconds = duration

        # 5. Post review comment to GitHub
        commenter = PRCommenter(installation_id)
        commenter.post_review(repo_full_name, pr_number, review_result)

        # 6. Optionally create auto-fix PR
        if settings.auto_fix_enabled and review_result.fix_suggestions:
            if not settings.auto_fix_require_approval:
                pr_creator = PRCreator(installation_id)
                pr_creator.create_fix_pr(
                    repo_full_name, pr_number, review_result.fix_suggestions
                )

        # 7. Record to DB
        from app.db.session import SessionLocal
        from app.db.models import ReviewRecord
        
        db = SessionLocal()
        try:
            record = ReviewRecord(
                repo_full_name=repo_full_name,
                pr_number=pr_number,
                installation_id=installation_id or 0,
                status="success",
                findings_count=len(review_result.findings),
                verdict=review_result.overall_verdict,
                duration_seconds=duration,
            )
            db.add(record)
            db.commit()
        finally:
            db.close()

        logger.info(f"Completed review for PR {repo_full_name}#{pr_number} in {duration:.2f}s")
        return {"status": "success", "duration": duration, "findings": len(review_result.findings)}

    except Exception as e:
        logger.error(f"Error during review of PR {repo_full_name}#{pr_number}: {e}")
        try:
            commenter = PRCommenter(installation_id)
            commenter.post_error_comment(
                repo_full_name, pr_number,
                f"⚠️ An error occurred during AI code review: {str(e)}"
            )
        except Exception as inner_e:
            logger.error(f"Failed to post error comment: {inner_e}")
            
        from app.db.session import SessionLocal
        from app.db.models import ReviewRecord
        db = SessionLocal()
        try:
            record = ReviewRecord(
                repo_full_name=repo_full_name,
                pr_number=pr_number,
                installation_id=installation_id or 0,
                status="error",
                error_message=str(e),
                duration_seconds=time.time() - start_time,
            )
            db.add(record)
            db.commit()
        except Exception:
            pass
        finally:
            db.close()
            
        raise self.retry(exc=e)
