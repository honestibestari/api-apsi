"""Konfigurasi aplikasi.

Semua setting dibaca dari environment / file .env lewat pydantic-settings,
sehingga tidak ada nilai yang di-hardcode di dalam kode.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ─── Aplikasi ────────────────────────────────────────
    app_name: str = "Product & Merchant API"
    app_version: str = "1.0.0"
    debug: bool = True

    # ─── Database ────────────────────────────────────────
    # Default: SQLite lokal di folder order_api.
    database_url: str = "sqlite:///./store.db"

    # ─── Frontend ────────────────────────────────────────
    # URL frontend yang dituju setelah scan QR dining table.
    frontend_url: str = "http://localhost:3000"

    # ─── CORS ────────────────────────────────────────────
    # Daftar origin dipisah koma, mis. "http://localhost:3000,http://localhost:5173"
    cors_origins: str = "*"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
