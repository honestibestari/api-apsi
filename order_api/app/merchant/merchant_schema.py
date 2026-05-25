from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, field_validator

from app.product.product_schema import ProductSummary


# Input
class MerchantCreate(BaseModel):
    """Body request untuk membuat merchant baru (POST /merchants)."""

    nama: str
    deskripsi: Optional[str] = None
    alamat: Optional[str] = None

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
    """

    nama: Optional[str] = None
    deskripsi: Optional[str] = None
    alamat: Optional[str] = None

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
    """Bentuk ringkas untuk list merchant / nested di dalam detail product."""

    id: int
    nama: str
    alamat: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MerchantDetail(BaseModel):
    """Detail merchant, beserta daftar product yang dijual."""

    id: int
    nama: str
    deskripsi: Optional[str] = None
    alamat: Optional[str] = None
    created_at: datetime
    products: List[ProductSummary] = []

    model_config = ConfigDict(from_attributes=True)