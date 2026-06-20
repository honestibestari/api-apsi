from datetime import datetime
from typing import Optional, TYPE_CHECKING
from pydantic import BaseModel, ConfigDict, field_validator

if TYPE_CHECKING:
    from app.merchant.merchant_schema import MerchantSummary


class CategoryInfo(BaseModel):
    id:            int
    nama_kategori: str
    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    nama:        str
    deskripsi:   Optional[str] = None
    foto:        Optional[str] = None
    harga:       float
    stok:        int = 0
    merchant_id: int
    category_id: Optional[int] = None   

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
    category_id: Optional[int]   = None

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


class ProductSummary(BaseModel):
    id:          int
    nama:        str
    harga:       float
    stok:        int
    merchant_id: int
    category_id: Optional[int]      = None   
    category:    Optional[CategoryInfo] = None  
    foto: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ProductDetail(BaseModel):
    id:          int
    nama:        str
    deskripsi:   Optional[str]      = None
    foto:        Optional[str]      = None
    harga:       float
    stok:        int
    merchant_id: int
    category_id: Optional[int]      = None   
    category:    Optional[CategoryInfo] = None  
    created_at:  datetime
    merchant:    "MerchantSummary"
    model_config = ConfigDict(from_attributes=True)