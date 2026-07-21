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
