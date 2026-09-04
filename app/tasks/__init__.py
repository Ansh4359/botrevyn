from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_code_reviewer",
    broker=settings.redis_url,
    backend=settings.redis_url
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue="celery",
)
celery_app.conf.include = ["app.tasks.review_task"]
