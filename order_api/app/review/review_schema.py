from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class ReviewCreate(BaseModel):
    merchant_id:       int
    customer_order_id: Optional[int] = None
    rating:            int
    komentar:          Optional[str] = None
    pelanggan:         Optional[str] = None

    @field_validator("rating")
    @classmethod
    def rating_valid(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("Rating harus 1..5")
        return v


class ReviewOut(BaseModel):
    id:                int
    merchant_id:       int
    customer_order_id: Optional[int] = None
    rating:            int
    komentar:          Optional[str] = None
    pelanggan_nama:    Optional[str] = None
    created_at:        datetime

    model_config = ConfigDict(from_attributes=True)
