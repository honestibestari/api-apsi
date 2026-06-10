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
    database_url: str

    # Jika true, DROP semua tabel + tipe enum lalu bangun ulang dari model saat
    # startup. HANYA untuk dev — SEMUA DATA HILANG. Set sekali untuk membereskan
    # drift skema, lalu kembalikan ke false.
    reset_db: bool = False

    # ─── Auth / JWT ──────────────────────────────────────
    # WAJIB di-set lewat env var di production. Default hanya untuk dev lokal.
    secret_key: str = "hjswbvgfjewht48whsdkvgds"
    algorithm: str = "HS256"
    token_expire_minutes: int = 60 * 24  # 1 hari

    # ─── Frontend ────────────────────────────────────────
    # URL frontend yang dituju setelah scan QR dining table.
    frontend_url: str = "http://localhost:3000"

    # ─── Pembayaran (mode dummy) ─────────────────────────
    # Selama belum ada gateway asli: pembayaran non-tunai yang masih PENDING akan
    # otomatis dianggap LUNAS setelah sekian detik (disimulasikan saat FE polling
    # status). Set 0 untuk menonaktifkan (mis. saat gateway asli sudah dipasang).
    dummy_payment_auto_paid_seconds: int = 20

    # Batas waktu merchant memutuskan (confirm/tolak) sebuah merchant order setelah
    # dibayar. Lewat ambang ini & masih 'terbuka' → otomatis dibatalkan. Set 0 = off.
    merchant_decide_timeout_seconds: int = 600  # 10 menit

    # ─── CORS ────────────────────────────────────────────
    # Daftar origin dipisah koma, mis. "http://localhost:3000,http://localhost:5173"
    cors_origins: str = "*"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
