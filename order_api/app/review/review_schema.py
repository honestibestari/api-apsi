from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


class ReviewCreate(BaseModel):
    merchant_id: int
    customer_id: Optional[int] = None
    pelanggan:   Optional[str] = None   
    rating:      int
    komentar:    Optional[str] = None

    @field_validator("rating")
    @classmethod
    def rating_valid(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("Rating harus antara 1 sampai 5")
        return v


class ReviewOut(BaseModel):
    id:          int
    merchant_id: int
    customer_id: Optional[int] = None
    pelanggan:   Optional[str] = None
    rating:      int
    komentar:    Optional[str] = None
    created_at:  datetime
    model_config = ConfigDict(from_attributes=True)