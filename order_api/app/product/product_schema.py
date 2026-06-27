from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from pydantic import BaseModel, ConfigDict, field_validator

if TYPE_CHECKING:
    from app.merchant.merchant_schema import MerchantSummary


class CategoryInfo(BaseModel):
    id:            int
    nama_kategori: str
    model_config = ConfigDict(from_attributes=True)


# ── Item tambahan (add-on) ───────────────────────────────────────────────────

class AddonIn(BaseModel):
    nama:      str
    harga:     float = 0.0
    is_active: bool  = True

    @field_validator("nama")
    @classmethod
    def nama_tidak_kosong(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Nama item tambahan tidak boleh kosong")
        return v

    @field_validator("harga")
    @classmethod
    def harga_non_negatif(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Harga item tambahan tidak boleh negatif")
        return v


class AddonOut(BaseModel):
    id:        int
    nama:      str
    harga:     float
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    nama:        str
    deskripsi:   Optional[str] = None
    foto:        Optional[str] = None
    harga:       float
    stok:        int = 0
    is_available: bool = True
    merchant_id: int
    category_id: Optional[int] = None
    additionals: Optional[List[AddonIn]] = None

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
    nama:        Optional[str]   = None
    deskripsi:   Optional[str]   = None
    foto:        Optional[str]   = None
    harga:       Optional[float] = None
    stok:        Optional[int]   = None
    is_available: Optional[bool] = None
    category_id: Optional[int]   = None
    additionals: Optional[List[AddonIn]] = None

    @field_validator("stok")
    @classmethod
    def stok_non_negatif(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Stok tidak boleh negatif")
        return v

    @field_validator("harga")
    @classmethod
    def harga_positif(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("Harga harus lebih dari 0")
        return v


class ProductBan(BaseModel):
    """Body request admin untuk blokir/buka-blokir produk (PUT /products/{id}/ban)."""
    is_banned: bool


class ProductSummary(BaseModel):
    id:          int
    nama:        str
    harga:       float
    stok:        int
    is_available: bool = True
    is_banned:   bool = False
    merchant_id: int
    category_id: Optional[int]      = None
    category:    Optional[CategoryInfo] = None
    foto: Optional[str] = None
    additionals: List[AddonOut] = []
    model_config = ConfigDict(from_attributes=True)


class ProductDetail(BaseModel):
    id:          int
    nama:        str
    deskripsi:   Optional[str]      = None
    foto:        Optional[str]      = None
    harga:       float
    stok:        int
    is_available: bool = True
    is_banned:   bool = False
    merchant_id: int
    category_id: Optional[int]      = None
    category:    Optional[CategoryInfo] = None
    additionals: List[AddonOut] = []
    created_at:  datetime
    merchant:    "MerchantSummary"
    model_config = ConfigDict(from_attributes=True)