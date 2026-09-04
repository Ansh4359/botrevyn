import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import health_router, webhooks_router
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.db.session import engine, Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up AI Code Reviewer...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")
    yield
    logger.info("Shutting down AI Code Reviewer...")

app = FastAPI(
    title="AI Code Reviewer",
    description="Multi-agent code review system",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"message": "Internal server error"})

app.include_router(health_router)
app.include_router(webhooks_router)
app.include_router(auth_router)
app.include_router(dashboard_router)
