from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id          = Column(Integer, primary_key=True, index=True)
    nama        = Column(String(100), nullable=False)
    email       = Column(String(150), unique=True, index=True, nullable=True)
    phone       = Column(String(30),  unique=True, index=True, nullable=True)
    no_wa       = Column(String(30),  nullable=True)
    session_id  = Column(String(200), nullable=True)
    expired_id  = Column(DateTime(timezone=True), nullable=True)
    minta_struk = Column(Boolean, nullable=False, default=False)
    # Penanda admin untuk customer yang dicurigai/diawasi (mis. fraud). Persist di DB.
    flagged     = Column(Boolean, nullable=False, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    # Relasi yang sudah ada
    orders = relationship("CustomerOrder", back_populates="customer")

    # ← TAMBAH: relasi ke Review (ULASAN → USER/Customer N:1)
    reviews = relationship("Review", back_populates="customer")

    # ── Property kalkulasi (dipakai konsol admin) ─────────────────────────────

    @property
    def total_orders(self) -> int:
        return len(self.orders)

    @property
    def total_spent(self) -> float:
        """Total belanja = Σ total_harga semua order yang tidak dibatalkan."""
        from app.customer_order.customer_order_model import CustomerOrderStatus
        return sum(
            o.total_harga
            for o in self.orders
            if o.status != CustomerOrderStatus.CANCELLED
        )

    @property
    def last_order_at(self):
        """Waktu order terakhir, atau None bila belum pernah order."""
        if not self.orders:
            return None
        return max(o.created_at for o in self.orders if o.created_at)