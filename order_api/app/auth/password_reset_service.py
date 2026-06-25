"""Logika lupa & reset password merchant.

Alur:
  1. request_reset  → cari user (email/username/HP), buat token acak, simpan
     HANYA hash-nya, kirim link berisi token asli ke email merchant.
  2. validate_token → cek token masih valid (ada, belum dipakai, belum kedaluwarsa).
  3. reset_password → set password baru ke User + Merchant, tandai token terpakai.

Demi keamanan, request_reset SELALU "berhasil" dari sudut pandang pemanggil
(tidak membocorkan apakah identifier terdaftar atau tidak).
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth.password_reset_model import PasswordResetToken
from app.core.auth import hash_password
from app.core.config import settings
from app.core.email import build_reset_password_html, send_email
from app.merchant.merchant_model import Merchant
from app.user.user_model import User, UserRole

TOKEN_TTL = timedelta(hours=1)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _find_merchant_user(db: Session, identifier: str) -> Optional[User]:
    """Cari User merchant lewat email/username/HP (sama seperti alur login)."""
    user = db.query(User).filter(User.email == identifier).first()
    if not user:
        user = db.query(User).filter(User.username == identifier).first()
    if not user:
        merchant = db.query(Merchant).filter(Merchant.phone == identifier).first()
        if merchant and merchant.user_id:
            user = db.query(User).filter(User.id == merchant.user_id).first()
    if user and user.role == UserRole.MERCHANT:
        return user
    return None


def _destination_email(user: User) -> Optional[str]:
    """Email tujuan kirim link. Utamakan email asli merchant; email
    `*@merchant.local` (placeholder untuk daftar via HP) dilewati."""
    merchant = user.merchant
    if merchant and merchant.email and "@" in merchant.email:
        return merchant.email
    if user.email and not user.email.endswith("@merchant.local"):
        return user.email
    return None


def request_reset(db: Session, identifier: str, background_tasks=None) -> None:
    """Buat token reset & kirim email. Selalu sukses tanpa membocorkan info akun.

    Bila `background_tasks` diberikan, pengiriman email dijadwalkan di latar
    agar response tidak menunggu round-trip Gmail API.
    """
    identifier = (identifier or "").strip()
    if not identifier:
        return

    user = _find_merchant_user(db, identifier)
    if not user:
        return

    to_email = _destination_email(user)
    if not to_email:
        # Tidak ada email tujuan (mis. merchant daftar pakai HP tanpa email).
        return

    # Batalkan token lama yang belum dipakai agar hanya satu link aktif.
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used.is_(False),
    ).update({PasswordResetToken.used: True}, synchronize_session=False)

    raw_token = secrets.token_urlsafe(32)
    db.add(PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + TOKEN_TTL,
    ))
    db.commit()

    base = settings.frontend_url.rstrip("/")
    reset_url = f"{base}/merchant/reset-password?token={raw_token}"
    nama = user.merchant.nama if user.merchant else None
    html = build_reset_password_html(nama, reset_url)
    subject = "Atur Ulang Kata Sandi — Teras LA DineHub"
    if background_tasks is not None:
        background_tasks.add_task(send_email, to_email, subject, html)
    else:
        send_email(to=to_email, subject=subject, html=html)


def _valid_token_or_none(db: Session, raw_token: str) -> Optional[PasswordResetToken]:
    if not raw_token:
        return None
    token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == _hash_token(raw_token),
        PasswordResetToken.used.is_(False),
    ).first()
    if not token:
        return None
    exp = token.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < datetime.now(timezone.utc):
        return None
    return token


def validate_token(db: Session, raw_token: str) -> bool:
    return _valid_token_or_none(db, raw_token) is not None


def reset_password(db: Session, raw_token: str, new_password: str) -> None:
    if not new_password or len(new_password) < 8:
        raise HTTPException(status_code=422, detail="Password minimal 8 karakter")

    token = _valid_token_or_none(db, raw_token)
    if not token:
        raise HTTPException(status_code=400, detail="Tautan reset tidak valid atau sudah kedaluwarsa")

    user = db.query(User).filter(User.id == token.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Akun tidak ditemukan")

    hashed = hash_password(new_password)
    user.password_hash = hashed
    if user.merchant:
        user.merchant.password_hash = hashed

    token.used = True
    db.commit()
