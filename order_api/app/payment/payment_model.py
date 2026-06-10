import enum
import secrets

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


def _generate_public_token() -> str:
    # ~43 char URL-safe acak. Dipakai di link status pembayaran karena customer
    # tidak login — id sekuensial gampang ditebak (IDOR), token ini tidak.
    return secrets.token_urlsafe(32)


class StatusPembayaran(str, enum.Enum):
    PENDING  = "pending"
    LUNAS    = "lunas"
    GAGAL    = "gagal"
    REFUNDED = "refunded"
 
 
class Payment(Base):
    __tablename__ = "payments"
 
    id                   = Column(Integer, primary_key=True, index=True)
    # Token publik acak untuk link status (customer tidak login). Nullable agar
    # migrasi additive di tabel lama tidak gagal; di-backfill untuk baris lama.
    public_token         = Column(String(64), unique=True, index=True, nullable=True,
                                  default=_generate_public_token)
    id_pesanan           = Column(Integer, ForeignKey("customer_orders.id"), nullable=False)
    metode_pembayaran_id = Column(Integer, ForeignKey("payment_methods.id"), nullable=True)
    metode_pembayaran    = Column(String(50), nullable=False)
    status_pembayaran    = Column(Enum(StatusPembayaran, name="status_pembayaran", values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=StatusPembayaran.PENDING)
    nominal              = Column(Float, nullable=False)
    qrcode_kode_url      = Column(String(500), nullable=True)
    timestamp            = Column(DateTime(timezone=True), server_default=func.now())

    # ── Field bergaya gateway (dipakai dummy, siap untuk Midtrans/Flip) ──────────
    # Diisi saat charge; bentuknya meniru respons gateway agar nanti tinggal swap.
    transaction_id       = Column(String(64), nullable=True, index=True)
    payment_url          = Column(String(500), nullable=True)   # type=redirect
    va_number            = Column(String(40), nullable=True)    # type=va
    expires_at           = Column(DateTime(timezone=True), nullable=True)
    paid_at              = Column(DateTime(timezone=True), nullable=True)

    # Relasi
    pesanan = relationship("CustomerOrder")
    metode  = relationship("PaymentMethod")