from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class PaymentMethodCreate(BaseModel):
    nama_metode: str
    # Kode channel Tripay (mis. "QRIS", "BRIVA"). Kosongkan untuk metode lokal.
    tripay_code: Optional[str] = None

    @field_validator("nama_metode")
    @classmethod
    def tidak_kosong(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nama metode tidak boleh kosong")
        return v


class PaymentMethodUpdate(BaseModel):
    """Semua field opsional — dipakai untuk toggle aktif / ubah nama / set kode Tripay."""
    nama_metode: Optional[str]  = None
    is_active:   Optional[bool] = None
    # Set string kosong "" untuk melepas kode Tripay (metode kembali lokal).
    tripay_code: Optional[str]  = None


class PaymentMethodOut(BaseModel):
    id:          int
    nama_metode: str
    is_active:   bool
    tripay_code: Optional[str]   = None
    fee_flat:    Optional[float] = None
    fee_percent: Optional[float] = None
    model_config = ConfigDict(from_attributes=True)


class TripaySyncResult(BaseModel):
    """Hasil sinkronisasi metode pembayaran dari daftar channel Tripay."""
    added:       int
    updated:     int
    deactivated: int
    methods:     list[PaymentMethodOut]