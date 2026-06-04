import enum
import random

from sqlalchemy import (
    Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CustomerOrderStatus(str, enum.Enum):
    """Lifecycle pesanan pelanggan (struk global)."""
    VERIFYING            = "verifying"
    OPEN                 = "open"
    PROCESS              = "process"
    WAITING_CONFIRMATION = "waiting_confirmation"
    DONE                 = "done"
    CANCELLED            = "cancelled"


class TipeOrder(str, enum.Enum):
    DINE_IN  = "dine_in"
    TAKEAWAY = "takeaway"


class MetodePembayaran(str, enum.Enum):
    QRIS  = "qris"
    TUNAI = "tunai"


def _generate_order_code() -> str:
    return f"ORD-{random.randint(1, 999999):06d}"


class CustomerOrder(Base):
    """Satu pesanan pelanggan = satu struk global yang dipecah ke beberapa MerchantOrder."""
    __tablename__ = "customer_orders"

    id                = Column(Integer, primary_key=True, index=True)
    order_code        = Column(String(20), unique=True, index=True,
                               default=_generate_order_code, nullable=False)
    customer_id       = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    dining_table_id   = Column(Integer, ForeignKey("dining_tables.id"), nullable=True)
    tipe_order        = Column(Enum(TipeOrder), nullable=False, default=TipeOrder.DINE_IN)
    status            = Column(Enum(CustomerOrderStatus), nullable=False,
                               default=CustomerOrderStatus.VERIFYING, index=True)
    metode_pembayaran = Column(Enum(MetodePembayaran), nullable=False,
                               default=MetodePembayaran.QRIS)
    catatan           = Column(Text, nullable=True)
    total_harga       = Column(Float, nullable=False, default=0.0)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
    updated_at        = Column(DateTime(timezone=True), onupdate=func.now())

    # Relasi yang sudah ada
    customer        = relationship("Customer", back_populates="orders")
    dining_table    = relationship("DiningTable")
    merchant_orders = relationship("MerchantOrder", back_populates="customer_order",
                                   cascade="all, delete-orphan")

    # ← TAMBAH: relasi ke Payment (PESANAN → PEMBAYARAN 1:N)
    payments = relationship("Payment", back_populates="pesanan",
                            cascade="all, delete-orphan")

    # ← TAMBAH: relasi ke Refund (PESANAN → REFUND 1:N)
    refunds  = relationship("Refund", back_populates="pesanan",
                            cascade="all, delete-orphan")

    # ── Property turunan ─────────────────────────────────────────────────────

    @property
    def no_meja(self):
        return self.dining_table.label if self.dining_table else None

    @property
    def tenant_count(self):
        return len(self.merchant_orders)

    @property
    def customer_nama(self):
        return self.customer.nama if self.customer else None