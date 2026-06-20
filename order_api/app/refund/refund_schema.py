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


class RefundProcess(BaseModel):
    """Pilihan customer: metode e-wallet + nomor tujuan. Memfinalkan refund."""
    metode_refund: str
    nomor_tujuan:  str

    @field_validator("metode_refund", "nomor_tujuan")
    @classmethod
    def tidak_kosong(cls, v: str) -> str:
        if not (v or "").strip():
            raise ValueError("Wajib diisi")
        return v.strip()