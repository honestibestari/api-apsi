"""Token reset password (lupa password merchant).

Saat merchant minta reset, kita buat token acak (secrets), kirim token tsb di
dalam link email, tetapi yang DISIMPAN di database hanya hash SHA-256-nya. Jadi
walau isi tabel bocor, token asli di link tidak bisa direkonstruksi. Token punya
masa berlaku (expires_at) dan sekali pakai (used).
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # Hanya hash token yang disimpan (token asli ada di link email).
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used       = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
