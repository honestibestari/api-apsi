import enum

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class StatusRefund(str, enum.Enum):
    PENDING   = "pending"
    DISETUJUI = "disetujui"
    DITOLAK   = "ditolak"


class Refund(Base):
    __tablename__ = "refunds"

    id            = Column(Integer, primary_key=True, index=True)
    id_pesanan    = Column(Integer, ForeignKey("customer_orders.id"), nullable=False)
    nominal       = Column(Float, nullable=False)
    metode_refund = Column(String(100), nullable=True)  # mis. "Transfer BCA"
    nomor_tujuan  = Column(String(100), nullable=True)  # nomor rekening tujuan
    status        = Column(Enum(StatusRefund), nullable=False, default=StatusRefund.PENDING)
    timestamp     = Column(DateTime(timezone=True), server_default=func.now())

    pesanan = relationship("CustomerOrder")