from typing import Optional
 
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
 
from app.core.auth import create_token, hash_password, verify_password
from app.core.database import get_db
from app.user.user_model import User, UserRole
from app.merchant.merchant_model import Merchant, MerchantStatus
 
router = APIRouter(prefix="/auth", tags=["Auth"])
 
 
# ── Schema ────────────────────────────────────────────────────────────────────
 
class LoginRequest(BaseModel):
    identifier: str   # email, username, atau nomor HP merchant
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
 
 
# ── Login ─────────────────────────────────────────────────────────────────────
 
@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """
    Login untuk admin dan merchant. Role dideteksi otomatis.
 
    Admin login pakai email:
    { "identifier": "admin@orderapi.com", "password": "admin123" }
 
    Merchant login pakai email atau nomor HP:
    { "identifier": "rinaseblak@gmail.com", "password": "password123" }
    { "identifier": "0812-3456-7890",       "password": "password123" }
    """
    user = None
 
    # 1. Cari by email di tabel User
    user = db.query(User).filter(User.email == data.identifier).first()
 
    # 2. Cari by username di tabel User
    if not user:
        user = db.query(User).filter(User.username == data.identifier).first()
 
    # 3. Khusus merchant — cari by nomor HP di tabel Merchant
    if not user:
        merchant = db.query(Merchant).filter(Merchant.phone == data.identifier).first()
        if merchant and merchant.user_id:
            user = db.query(User).filter(User.id == merchant.user_id).first()
 
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email/No HP atau password salah")
 
    token = create_token(user_id=user.id, role=user.role.value)
 
    response = {
        "access_token": token,
        "token_type":   "bearer",
        "role":         user.role,
        "user_id":      user.id,
        "email":        user.email,
    }
 
    # Tambah info merchant jika role merchant
    if user.role == UserRole.MERCHANT and user.merchant:
        response["merchant_id"] = user.merchant.id
        response["nama"]        = user.merchant.nama
        response["status"]      = user.merchant.status
 
    # Tambah info admin jika role admin
    if user.role == UserRole.ADMIN and user.admin:
        response["nama"] = user.admin.nama
 
    return response
 
 
# ── Register Merchant ─────────────────────────────────────────────────────────
 
@router.post("/register", status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    is_email = "@" in data.identifier

    # Cek duplikat
    existing_user = db.query(User).filter(User.email == data.identifier).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Email sudah terdaftar")

    if not is_email:
        existing_phone = db.query(Merchant).filter(Merchant.phone == data.identifier).first()
        if existing_phone:
            raise HTTPException(status_code=409, detail="Nomor HP sudah terdaftar")

    # 1. Buat User dulu
    username = data.identifier.split("@")[0] if is_email else data.identifier.replace("-", "")
    hashed   = hash_password(data.password)

    user = User(
        username      = username,
        email         = data.identifier if is_email else f"{username}@merchant.local",
        password_hash = hashed,
        role          = UserRole.MERCHANT,
    )
    db.add(user)
    db.flush()  # ← wajib ada agar user.id tersedia sebelum buat Merchant

    # 2. Buat Merchant pakai user.id
    merchant = Merchant(
        user_id       = user.id,           # ← dari user yang baru dibuat
        password_hash = hashed,            # ← sama dengan user
        nama          = data.nama,
        email         = data.identifier if is_email else None,
        phone         = data.identifier if not is_email else None,
        owner         = data.owner,
        alamat        = data.alamat,
        block         = data.block,
        category      = data.category,
        deskripsi     = data.deskripsi,
        status        = MerchantStatus.ACTIVE,
    )
    db.add(merchant)
    db.commit()
    db.refresh(merchant)

    return {
        "message":     "Merchant berhasil didaftarkan",
        "user_id":     user.id,
        "merchant_id": merchant.id,
        "nama":        merchant.nama,
        "role":        user.role,
    }