import hmac
import hashlib
import json
import time
import logging
from fastapi import APIRouter, Header, Request, HTTPException, status, Response, BackgroundTasks
from typing import Optional
from app.config import get_settings
from app.models.webhook_payload import WebhookPayload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["Webhooks"])

DELIVERY_CACHE: dict[str, float] = {}
DELIVERY_TTL = 3600  # 1 hour


def is_duplicate_delivery(delivery_id: str) -> bool:
    now = time.time()
    if delivery_id in DELIVERY_CACHE:
        if now - DELIVERY_CACHE[delivery_id] < DELIVERY_TTL:
            return True
        else:
            del DELIVERY_CACHE[delivery_id]

    # Cleanup expired entries
    if len(DELIVERY_CACHE) > 1000:
        keys_to_delete = [k for k, v in DELIVERY_CACHE.items() if now - v > DELIVERY_TTL]
        for k in keys_to_delete:
            del DELIVERY_CACHE[k]

    DELIVERY_CACHE[delivery_id] = now
    return False


def run_review_sync(repo_full_name: str, pr_number: int, action: str, installation_id: Optional[int] = None):
    """Run the review synchronously as a FastAPI background task (fallback when Celery is unavailable)."""
    try:
        from app.github_client.pr_fetcher import PRFetcher
        from app.github_client.commenter import PRCommenter
        from app.github_client.pr_creator import PRCreator
        from app.agents.graph import run_review
        from app.vectordb.indexer import CodebaseIndexer
        from datetime import datetime, timezone

        logger.info(f"[SYNC] Starting review for {repo_full_name}#{pr_number}")
        start_time = time.time()
        settings = get_settings()

        # 1. Fetch PR context
        pr_fetcher = PRFetcher(installation_id)
        pr_context = pr_fetcher.fetch_pr_context(repo_full_name, pr_number)
        logger.info(f"[SYNC] Fetched PR context: {len(pr_context.diff_files)} files changed")

        # 2. Update vector DB (best-effort)
        try:
            indexer = CodebaseIndexer(
                collection_name=repo_full_name.replace("/", "_"),
                persist_directory=settings.chromadb_path,
            )
            indexer.update_from_pr(pr_context)
        except Exception as e:
            logger.warning(f"[SYNC] Vector DB update skipped: {e}")

        # 3. Run agent pipeline
        review_result = run_review(pr_context)
        duration = time.time() - start_time
        review_result.pr_number = pr_number
        review_result.repo_full_name = repo_full_name
        review_result.reviewed_at = datetime.now(timezone.utc)
        review_result.review_duration_seconds = duration
        logger.info(f"[SYNC] Review done: {len(review_result.findings)} findings in {duration:.1f}s")

        # 4. Post review
        commenter = PRCommenter(installation_id)
        commenter.post_review(repo_full_name, pr_number, review_result)
        logger.info(f"[SYNC] Review posted to PR #{pr_number}")

        # 5. Auto-fix
        if settings.auto_fix_enabled and review_result.fix_suggestions:
            if not settings.auto_fix_require_approval:
                pr_creator = PRCreator(installation_id)
                new_pr = pr_creator.create_fix_pr(
                    repo_full_name, pr_number, review_result.fix_suggestions
                )
                logger.info(f"[SYNC] Fix PR created: #{new_pr}")

    except Exception as e:
        logger.error(f"[SYNC] Review failed for {repo_full_name}#{pr_number}: {e}", exc_info=True)
        # Try to post error to PR
        try:
            from app.github_client.commenter import PRCommenter
            commenter = PRCommenter(installation_id)
            commenter.post_error_comment(
                repo_full_name, pr_number,
                f"⚠️ AI Code Review failed:\n```\n{str(e)}\n```"
            )
        except Exception as inner:
            logger.error(f"[SYNC] Could not post error comment: {inner}")


@router.post("")
async def github_webhook(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(...),
    x_github_delivery: str = Header(...),
    x_hub_signature_256: str = Header(None),
):
    settings = get_settings()

    if is_duplicate_delivery(x_github_delivery):
        logger.info(f"Duplicate delivery: {x_github_delivery}")
        return {"message": "Duplicate delivery"}

    body = await request.body()

    if settings.github_webhook_secret:
        if not x_hub_signature_256:
            raise HTTPException(status_code=400, detail="Missing signature")

        signature = f"sha256={hmac.new(settings.github_webhook_secret.encode(), body, hashlib.sha256).hexdigest()}"
        if not hmac.compare_digest(signature, x_hub_signature_256):
            raise HTTPException(status_code=400, detail="Invalid signature")

    if x_github_event != "pull_request":
        logger.info(f"Ignored event: {x_github_event}")
        return {"message": "Ignored event type"}

    try:
        payload_dict = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    action = payload_dict.get("action")
    if action not in ("opened", "synchronize", "reopened"):
        logger.info(f"Ignored action: {action}")
        return {"message": f"Ignored action {action}"}

    repo_full_name = payload_dict.get("repository", {}).get("full_name", "")
    pr_number = payload_dict.get("number", 0)
    installation_id = payload_dict.get("installation", {}).get("id")
    
    # Auto-resolve installation_id from App credentials if not in payload
    if not installation_id and settings.github_app_id and settings.github_private_key and "/" in repo_full_name:
        try:
            import github
            pk = settings.github_private_key.replace("\\n", "\n")
            integration = github.GithubIntegration(int(settings.github_app_id), pk)
            owner, repo_name = repo_full_name.split("/")
            inst = integration.get_repo_installation(owner, repo_name)
            installation_id = inst.id
            logger.info(f"Auto-resolved installation_id {installation_id} for {repo_full_name}")
        except Exception as e:
            logger.warning(f"Could not auto-resolve installation for {repo_full_name}: {e}")

    logger.info(f"Processing PR: {repo_full_name}#{pr_number} (action={action}, install_id={installation_id})")

    # Try Celery first, fall back to sync background task
    try:
        from app.tasks.review_task import review_pull_request
        review_pull_request.delay(repo_full_name, pr_number, action, installation_id)
        logger.info(f"Queued to Celery: {repo_full_name}#{pr_number}")
    except Exception as e:
        logger.warning(f"Celery unavailable ({e}), running sync background task")
        background_tasks.add_task(run_review_sync, repo_full_name, pr_number, action, installation_id)

    response.status_code = status.HTTP_202_ACCEPTED
    return {"message": "Accepted for processing", "repo": repo_full_name, "pr": pr_number}
