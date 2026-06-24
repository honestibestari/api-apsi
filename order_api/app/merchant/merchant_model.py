import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression, func

from app.core.database import Base


class MerchantStatus(str, enum.Enum):
    ACTIVE    = "active"
    PENDING   = "pending"
    SUSPENDED = "suspended"


class Merchant(Base):
    __tablename__ = "merchants"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    foto          = Column(String(500), nullable=True)
    nama          = Column(String, nullable=False, index=True)
    deskripsi     = Column(String, nullable=True)
    alamat        = Column(String, nullable=True)
    owner         = Column(String, nullable=True)
    email         = Column(String, nullable=True)
    phone         = Column(String, nullable=True)
    block         = Column(String, nullable=True)
    category      = Column(String, nullable=True)
    status        = Column(Enum(MerchantStatus, name="merchant_status", values_callable=lambda obj: [e.value for e in obj]), nullable=False,
                           default=MerchantStatus.PENDING, index=True)
    # Status buka/tutup toko yang diatur sendiri oleh merchant (default: buka).
    is_open       = Column(Boolean, nullable=False, server_default=expression.true(),
                           default=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    # Relasi yang sudah ada
    user            = relationship("User", back_populates="merchant")
    products        = relationship("Product", back_populates="merchant",
                                   cascade="all, delete-orphan")
    merchant_orders = relationship("MerchantOrder", back_populates="merchant")
    withdrawals     = relationship("Withdrawal", back_populates="merchant",
                                   cascade="all, delete-orphan")
    bank_accounts   = relationship("MerchantBankAccount", back_populates="merchant",
                                   cascade="all, delete-orphan")
    reviews         = relationship("Review", back_populates="merchant",
                                   cascade="all, delete-orphan")

    # ── Property kalkulasi ────────────────────────────────────────────────────

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
            w.amount for w in self.withdrawals
            if w.status == WithdrawalStatus.APPROVED
        )
        return self.total_revenue - disbursed

    @property
    def rating(self) -> float:
        if not self.reviews:
            return 0.0
        return round(sum(r.rating for r in self.reviews) / len(self.reviews), 1)