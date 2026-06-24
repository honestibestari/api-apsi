from sqlalchemy import Boolean, Column, DateTime, Float, Integer
from sqlalchemy.sql import expression, func

from app.core.database import Base


class PlatformSetting(Base):
    """Konfigurasi pendapatan platform (biaya layanan) — SATU baris (singleton).

    Disimpan di DB (bukan .env) supaya admin bisa mengubah besar revenue saat
    runtime tanpa redeploy. Biaya layanan dibebankan ke CUSTOMER (ditambahkan ke
    total bayar) dengan model gabungan persen + nominal tetap:

        biaya_layanan = round( fee_rate% × subtotal  +  fee_fixed )

    `fee_rate` dalam persen (mis. 5.0 = 5%). `fee_fixed` dalam rupiah. Bila
    `is_active` false → biaya layanan = 0 (fitur dimatikan).
    """
    __tablename__ = "platform_settings"

    id         = Column(Integer, primary_key=True, index=True)
    fee_rate   = Column(Float, nullable=False, default=0.0, server_default="0")
    fee_fixed  = Column(Float, nullable=False, default=0.0, server_default="0")
    is_active  = Column(Boolean, nullable=False, default=True,
                        server_default=expression.true())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now())
