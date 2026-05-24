from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProductBase(BaseModel):
    nama: str
    deskripsi: Optional[str] = None
    harga: float
    stok: int = 0


class ProductSummary(BaseModel):
    """Bentuk ringkas untuk list product / nested di dalam detail merchant."""

    id: int
    nama: str
    harga: float
    stok: int
    merchant_id: int

    model_config = ConfigDict(from_attributes=True)


class ProductDetail(ProductBase):
    """Detail product, beserta info merchant pemiliknya."""

    id: int
    merchant_id: int
    created_at: datetime
    # Forward reference; di-resolve di app/__init__.py untuk menghindari
    # circular import dengan modul merchant.
    merchant: "MerchantSummary"

    model_config = ConfigDict(from_attributes=True)
