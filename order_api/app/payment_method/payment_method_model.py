from sqlalchemy import Boolean, Column, Integer, String

from app.core.database import Base


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id          = Column(Integer, primary_key=True, index=True)
    nama_metode = Column(String(50), unique=True, nullable=False)
    # Aktif/nonaktif: metode nonaktif tidak ditawarkan ke customer saat checkout.
    is_active   = Column(Boolean, nullable=False, server_default="true")
    # Kode channel Tripay untuk metode ini (mis. "QRIS", "BRIVA", "OVO").
    # NULL = metode lokal tanpa gateway (mis. Tunai) / belum dihubungkan —
    # saat PAYMENT_GATEWAY=tripay, metode non-tunai tanpa kode ini ditolak charge.
    tripay_code = Column(String(30), nullable=True)
    # Data awal: QRIS, Tunai, Transfer Bank, OVO, GoPay