"""Entry point serverless Vercel.

Vercel mendeteksi file di folder api/ sebagai serverless function dan memakai
variabel `app` (ASGI) secara langsung. Semua path aplikasi diarahkan ke sini
lewat rewrite di vercel.json, jadi seluruh router FastAPI tetap dilayani di
path aslinya (/payments, /products, /docs, dst).

Catatan serverless:
  • Set env MAINTENANCE_SWEEP_SECONDS=0 di Vercel — BackgroundScheduler tidak
    hidup di serverless; gantinya panggil /maintenance/sweep via cron eksternal.
  • Filesystem read-only — upload attachment butuh BLOB_READ_WRITE_TOKEN
    (Vercel Blob), fallback disk lokal tidak tersedia.
"""
import sys
from pathlib import Path

# Pastikan root project (folder yang berisi package `app/`) ada di sys.path,
# apa pun working directory yang dipakai runtime Vercel.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402,F401
