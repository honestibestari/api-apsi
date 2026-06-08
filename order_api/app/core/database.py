"""Koneksi database & session SQLAlchemy.

URL database diambil dari konfigurasi (.env). Secara default memakai SQLite
lokal, tetapi bisa diganti ke Postgres/MySQL hanya dengan mengubah DATABASE_URL.
"""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.schema import CreateColumn

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


def reset_schema():
    """DROP semua tabel + tipe enum, lalu biarkan create_all() membangun ulang.

    Dipakai sekali untuk membereskan drift skema yang tidak bisa diperbaiki
    secara additive (mis. nilai tipe enum yang berbeda). DESTRUKTIF: semua data
    hilang. Hanya jalan jika settings.reset_db == True.
    """
    print("[reset_schema] DROP semua tabel & tipe enum (RESET_DB aktif)...")
    Base.metadata.drop_all(bind=engine)

    # drop_all tidak selalu menghapus tipe ENUM native Postgres. Hapus eksplisit
    # agar create_all bisa membuat ulang sesuai definisi model terbaru.
    if engine.dialect.name == "postgresql":
        enum_names = {
            col.type.name
            for table in Base.metadata.tables.values()
            for col in table.columns
            if isinstance(col.type, SAEnum) and col.type.name
        }
        with engine.begin() as conn:
            for enum_name in enum_names:
                conn.execute(text(f'DROP TYPE IF EXISTS "{enum_name}" CASCADE'))
                print(f"[reset_schema] dropped enum type {enum_name}")


def sync_columns():
    """Auto-migrasi ringan tanpa alembic.

    `Base.metadata.create_all()` hanya membuat tabel yang belum ada; ia TIDAK
    menambahkan kolom baru ke tabel yang sudah terlanjur dibuat di deploy
    sebelumnya. Fungsi ini membandingkan kolom pada model dengan kolom yang ada
    di database, lalu menjalankan `ALTER TABLE ... ADD COLUMN` untuk yang kurang.

    Aman dijalankan berulang kali: kolom yang sudah ada dilewati. Cukup untuk
    perubahan additive (menambah kolom). Untuk rename/drop/ubah tipe tetap perlu
    SQL manual.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            # Tabel yang benar-benar baru sudah ditangani create_all().
            if table.name not in existing_tables:
                continue

            existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_cols:
                    continue
                col_ddl = CreateColumn(column).compile(dialect=engine.dialect)
                conn.execute(
                    text(f'ALTER TABLE "{table.name}" ADD COLUMN {col_ddl}')
                )
                print(f"[sync_columns] added {table.name}.{column.name}")
