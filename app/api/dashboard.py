import logging
import os
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, case, or_

from app.db.session import get_db
from app.db.models import User, ReviewRecord, AppInstallation
from app.api.auth import get_current_user
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Dashboard"])

# Get absolute path for templates
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates_dir = os.path.join(BASE_DIR, "templates")
os.makedirs(templates_dir, exist_ok=True)

templates = Jinja2Templates(directory=templates_dir)


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, user: User = Depends(get_current_user)):
    if user:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse(request, "login.html")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user:
        return RedirectResponse(url="/")

    # ── Resolve user's installations ──
    user_installs = (
        db.query(AppInstallation)
        .filter(
            or_(
                AppInstallation.user_id == user.id,
                func.lower(AppInstallation.account_name) == user.username.lower(),
            )
        )
        .all()
    )
    user_installation_ids = [inst.installation_id for inst in user_installs]

    # Best-effort sync from GitHub App if no installations recorded in DB yet
    if not user_installation_ids:
        try:
            settings = get_settings()
            if settings.github_app_id and settings.github_private_key:
                import github
                pk = settings.github_private_key.replace("\\n", "\n")
                gi = github.GithubIntegration(int(settings.github_app_id), pk)
                for inst in gi.get_installations():
                    acc = inst.raw_data.get("account", {})
                    acc_login = acc.get("login", "")
                    if acc_login.lower() == user.username.lower():
                        existing = (
                            db.query(AppInstallation)
                            .filter(AppInstallation.installation_id == inst.id)
                            .first()
                        )
                        if existing:
                            existing.user_id = user.id
                            existing.account_name = acc_login
                        else:
                            db.add(
                                AppInstallation(
                                    installation_id=inst.id,
                                    target_id=acc.get("id", 0),
                                    target_type=acc.get("type", "User"),
                                    account_name=acc_login,
                                    user_id=user.id,
                                )
                            )
                        user_installation_ids.append(inst.id)
                db.commit()
        except Exception as e:
            logger.debug(f"Auto-sync installation for {user.username} failed: {e}")

    # ── User scoping filter ──
    # A review belongs to the logged-in user if:
    # 1. repo starts with user's username (e.g. 'Ansh4359/...')
    # 2. OR installation_id matches one of the user's App installations
    user_conditions = [
        func.lower(ReviewRecord.repo_full_name).like(f"{user.username.lower()}/%")
    ]
    if user_installation_ids:
        user_conditions.append(ReviewRecord.installation_id.in_(user_installation_ids))

    user_filter = or_(*user_conditions)

    # ── Scoped Queries ──
    user_reviews_query = db.query(ReviewRecord).filter(user_filter)

    total_reviews = user_reviews_query.count()
    successful_reviews = (
        user_reviews_query.filter(ReviewRecord.status == "success").count()
    )
    failed_reviews = (
        user_reviews_query.filter(ReviewRecord.status == "error").count()
    )

    # Scoped total findings
    total_findings = (
        db.query(func.coalesce(func.sum(ReviewRecord.findings_count), 0))
        .filter(user_filter)
        .scalar()
    )

    # Scoped verdicts
    approve_count = (
        user_reviews_query.filter(ReviewRecord.verdict == "APPROVE").count()
    )
    changes_count = (
        user_reviews_query.filter(ReviewRecord.verdict == "REQUEST_CHANGES").count()
    )
    comment_count = (
        user_reviews_query.filter(ReviewRecord.verdict == "COMMENT").count()
    )

    # Scoped average duration
    avg_duration = (
        db.query(func.avg(ReviewRecord.duration_seconds))
        .filter(user_filter, ReviewRecord.status == "success")
        .scalar()
    ) or 0.0

    # Scoped unique repositories
    repos_monitored = (
        db.query(func.count(func.distinct(ReviewRecord.repo_full_name)))
        .filter(user_filter)
        .scalar()
    )

    # Scoped recent reviews (last 30)
    recent_reviews = (
        user_reviews_query.order_by(ReviewRecord.created_at.desc())
        .limit(30)
        .all()
    )

    # Scoped per-repo breakdown
    repo_stats = (
        db.query(
            ReviewRecord.repo_full_name,
            func.count(ReviewRecord.id).label("review_count"),
            func.coalesce(func.sum(ReviewRecord.findings_count), 0).label(
                "total_findings"
            ),
            func.count(
                case(
                    (ReviewRecord.verdict == "REQUEST_CHANGES", 1),
                )
            ).label("changes_requested"),
        )
        .filter(user_filter)
        .group_by(ReviewRecord.repo_full_name)
        .all()
    )

    success_rate = (
        round(successful_reviews / total_reviews * 100) if total_reviews > 0 else 0
    )

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        context={
            "user": user,
            "recent_reviews": recent_reviews,
            "total_reviews": total_reviews,
            "successful_reviews": successful_reviews,
            "failed_reviews": failed_reviews,
            "total_findings": total_findings,
            "approve_count": approve_count,
            "changes_count": changes_count,
            "comment_count": comment_count,
            "avg_duration": round(avg_duration, 1),
            "repos_monitored": repos_monitored,
            "repo_stats": repo_stats,
            "success_rate": success_rate,
        },
    )
