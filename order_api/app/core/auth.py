from datetime import datetime, timedelta, timezone
from typing import Optional
 
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

SECRET_KEY           = settings.secret_key
ALGORITHM            = settings.algorithm
TOKEN_EXPIRE_MINUTES = settings.token_expire_minutes
 
pwd_context   = CryptContext(schemes=["bcrypt"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
 
 
# ── Password ──────────────────────────────────────────────────────────────────
 
def hash_password(password: str) -> str:
    return pwd_context.hash(password)
 
 
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
 
 
# ── Token ─────────────────────────────────────────────────────────────────────
 
def create_token(user_id: int, role: str) -> str:
    """Buat JWT token berisi user_id dan role."""
    expire  = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
 
 
# ── Dependencies ──────────────────────────────────────────────────────────────
 
def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Decode token → return User object."""
    from app.user.user_model import User
 
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak ditemukan, silakan login",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid atau sudah expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
 
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User tidak ditemukan")
    return user
 
 
def require_admin(current_user=Depends(get_current_user)):
    """Dependency — hanya admin yang boleh akses."""
    from app.user.user_model import UserRole
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak — hanya admin",
        )
    return current_user
 
 
def get_current_merchant(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dependency — hanya merchant yang boleh akses. Return object Merchant."""
    from app.user.user_model import UserRole
    from app.merchant.merchant_model import Merchant
 
    if current_user.role != UserRole.MERCHANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak — hanya merchant",
        )
    merchant = db.query(Merchant).filter(Merchant.user_id == current_user.id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Data merchant tidak ditemukan")
    return merchant