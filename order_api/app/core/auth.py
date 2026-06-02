"""Core auth — JWT token, password hashing, dependency get_current_user.

Perubahan dari versi sebelumnya:
- create_token() sekarang menyertakan 'role' (admin/merchant) di dalam token
- Tambah get_current_user() → return dict {id, role}
- Tambah require_admin() → dependency khusus endpoint admin
- Tambah get_current_merchant() → dependency khusus endpoint merchant
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.database import get_db

SECRET_KEY             = "hjswbvgfjewht48whsdkvgds"
ALGORITHM              = "HS256"
TOKEN_EXPIRE_MINUTES   = 60 * 24  # 1 hari

pwd_context   = CryptContext(schemes=["bcrypt"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


# ── Password ──────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── Token ─────────────────────────────────────────────────────────────────────

def create_token(user_id: int, role: str) -> str:
    """Buat JWT token berisi user_id dan role (admin/merchant)."""
    expire  = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ── Dependencies ──────────────────────────────────────────────────────────────

def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
) -> dict:
    """Decode token → return {"id": int, "role": str}.

    Dipanggil oleh require_admin dan get_current_merchant.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak ditemukan, silakan login",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
        role    = payload["role"]
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid atau sudah expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"id": user_id, "role": role}


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Dependency — hanya admin yang boleh akses.

    Pasang di endpoint admin:
    _: None = Depends(require_admin)
    """
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak — hanya admin yang bisa mengakses endpoint ini",
        )
    return current_user


def get_current_merchant(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dependency — hanya merchant yang boleh akses.

    Pasang di endpoint merchant:
    current_merchant: Merchant = Depends(get_current_merchant)
    """
    from app.merchant.merchant_model import Merchant

    if current_user["role"] != "merchant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak — hanya merchant yang bisa mengakses endpoint ini",
        )
    merchant = db.query(Merchant).filter(Merchant.id == current_user["id"]).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant tidak ditemukan")
    return merchant