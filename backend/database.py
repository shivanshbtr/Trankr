"""
database.py — SQLAlchemy engine + session factory
Reads DATABASE_URL from the environment (set this on your host, e.g. Render,
to your Postgres connection string). Falls back to a local SQLite file when
DATABASE_URL isn't set, so local dev with `uvicorn main:app --reload` still
works with zero setup.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./trankr.db"

# Render/Heroku-style URLs sometimes start with "postgres://"; SQLAlchemy 2.x
# requires the "postgresql://" scheme.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,   # test each connection before use; transparently
                           # reconnects if the DB (e.g. Neon after a suspend)
                           # silently dropped it, instead of raising an error
    pool_recycle=300,     # also proactively recycle connections older than
                           # 5 min, so idle ones don't get a chance to go
                           # stale between requests
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
