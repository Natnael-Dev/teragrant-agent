"""
Database Connection and Session Engine for TeraGrant Persistence Layer.
Implements SQLAlchemy with SQLite (teragrant.db) and strictly enforces
foreign key constraints via PRAGMA foreign_keys=ON.
"""

from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Default SQLite connection URI
DEFAULT_DATABASE_URL = "sqlite:///./teragrant.db"

# Engine configuration with connect_args for SQLite thread safety
engine = create_engine(
    DEFAULT_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Ensures SQLite foreign key constraints and cascade deletions
    are strictly enforced for every active connection.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Base model class for all SQLAlchemy declarative ORM models
Base = declarative_base()

# Session factory for generating database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(target_engine=None) -> None:
    """
    Initializes and creates all registered ORM tables.
    Accepts an optional target_engine for in-memory testing.
    """
    # Import models to ensure they are registered with Base.metadata
    from app import models  # noqa: F401

    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session per request
    and ensures clean session teardown.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
