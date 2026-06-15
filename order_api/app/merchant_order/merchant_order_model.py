import enum

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class MerchantOrderStatus(str, enum.Enum):
    """Lifecycle pesanan di sisi merchant (tenant)."""
    BARU       = "baru"
    TERBUKA    = "terbuka"
    DIPROSES   = "diproses"
    SELESAI    = "selesai"
    DIBATALKAN = "dibatalkan"


class NotifikasiTipe(str, enum.Enum):
    ORDER_BARU       = "order_baru"
    STATUS_BERUBAH   = "status_berubah"
    ORDER_DIBATALKAN = "order_dibatalkan"
    ORDER_SELESAI    = "order_selesai"


class MerchantOrder(Base):
    """Bagian dari CustomerOrder yang ditujukan ke satu merchant (satu tenant order)."""
    __tablename__ = "merchant_orders"

    id                = Column(Integer, primary_key=True, index=True)
    order_code        = Column(String(30), unique=True, index=True, nullable=False)
    customer_order_id = Column(Integer, ForeignKey("customer_orders.id"), nullable=False, index=True)
    merchant_id       = Column(Integer, ForeignKey("merchants.id"), nullable=False, index=True)
    status            = Column(Enum(MerchantOrderStatus, name="merchant_order_status",
                                   values_callable=lambda obj: [e.value for e in obj]),
                               nullable=False, default=MerchantOrderStatus.BARU, index=True)
    subtotal          = Column(Float, nullable=False, default=0.0)
    biaya_penanganan  = Column(Float, nullable=False, default=0.0)
    total_harga       = Column(Float, nullable=False, default=0.0)

    metode_pembayaran = Column(String(50), nullable=True)

    created_at        = Column(DateTime(timezone=True), server_default=func.now())
    updated_at        = Column(DateTime(timezone=True), onupdate=func.now())

    customer_order = relationship("CustomerOrder", back_populates="merchant_orders")
    merchant       = relationship("Merchant", back_populates="merchant_orders")
    items          = relationship("OrderItem", back_populates="merchant_order",
                                  cascade="all, delete-orphan")
    notifikasi     = relationship("Notification", back_populates="merchant_order",
                                  cascade="all, delete-orphan")

    # ── Property turunan untuk response ──────────────────────────────────────

    @property
    def merchant_nama(self):
        return self.merchant.nama if self.merchant else None

    @property
    def no_meja(self):
        co = self.customer_order
        return co.dining_table.label if co and co.dining_table else None

    @property
    def pelanggan_nama(self):
        co = self.customer_order
        return co.customer.nama if co and co.customer else None

    @property
    def tipe_order(self):
        return self.customer_order.tipe_order if self.customer_order else None


    @property
    def metode_pembayaran_display(self):
        co = self.customer_order
        return co.metode_pembayaran if co else self.metode_pembayaran

    @property
    def preview_items(self):
        return ", ".join(
            f"{i.jumlah}x {i.product.nama}" for i in self.items if i.product
        )


class OrderItem(Base):
    __tablename__ = "order_items"

    id                = Column(Integer, primary_key=True, index=True)
    merchant_order_id = Column(Integer, ForeignKey("merchant_orders.id"), nullable=False)
    product_id        = Column(Integer, ForeignKey("products.id"), nullable=False)
    jumlah            = Column(Integer, nullable=False, default=1)
    harga_satuan      = Column(Float, nullable=False)
    subtotal          = Column(Float, nullable=False)
    varian            = Column(String(100), nullable=True)

    merchant_order = relationship("MerchantOrder", back_populates="items")
    product        = relationship("Product")


class Notification(Base):
    __tablename__ = "notifications"

    id                = Column(Integer, primary_key=True, index=True)
    merchant_id       = Column(Integer, ForeignKey("merchants.id"), nullable=False, index=True)
    merchant_order_id = Column(Integer, ForeignKey("merchant_orders.id"), nullable=True)
    tipe              = Column(Enum(NotifikasiTipe, name="notifikasi_tipe",
                                   values_callable=lambda obj: [e.value for e in obj]),
                               nullable=False)
    judul             = Column(String(200), nullable=False)
    pesan             = Column(Text, nullable=False)
    is_read           = Column(Boolean, nullable=False, default=False)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())

    merchant       = relationship("Merchant")
    merchant_order = relationship("MerchantOrder", back_populates="notifikasi")