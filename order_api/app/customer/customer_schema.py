from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


# ── Input ─────────────────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    """Body POST /customers — buat customer baru."""
    nama:  str
    email: Optional[EmailStr] = None
    phone: Optional[str]      = None

    @field_validator("nama")
    @classmethod
    def nama_tidak_kosong(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nama tidak boleh kosong")
        return v


class CustomerUpdate(BaseModel):
    """Body PUT /customers/{id} — partial update, semua field opsional."""
    nama:  Optional[str]      = None
    email: Optional[EmailStr] = None
    phone: Optional[str]      = None

    @field_validator("nama")
    @classmethod
    def nama_tidak_kosong(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Nama tidak boleh kosong")
        return v


# ── Output ────────────────────────────────────────────────────────────────────

class CustomerOut(BaseModel):
    """Response detail customer — dipakai GET /customers/{id}."""
    id:         int
    nama:       str
    email:      Optional[str]
    phone:      Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class CustomerSummary(BaseModel):
    """Ringkasan customer — dipakai di list GET /customers."""
    id:          int
    nama:        str
    email:       Optional[str]
    phone:       Optional[str]
    total_orders: int = 0       # jumlah CustomerOrder milik customer ini
    created_at:  datetime

    model_config = ConfigDict(from_attributes=True)