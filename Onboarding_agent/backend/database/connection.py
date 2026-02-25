from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from pathlib import Path
from backend.config import settings
from backend.database.models import Base


def _resolve_database_url(database_url: str) -> str:
    """Resolve relative sqlite URLs to a stable absolute DB file path."""
    url = str(database_url or "").strip()
    if not url.startswith("sqlite"):
        return url

    app_root = Path(__file__).resolve().parents[2]

    if url.startswith("sqlite:///./"):
        relative_part = url[len("sqlite:///./"):]
        absolute_path = (app_root / relative_part).resolve()
        return f"sqlite:///{absolute_path.as_posix()}"

    if url.startswith("sqlite:///"):
        raw_path = url[len("sqlite:///"):]
        is_windows_abs = len(raw_path) > 1 and raw_path[1] == ":"
        is_posix_abs = raw_path.startswith("/")
        if not is_windows_abs and not is_posix_abs:
            absolute_path = (app_root / raw_path).resolve()
            return f"sqlite:///{absolute_path.as_posix()}"

    return url


engine = create_engine(
    _resolve_database_url(settings.DATABASE_URL),
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
