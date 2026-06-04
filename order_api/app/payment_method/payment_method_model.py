from sqlalchemy import Column, Integer, String

from app.core.database import Base


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id          = Column(Integer, primary_key=True, index=True)
    nama_metode = Column(String(50), unique=True, nullable=False)
    # Data awal: QRIS, Tunai, Transfer Bank, OVO, GoPay