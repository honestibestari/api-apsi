import enum
import random
from datetime import timedelta

from sqlalchemy import (
    Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core import idhash
from app.core.config import settings
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
    tipe_order        = Column(Enum(TipeOrder, name="tipe_order", values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=TipeOrder.DINE_IN)
    status            = Column(Enum(CustomerOrderStatus, name="customer_order_status", values_callable=lambda obj: [e.value for e in obj]), nullable=False,
                               default=CustomerOrderStatus.VERIFYING, index=True)
    # Metode pembayaran kini FK ke tabel payment_methods (bukan enum), agar selaras
    # dengan daftar yang dikelola admin & dipilih customer. Nullable supaya order
    # lama tanpa metode tidak menghalangi migrasi.
    metode_pembayaran_id = Column(Integer, ForeignKey("payment_methods.id"), nullable=True)
    catatan           = Column(Text, nullable=True)
    total_harga       = Column(Float, nullable=False, default=0.0)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
    updated_at        = Column(DateTime(timezone=True), onupdate=func.now())

    # Relasi yang sudah ada
    customer        = relationship("Customer", back_populates="orders")
    dining_table    = relationship("DiningTable")
    metode          = relationship("PaymentMethod")
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
    def metode_pembayaran(self):
        """Nama metode (string) demi kompatibilitas serialisasi/tampilan lama."""
        return self.metode.nama_metode if self.metode else None

    @property
    def no_meja(self):
        return self.dining_table.label if self.dining_table else None

    @property
    def tenant_count(self):
        return len(self.merchant_orders)

    @property
    def customer_nama(self):
        return self.customer.nama if self.customer else None

    @property
    def hash(self):
        """ID opaque ber-signature untuk akses publik (link email, dsb)."""
        return idhash.encode("customer_order", self.id) if self.id else None

    # ── Deadline turunan (untuk warning di FE) ───────────────────────────────

    @property
    def pay_deadline_at(self):
        """Batas akhir customer membayar. Lewat ini → order dibatalkan otomatis."""
        secs = settings.customer_pay_timeout_seconds
        if self.status != CustomerOrderStatus.VERIFYING or secs <= 0 or not self.created_at:
            return None
        return self.created_at + timedelta(seconds=secs)

    @property
    def auto_confirm_at(self):
        """Batas akhir customer konfirmasi. Lewat ini → order dianggap selesai otomatis."""
        secs = settings.customer_confirm_timeout_seconds
        if self.status != CustomerOrderStatus.WAITING_CONFIRMATION or secs <= 0:
            return None
        ref = self.updated_at or self.created_at
        return ref + timedelta(seconds=secs) if ref else None