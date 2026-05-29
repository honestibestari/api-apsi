from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.merchant.merchant_model import Merchant

SECRET_KEY = "hjswbvgfjewht48whsdkvgds"  # simpan di .env
ALGORITHM  = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 hari

pwd_context   = CryptContext(schemes=["bcrypt"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(merchant_id: int) -> str:
    """Buat JWT token berisi merchant_id."""
    expire  = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(merchant_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_merchant(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Merchant:
    """Dependency — decode token, ambil merchant dari DB.
    
    Dipasang di endpoint yang butuh login.
    Otomatis return 401 jika token tidak valid.
    """
    try:
        payload     = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        merchant_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid atau sudah expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=401, detail="Merchant tidak ditemukan")

    return merchant