import enum
import random

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float,
    ForeignKey, Integer, String, Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class OrderStatus(str, enum.Enum):
    BARU       = "baru"
    DIPROSES   = "diproses"
    SELESAI    = "selesai"
    DIBATALKAN = "dibatalkan"


class TipeOrder(str, enum.Enum):
    DINE_IN  = "dine_in"
    TAKEAWAY = "takeaway"


class MetodePembayaran(str, enum.Enum):
    QRIS  = "qris"
    TUNAI = "tunai"


class NotifikasiTipe(str, enum.Enum):
    ORDER_BARU       = "order_baru"
    STATUS_BERUBAH   = "status_berubah"
    ORDER_DIBATALKAN = "order_dibatalkan"
    ORDER_SELESAI    = "order_selesai"


def _generate_order_code() -> str:
    return f"ORD-{random.randint(1, 9999):04d}"


class Order(Base):
    __tablename__ = "orders"

    id              = Column(Integer, primary_key=True, index=True)
    order_code      = Column(String(20), unique=True, index=True, default=_generate_order_code, nullable=False)
    merchant_id     = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    dining_table_id = Column(Integer, ForeignKey("dining_tables.id"), nullable=True)
    nama_pelanggan  = Column(String(100), nullable=False)
    tipe_order      = Column(Enum(TipeOrder), nullable=False, default=TipeOrder.DINE_IN)
    status          = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.BARU, index=True)
    catatan         = Column(Text, nullable=True)
    subtotal        = Column(Float, nullable=False, default=0.0)
    biaya_penanganan = Column(Float, nullable=False, default=1000.0)
    total_harga     = Column(Float, nullable=False, default=0.0)
    metode_pembayaran = Column(Enum(MetodePembayaran), nullable=False, default=MetodePembayaran.QRIS)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    merchant     = relationship("Merchant")
    dining_table = relationship("DiningTable")
    items        = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    notifikasi   = relationship("Notification", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id           = Column(Integer, primary_key=True, index=True)
    order_id     = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id   = Column(Integer, ForeignKey("products.id"), nullable=False)
    jumlah       = Column(Integer, nullable=False, default=1)
    harga_satuan = Column(Float, nullable=False)
    subtotal     = Column(Float, nullable=False)
    varian       = Column(String(100), nullable=True)

    order   = relationship("Order", back_populates="items")
    product = relationship("Product")


class Notification(Base):
    __tablename__ = "notifications"

    id          = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    order_id    = Column(Integer, ForeignKey("orders.id"), nullable=True)
    tipe        = Column(Enum(NotifikasiTipe), nullable=False)
    judul       = Column(String(200), nullable=False)
    pesan       = Column(Text, nullable=False)
    is_read     = Column(Boolean, nullable=False, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    merchant = relationship("Merchant")
    order    = relationship("Order", back_populates="notifikasi")