import enum

from sqlalchemy import Column, DateTime, Enum, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class MerchantStatus(str, enum.Enum):
    ACTIVE    = "active"
    PENDING   = "pending"
    SUSPENDED = "suspended"


class Merchant(Base):
    __tablename__ = "merchants"

    password_hash = Column(String, nullable=False)

    id = Column(Integer, primary_key=True, index=True)
    nama = Column(String, nullable=False, index=True)
    deskripsi = Column(String)
    alamat = Column(String)

    # Profil untuk konsol admin.
    owner    = Column(String)
    email    = Column(String)
    phone    = Column(String)
    block    = Column(String)
    category = Column(String)
    status   = Column(Enum(MerchantStatus), nullable=False, default=MerchantStatus.PENDING, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relasi.
    products        = relationship("Product", back_populates="merchant", cascade="all, delete-orphan")
    merchant_orders = relationship("MerchantOrder", back_populates="merchant")
    withdrawals     = relationship("Withdrawal", back_populates="merchant", cascade="all, delete-orphan")
    reviews         = relationship("Review", back_populates="merchant", cascade="all, delete-orphan")

    # ── Ringkasan yang dihitung langsung dari relasi ──
    @property
    def total_orders(self) -> int:
        return len(self.merchant_orders)

    @property
    def total_revenue(self) -> float:
        from app.merchant_order.merchant_order_model import MerchantOrderStatus
        return sum(
            mo.total_harga
            for mo in self.merchant_orders
            if mo.status == MerchantOrderStatus.SELESAI
        )

    @property
    def balance(self) -> float:
        from app.withdrawal.withdrawal_model import WithdrawalStatus
        disbursed = sum(
            w.amount for w in self.withdrawals if w.status == WithdrawalStatus.APPROVED
        )
        return self.total_revenue - disbursed

    @property
    def rating(self) -> float:
        if not self.reviews:
            return 0.0
        return round(sum(r.rating for r in self.reviews) / len(self.reviews), 1)
