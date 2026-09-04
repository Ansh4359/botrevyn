from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, case
import os

from app.db.session import get_db
from app.db.models import User, ReviewRecord
from app.api.auth import get_current_user

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

    # ── Core stats ──
    total_reviews = db.query(ReviewRecord).count()
    successful_reviews = (
        db.query(ReviewRecord).filter(ReviewRecord.status == "success").count()
    )
    failed_reviews = (
        db.query(ReviewRecord).filter(ReviewRecord.status == "error").count()
    )

    # ── Findings stats ──
    total_findings = (
        db.query(func.coalesce(func.sum(ReviewRecord.findings_count), 0)).scalar()
    )

    # ── Verdict breakdown ──
    approve_count = (
        db.query(ReviewRecord)
        .filter(ReviewRecord.verdict == "APPROVE")
        .count()
    )
    changes_count = (
        db.query(ReviewRecord)
        .filter(ReviewRecord.verdict == "REQUEST_CHANGES")
        .count()
    )
    comment_count = (
        db.query(ReviewRecord)
        .filter(ReviewRecord.verdict == "COMMENT")
        .count()
    )

    # ── Performance stats ──
    avg_duration = (
        db.query(func.avg(ReviewRecord.duration_seconds))
        .filter(ReviewRecord.status == "success")
        .scalar()
    ) or 0.0

    # ── Unique repos ──
    repos_monitored = (
        db.query(func.count(func.distinct(ReviewRecord.repo_full_name))).scalar()
    )

    # ── Recent reviews (last 30) ──
    recent_reviews = (
        db.query(ReviewRecord)
        .order_by(ReviewRecord.created_at.desc())
        .limit(30)
        .all()
    )

    # ── Per-repo breakdown ──
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
