import time
import logging
from fastapi import APIRouter
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["Health"])

START_TIME = time.time()

@router.get("")
async def get_health():
    uptime = time.time() - START_TIME
    return {"status": "ok", "version": "1.0.0", "uptime": uptime}

@router.get("/ready")
async def get_ready():
    settings = get_settings()
    ready = True
    
    # Check Redis
    try:
        import redis
        if settings.redis_url:
            r = redis.Redis.from_url(settings.redis_url)
            r.ping()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        ready = False
        
    # Check ChromaDB
    try:
        import chromadb
        if settings.chroma_host and settings.chroma_port:
            client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
            client.heartbeat()
    except Exception as e:
        logger.error(f"ChromaDB health check failed: {e}")
        ready = False

    if ready:
        return {"status": "ready"}
    return {"status": "not ready"}
