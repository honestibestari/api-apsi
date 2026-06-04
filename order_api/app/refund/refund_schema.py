from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator
from app.refund.refund_model import StatusRefund


class RefundCreate(BaseModel):
    id_pesanan:    int
    nominal:       float
    metode_refund: Optional[str] = None
    nomor_tujuan:  Optional[str] = None

    @field_validator("nominal")
    @classmethod
    def nominal_positif(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Nominal harus lebih dari 0")
        return v


class RefundOut(BaseModel):
    id:            int
    id_pesanan:    int
    nominal:       float
    metode_refund: Optional[str] = None
    nomor_tujuan:  Optional[str] = None
    status:        StatusRefund
    timestamp:     datetime
    model_config = ConfigDict(from_attributes=True)