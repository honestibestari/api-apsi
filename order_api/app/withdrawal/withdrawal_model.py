import enum

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class WithdrawalStatus(str, enum.Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Withdrawal(Base):
    """Permintaan penarikan dana (payout) merchant.

    Saldo merchant diturunkan dari (total_revenue − Σ withdrawal yang APPROVED).
    """
    __tablename__ = "withdrawals"

    id             = Column(Integer, primary_key=True, index=True)
    merchant_id    = Column(Integer, ForeignKey("merchants.id"), nullable=False, index=True)
    amount         = Column(Float, nullable=False)
    status         = Column(Enum(WithdrawalStatus, name="withdrawal_status", values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=WithdrawalStatus.PENDING, index=True)
    bank           = Column(String(50))
    account_number = Column(String(40))
    account_name   = Column(String(100))
    note           = Column(Text, nullable=True)
    processed_by   = Column(Integer, ForeignKey("users.id"), nullable=True)
    requested_at   = Column(DateTime(timezone=True), server_default=func.now())
    processed_at   = Column(DateTime(timezone=True), nullable=True)

    merchant   = relationship("Merchant", back_populates="withdrawals")
    admin_user = relationship("User", foreign_keys=[processed_by])

    @property
    def merchant_nama(self):
        return self.merchant.nama if self.merchant else None


class MerchantBankAccount(Base):
    """Rekening tujuan pencairan yang disimpan merchant (reusable saat menarik dana).

    Sebelumnya hanya disimpan di localStorage browser → hilang bila ganti
    perangkat/clear browser. Kini dipersistensikan per-merchant di server.
    """
    __tablename__ = "merchant_bank_accounts"

    id             = Column(Integer, primary_key=True, index=True)
    merchant_id    = Column(Integer, ForeignKey("merchants.id"), nullable=False, index=True)
    bank           = Column(String(50), nullable=False)
    account_number = Column(String(40), nullable=False)
    account_name   = Column(String(100), nullable=False)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    merchant = relationship("Merchant", back_populates="bank_accounts")
