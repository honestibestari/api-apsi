from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class PaymentMethodCreate(BaseModel):
    nama_metode: str
    fee:         str = ""

    @field_validator("nama_metode")
    @classmethod
    def tidak_kosong(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nama metode tidak boleh kosong")
        return v


class PaymentMethodUpdate(BaseModel):
    """Semua field opsional — dipakai untuk toggle aktif atau ubah fee/nama."""
    nama_metode: Optional[str]  = None
    fee:         Optional[str]  = None
    is_active:   Optional[bool] = None


class PaymentMethodOut(BaseModel):
    id:          int
    nama_metode: str
    is_active:   bool
    fee:         str
    model_config = ConfigDict(from_attributes=True)