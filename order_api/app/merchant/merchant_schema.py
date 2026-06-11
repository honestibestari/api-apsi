from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, field_validator

from app.merchant.merchant_model import MerchantStatus
from app.product.product_schema import ProductSummary


# Input
class MerchantCreate(BaseModel):
    """Body request untuk membuat merchant baru (POST /merchants)."""

    nama: str
    deskripsi: Optional[str] = None
    alamat: Optional[str] = None
    owner: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    block: Optional[str] = None
    category: Optional[str] = None
    status: MerchantStatus = MerchantStatus.PENDING

    @field_validator("nama")
    @classmethod
    def nama_tidak_kosong(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nama merchant tidak boleh kosong")
        return v


class MerchantUpdate(BaseModel):
    """Body request untuk update merchant (PUT /merchants/{id}).
    Semua field opsional → client hanya kirim field yang berubah (partial update).
    Untuk approve/suspend dari admin cukup kirim { "status": "active" }.
    """

    nama: Optional[str] = None
    deskripsi: Optional[str] = None
    alamat: Optional[str] = None
    owner: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    block: Optional[str] = None
    category: Optional[str] = None
    status: Optional[MerchantStatus] = None

    @field_validator("nama")
    @classmethod
    def nama_tidak_kosong(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Nama merchant tidak boleh kosong")
        return v


# Output
class MerchantSummary(BaseModel):
    """Bentuk ringkas untuk list merchant / nested di dalam detail product.
    Mencakup profil & ringkasan finansial yang dipakai konsol admin.
    """

    id: int
    nama: str
    alamat: Optional[str] = None
    owner: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    block: Optional[str] = None
    category: Optional[str] = None
    foto: Optional[str] = None
    status: MerchantStatus
    rating: float
    total_orders: int
    total_revenue: float
    balance: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MerchantDetail(BaseModel):
    """Detail merchant, beserta daftar product yang dijual."""

    id: int
    nama: str
    deskripsi: Optional[str] = None
    alamat: Optional[str] = None
    owner: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    block: Optional[str] = None
    category: Optional[str] = None
    foto: Optional[str] = None
    status: MerchantStatus
    rating: float
    total_orders: int
    total_revenue: float
    balance: float
    created_at: datetime
    products: List[ProductSummary] = []

    model_config = ConfigDict(from_attributes=True)
