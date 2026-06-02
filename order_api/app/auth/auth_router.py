from typing import Optional
 
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
 
from app.core.auth import create_token, hash_password, verify_password
from app.core.database import get_db
from app.admin.admin_model import Admin
from app.merchant.merchant_model import Merchant, MerchantStatus
from app.user.user_model import User
from app.user.user_model import UserRole
 
router = APIRouter(prefix="/auth", tags=["Auth"])
 
 
# ── Schema ────────────────────────────────────────────────────────────────────
 
class LoginRequest(BaseModel):
    identifier: str   # email atau nomor HP
    password:   str
 
 
class RegisterRequest(BaseModel):
    nama:      str
    identifier: str   # email atau nomor HP
    password:  str
    owner:     Optional[str] = None
    alamat:    Optional[str] = None
    block:     Optional[str] = None
    category:  Optional[str] = None
    deskripsi: Optional[str] = None
 
 
# ── Login — detect admin atau merchant otomatis ───────────────────────────────
 
@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):

    # cari user berdasarkan email
    user = (
        db.query(User)
        .filter(User.email == data.identifier)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User tidak ditemukan"
        )

    if not verify_password(
        data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Password salah"
        )

    token = create_token(
        user_id=user.id,
        role=user.role.value
    )

    # ==========================
    # ADMIN
    # ==========================
    if user.role == UserRole.ADMIN:

        admin = (
            db.query(Admin)
            .filter(Admin.user_id == user.id)
            .first()
        )

        if not admin:
            raise HTTPException(
                status_code=404,
                detail="Data admin tidak ditemukan"
            )

        return {
            "access_token": token,
            "token_type": "bearer",
            "role": user.role.value,
            "id": admin.id,
            "nama": admin.nama,
        }

    # ==========================
    # MERCHANT
    # ==========================
    merchant = (
        db.query(Merchant)
        .filter(Merchant.user_id == user.id)
        .first()
    )

    if not merchant:
        raise HTTPException(
            status_code=404,
            detail="Data merchant tidak ditemukan"
        )

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role.value,
        "id": merchant.id,
        "nama": merchant.nama,
        "status": merchant.status,
    }
 
# ── Register Merchant ─────────────────────────────────────────────────────────
 
@router.post("/register", status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):

    # cek email sudah ada di users
    existing_user = (
        db.query(User)
        .filter(User.email == data.identifier)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Email sudah terdaftar"
        )

    # buat user
    user = User(
        username=data.nama.lower().replace(" ", ""),
        email=data.identifier,
        password_hash=hash_password(data.password),
        role=UserRole.MERCHANT
    )

    db.add(user)
    db.flush()

    # buat merchant
    merchant = Merchant(
        user_id=user.id,
        nama=data.nama,
        email=data.identifier,
        phone=None,
        password_hash=user.password_hash,
        owner=data.owner,
        alamat=data.alamat,
        block=data.block,
        category=data.category,
        deskripsi=data.deskripsi,
        status=MerchantStatus.ACTIVE,
    )

    db.add(merchant)

    db.commit()
    db.refresh(merchant)

    return {
        "message": "Merchant berhasil didaftarkan",
        "user_id": user.id,
        "merchant_id": merchant.id,
        "role": user.role.value,
        "nama": merchant.nama,
        "status": merchant.status,
    }