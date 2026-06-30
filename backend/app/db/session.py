"""
Database engine and session management.
"""
from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def _build_engine():
    """Create the appropriate SQLAlchemy engine.

    When ``TURSO_DATABASE_URL`` is set the engine is wired through the
    pure-Python Turso HTTP DBAPI adapter so no native compilation is
    needed.  Otherwise the default local SQLite driver is used.
    """
    if settings.TURSO_DATABASE_URL and settings.TURSO_AUTH_TOKEN:
        # Convert libsql:// URL to HTTPS for the HTTP Pipeline API
        http_url = settings.TURSO_DATABASE_URL
        if http_url.startswith("libsql://"):
            http_url = http_url.replace("libsql://", "https://", 1)

        from app.db import turso  # local pure-Python DBAPI module

        def _creator():
            return turso.connect(
                http_url=http_url,
                auth_token=settings.TURSO_AUTH_TOKEN,
            )

        return create_engine(
            "sqlite://",  # dialect only; the connection is created by _creator
            creator=_creator,
            poolclass=pool.StaticPool,
            echo=False,
        )

    # Local SQLite fallback
    connect_args = {}
    if settings.DATABASE_URL.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    return create_engine(
        settings.DATABASE_URL,
        connect_args=connect_args,
        echo=False,
    )


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
