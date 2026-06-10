from sqlalchemy import Boolean, Column, Integer, String

from app.core.database import Base


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id          = Column(Integer, primary_key=True, index=True)
    nama_metode = Column(String(50), unique=True, nullable=False)
    # Aktif/nonaktif: metode nonaktif tidak ditawarkan ke customer saat checkout.
    is_active   = Column(Boolean, nullable=False, server_default="true")
    # Fee disimpan sebagai teks bebas agar muat format apa pun ("0.7%", "Rp 2.000").
    fee         = Column(String(50), nullable=False, server_default="")
    # Data awal: QRIS, Tunai, Transfer Bank, OVO, GoPay