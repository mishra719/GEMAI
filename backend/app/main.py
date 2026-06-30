"""
Gem-AI — FastAPI Application Entry Point
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from sqlalchemy import inspect, text

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine

# Import all models so they register with Base.metadata
from app.models.user import User
from app.models.chat import Chat
from app.models.message import Message

# Import routers
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.zip import router as zip_router

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def ensure_runtime_schema():
    """Add lightweight runtime columns needed by newer app features."""
    with engine.begin() as connection:
        inspector = inspect(connection)
        table_names = set(inspector.get_table_names())
        if "users" not in table_names:
            return

        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "reset_otp_hash" not in user_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN reset_otp_hash VARCHAR(255)"))
        if "reset_otp_expires_at" not in user_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN reset_otp_expires_at DATETIME"))


# ---------- Lifespan (replaces deprecated on_event) ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # Startup
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()
    logger.info(f"🚀 {settings.APP_NAME} is ready!")
    yield
    # Shutdown
    logger.info(f"👋 {settings.APP_NAME} shutting down...")


# ---------- App ----------
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered chatbot with OpenRouter chat, coding assistance, and image generation",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# ---------- Exception Handlers ----------

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler."""
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )


# ---------- Static Files ----------
static_dir = Path(__file__).resolve().parent.parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
(static_dir / "images").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ---------- Routers ----------
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(zip_router)


# ---------- Health Check ----------

@app.get("/api/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "1.0.0",
    }
