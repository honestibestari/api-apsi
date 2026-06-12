import enum

from sqlalchemy import (
    CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class EntityType(str, enum.Enum):
    """Tabel-tabel yang boleh dilampiri attachment.

    Tambah nilai baru di sini saja saat ada kebutuhan — skema tabel tidak perlu
    diubah (inilah keunggulan pola polymorphic).
    """
    PRODUCT  = "product"
    MERCHANT = "merchant"
    REVIEW   = "review"
    PAYMENT  = "payment"


class Attachment(Base):
    __tablename__ = "attachments"

    id           = Column(Integer, primary_key=True, index=True)
    url          = Column(String(500), nullable=False)       # URL dari Vercel Blob
    filename     = Column(String(200), nullable=False)       # nama file asli
    content_type = Column(String(100), nullable=True)        # image/jpeg, image/png, dll
    size         = Column(Integer, nullable=True)            # ukuran file dalam bytes

    # ── Relasi polymorphic: WAJIB terisi keduanya ──────────────────────────────
    entity_type  = Column(String(50), nullable=False)        # "product", "merchant", dll
    entity_id    = Column(Integer,    nullable=False)        # id baris di tabel tujuan

    uploaded_by  = Column(Integer, ForeignKey("merchants.id"), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    uploader = relationship("Merchant")

    __table_args__ = (
        # Percepat query "semua attachment milik <entity> #<id>".
        Index("ix_attachment_entity", "entity_type", "entity_id"),
        # Jaminan "selalu punya relasi": kedua kolom tak boleh kosong.
        CheckConstraint(
            "entity_type IS NOT NULL AND entity_id IS NOT NULL",
            name="ck_attachment_entity_required",
        ),
    )
