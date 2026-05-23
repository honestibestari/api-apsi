"""Koneksi database & session SQLAlchemy.

URL database diambil dari konfigurasi (.env). Secara default memakai SQLite
lokal, tetapi bisa diganti ke Postgres/MySQL hanya dengan mengubah DATABASE_URL.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# check_same_thread hanya relevan untuk SQLite (FastAPI memakai banyak thread).
connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(settings.database_url, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency FastAPI: buka session per-request, lalu pastikan ditutup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
