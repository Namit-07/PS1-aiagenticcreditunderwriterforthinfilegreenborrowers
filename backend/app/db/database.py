"""SQLAlchemy database engine and session management (Team A)."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()


def _make_engine(url: str):
    if url.startswith("sqlite"):
        if ":memory:" not in url:
            db_path = url.replace("sqlite:///", "").split("?")[0]
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        eng = create_engine(url, connect_args={"check_same_thread": False})

        # SQLite ignores foreign keys unless asked; enforce them so local runs and the
        # test suite behave like Postgres (which rejects out-of-order child inserts).
        @event.listens_for(eng, "connect")
        def _enable_sqlite_fks(dbapi_connection, _record):  # pragma: no cover - trivial
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return eng
    return create_engine(url, pool_pre_ping=True)


engine = _make_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def init_db() -> None:
    """Create all tables (idempotent). Alembic owns real migrations in prod."""
    import app.models  # noqa: F401  (registers every model on Base.metadata)

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
