from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import create_token, hash_password, verify_password
from app.core.database import get_db
from app.merchant.merchant_model import Merchant, MerchantStatus

router = APIRouter(prefix="/auth", tags=["Auth"])


# ── Schema ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    identifier: str   # email atau nomor HP
    password:   str


class RegisterRequest(BaseModel):
    nama:       str
    identifier: str   # email atau nomor HP
    password:   str
    owner:      Optional[str] = None
    alamat:     Optional[str] = None
    block:      Optional[str] = None
    category:   Optional[str] = None
    deskripsi:  Optional[str] = None


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """
    Login dengan email atau nomor HP + password.

    Body:
    { "identifier": "rinaseblak@gmail.com", "password": "password123" }
    atau
    { "identifier": "0812-3456-7890", "password": "password123" }
    """
    merchant = db.query(Merchant).filter(Merchant.email == data.identifier).first()
    if not merchant:
        merchant = db.query(Merchant).filter(Merchant.phone == data.identifier).first()

    if not merchant or not verify_password(data.password, merchant.password_hash):
        raise HTTPException(status_code=401, detail="Email/No HP atau password salah")

    token = create_token(merchant.id)
    return {
        "access_token": token,
        "token_type":   "bearer",
        "merchant_id":  merchant.id,
        "nama":         merchant.nama,
        "status":       merchant.status,
    }


@router.post("/register", status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """
    Daftarkan merchant baru.

    Body:
    {
        "nama": "Warung Baru",
        "identifier": "warungbaru@gmail.com",
        "password": "password123",
        "owner": "Nama Pemilik",
        "alamat": "Blok A-001",
        "block": "A-001",
        "category": "Makanan",
        "deskripsi": "Warung masakan rumahan"
    }

    Status awal: PENDING (menunggu persetujuan admin sebelum bisa aktif).
    """
    # Cek duplikat email atau nomor HP
    existing = (
        db.query(Merchant)
        .filter(
            (Merchant.email == data.identifier) |
            (Merchant.phone == data.identifier)
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Email atau nomor HP sudah terdaftar")

    merchant = Merchant(
        nama          = data.nama,
        email         = data.identifier if "@" in data.identifier else None,
        phone         = data.identifier if "@" not in data.identifier else None,
        password_hash = hash_password(data.password),
        owner         = data.owner,
        alamat        = data.alamat,
        block         = data.block,
        category      = data.category,
        deskripsi     = data.deskripsi,
        status        = MerchantStatus.PENDING,
    )
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    return {
        "message":     "Merchant berhasil didaftarkan, menunggu persetujuan admin",
        "id":          merchant.id,
        "nama":        merchant.nama,
        "status":      merchant.status,
    }