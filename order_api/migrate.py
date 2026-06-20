"""Migrasi skema database — idempotent & aman dijalankan berulang.

Menjalankan:
  1. create_all          → buat tabel yang belum ada
  2. sync_columns        → tambah kolom baru ke tabel lama (ALTER ADD COLUMN)
  3. apply_manual_migrations → migrasi non-additive (Postgres) yang sudah bersifat
                               IF EXISTS / kondisional → aman diulang

TIDAK melakukan seed dan TIDAK reset (DROP). Cocok dijalankan sebelum/sesudah
deploy ke Railway untuk memastikan skema selaras dengan model tanpa error.

Jalankan:  python migrate.py
"""
import app  # noqa: F401 — registrasi seluruh model ke Base.metadata
from app.core.config import settings
from app.core.database import (
    Base,
    apply_manual_migrations,
    engine,
    sync_columns,
)


def main() -> None:
    # Tampilkan target DB tanpa membocorkan kredensial.
    url = settings.database_url
    safe = url.split("@")[-1] if "@" in url else url
    print(f"[migrate] target DB: ...@{safe}")

    print("[migrate] 1/3 create_all (tabel baru)...")
    Base.metadata.create_all(bind=engine)

    print("[migrate] 2/3 sync_columns (kolom baru)...")
    sync_columns()

    print("[migrate] 3/3 apply_manual_migrations...")
    apply_manual_migrations()

    print("[migrate] SELESAI — skema selaras, tidak ada error.")


if __name__ == "__main__":
    main()
