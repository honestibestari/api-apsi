import secrets

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


def _generate_code() -> str:
    # Token acak 8-byte → ~11 char URL-safe (mis. "aB3xK9pQr2_")
    return secrets.token_urlsafe(8)


class DiningTable(Base):
    """Meja fisik di area dining.

    Tidak terikat ke merchant manapun — di skenario food court, meja
    netral dan bisa dipakai pesan ke tenant manapun. Relasi ke tenant
    baru muncul lewat tabel Order nanti.
    """

    __tablename__ = "dining_tables"

    id = Column(Integer, primary_key=True, index=True)
    # Kode unik yang ditanam di QR. Bukan id sequential, supaya tidak gampang ditebak.
    code = Column(
        String, unique=True, nullable=False, index=True, default=_generate_code
    )
    # Label fisik yang dilihat staff & pelanggan (mis. "T-12", "A1").
    label = Column(String, unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
