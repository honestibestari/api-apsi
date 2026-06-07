"""Entrypoint untuk menjalankan server secara lokal.

Jalankan dengan:  python run.py
Atau langsung:    uvicorn app.main:app --reload
"""
import os

import uvicorn

from app.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        # Render (dan platform PaaS lain) menyuntik port lewat env var PORT.
        port=int(os.getenv("PORT", "8000")),
        reload=settings.debug,
    )
