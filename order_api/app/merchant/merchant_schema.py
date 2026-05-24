from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.product.product_schema import ProductSummary


class MerchantBase(BaseModel):
    nama: str
    deskripsi: Optional[str] = None
    alamat: Optional[str] = None


class MerchantSummary(BaseModel):
    """Bentuk ringkas untuk list merchant / nested di dalam detail product."""

    id: int
    nama: str
    alamat: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MerchantDetail(MerchantBase):
    """Detail merchant, beserta daftar product yang dijual."""

    id: int
    created_at: datetime
    products: List[ProductSummary] = []

    model_config = ConfigDict(from_attributes=True)
