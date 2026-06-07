import enum
 
from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
 
from app.core.database import Base
 
 
class StatusPembayaran(str, enum.Enum):
    PENDING  = "pending"
    LUNAS    = "lunas"
    GAGAL    = "gagal"
    REFUNDED = "refunded"
 
 
class Payment(Base):
    __tablename__ = "payments"
 
    id                   = Column(Integer, primary_key=True, index=True)
    id_pesanan           = Column(Integer, ForeignKey("customer_orders.id"), nullable=False)
    metode_pembayaran_id = Column(Integer, ForeignKey("payment_methods.id"), nullable=True)
    metode_pembayaran    = Column(String(50), nullable=False)
    status_pembayaran    = Column(Enum(StatusPembayaran, name="status_pembayaran", values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=StatusPembayaran.PENDING)
    nominal              = Column(Float, nullable=False)
    qrcode_kode_url      = Column(String(500), nullable=True)
    struk_dikirim        = Column(String(200), nullable=True)
    timestamp            = Column(DateTime(timezone=True), server_default=func.now())
 
    # Relasi
    pesanan = relationship("CustomerOrder")
    metode  = relationship("PaymentMethod")