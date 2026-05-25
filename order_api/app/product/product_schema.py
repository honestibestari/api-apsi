from datetime import datetime
from typing import TYPE_CHECKING, Optional
from pydantic import BaseModel, ConfigDict, field_validator
 
if TYPE_CHECKING:
    from app.merchant.merchant_schema import MerchantSummary
 
 
# Input
class ProductCreate(BaseModel):
    """Body request untuk membuat product baru (POST /products)."""

    nama: str
    deskripsi: Optional[str] = None
    harga: float
    stok: int = 0
    merchant_id: int
 
    @field_validator("nama")
    @classmethod
    def nama_tidak_kosong(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nama product tidak boleh kosong")
        return v
 
    @field_validator("harga")
    @classmethod
    def harga_positif(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Harga harus lebih dari 0")
        return v
 
    @field_validator("stok")
    @classmethod
    def stok_non_negatif(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Stok tidak boleh negatif")
        return v
 
 
class ProductUpdate(BaseModel):
    """Body request untuk update product (PUT /products/{id})."""
 
    nama: Optional[str] = None
    deskripsi: Optional[str] = None
    harga: Optional[float] = None
    stok: Optional[int] = None
 
    @field_validator("nama")
    @classmethod
    def nama_tidak_kosong(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Nama product tidak boleh kosong")
        return v
 
    @field_validator("harga")
    @classmethod
    def harga_positif(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("Harga harus lebih dari 0")
        return v
 
    @field_validator("stok")
    @classmethod
    def stok_non_negatif(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Stok tidak boleh negatif")
        return v
 
 
# Output 
class ProductSummary(BaseModel):
    """Bentuk ringkas untuk list product / nested di dalam detail merchant."""
 
    id: int
    nama: str
    harga: float
    stok: int
    merchant_id: int
 
    model_config = ConfigDict(from_attributes=True)
 
 
class ProductDetail(BaseModel):
    """Detail product, beserta info merchant pemiliknya."""
 
    id: int
    nama: str
    deskripsi: Optional[str] = None
    harga: float
    stok: int
    merchant_id: int
    created_at: datetime
    merchant: "MerchantSummary"
 
    model_config = ConfigDict(from_attributes=True)