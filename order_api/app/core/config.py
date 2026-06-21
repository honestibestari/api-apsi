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

    # ─── Vercel Blob ─────────────────────────────────────────
    blob_read_write_token: str = ""

    # ─── Penyimpanan attachment lokal (fallback) ─────────────
    # Bila blob_read_write_token kosong, file diunggah ke disk lokal & dilayani
    # via /static. static_base_url = origin publik API ini (tanpa trailing slash),
    # dipakai membentuk URL absolut file lokal agar bisa diakses FE.
    static_base_url: str = "http://localhost:8000"

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

    # ─── Email (Brevo HTTP API) ──────────────────────────
    # Pengiriman email notifikasi pesanan lewat Brevo (HTTPS:443) — aman di host
    # cloud yang memblokir port SMTP keluar (Render/Railway). Bisa kirim ke email
    # mana pun TANPA punya domain: cukup verifikasi 1 alamat pengirim
    # (brevo_sender_email) di dashboard Brevo (Senders → klik link verifikasi).
    # Bila brevo_api_key / brevo_sender_email kosong → pengiriman dilewati
    # diam-diam (tidak menghalangi pembuatan order).
    email_from_name: str = "Teras LA DineHub"
    brevo_api_key: str = ""
    brevo_sender_email: str = ""

    # ─── Pembayaran (mode dummy) ─────────────────────────
    # Selama belum ada gateway asli: pembayaran non-tunai yang masih PENDING akan
    # otomatis dianggap LUNAS setelah sekian detik (disimulasikan saat FE polling
    # status). Set 0 untuk menonaktifkan (mis. saat gateway asli sudah dipasang).
    dummy_payment_auto_paid_seconds: int = 20

    # Batas waktu merchant memutuskan (confirm/tolak) sebuah merchant order setelah
    # dibayar. Lewat ambang ini & masih 'terbuka' → otomatis dibatalkan. Set 0 = off.
    merchant_decide_timeout_seconds: int = 600  # 10 menit

    # ─── Timeout siklus order (sweep maintenance) ────────
    # Order 'verifying' (belum dibayar) lewat ambang ini sejak dibuat → otomatis
    # dibatalkan & stok dikembalikan. Mencegah order telantar mengunci stok. 0 = off.
    customer_pay_timeout_seconds: int = 900  # 15 menit

    # Batas wajar merchant menyelesaikan pesanan yang sudah 'diproses'. Lewat ambang
    # ini → ditandai TERLAMBAT (pengingat ke merchant), TIDAK auto-selesai. 0 = off.
    merchant_prep_timeout_seconds: int = 1800  # 30 menit

    # Order 'waiting_confirmation' (semua tenant selesai) yang tak dikonfirmasi
    # customer dalam ambang ini → otomatis dianggap 'done'. 0 = off.
    customer_confirm_timeout_seconds: int = 86400  # 24 jam

    # Batas jumlah pesanan AKTIF (belum done/cancelled) per akun customer (per email).
    # Cegah satu akun menumpuk banyak pesanan sekaligus. 0 = tanpa batas.
    max_active_orders_per_customer: int = 2

    # Interval sweep maintenance otomatis (detik). Menggerakkan semua timeout di
    # atas tanpa bergantung pada polling FE. 0 = nonaktifkan scheduler internal
    # (gunakan endpoint POST /maintenance/sweep via cron eksternal sebagai gantinya).
    maintenance_sweep_seconds: int = 60

    # ─── CORS ────────────────────────────────────────────
    # Daftar origin dipisah koma, mis. "http://localhost:3000,http://localhost:5173"
    cors_origins: str = "*"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
