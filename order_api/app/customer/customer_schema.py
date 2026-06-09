from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


class CustomerCreate(BaseModel):
    nama:  str
    email: Optional[str] = None
    phone: Optional[str] = None
    no_wa: Optional[str] = None

    @field_validator("nama")
    @classmethod
    def nama_tidak_kosong(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nama tidak boleh kosong")
        return v


class CustomerUpdate(BaseModel):
    nama:        Optional[str] = None
    email:       Optional[str] = None
    phone:       Optional[str] = None
    no_wa:       Optional[str] = None
    minta_struk: Optional[bool] = None
    flagged:     Optional[bool] = None


class CustomerOut(BaseModel):
    id:            int
    nama:          str
    email:         Optional[str] = None
    phone:         Optional[str] = None
    no_wa:         Optional[str] = None
    minta_struk:   bool
    flagged:       bool
    created_at:    datetime
    updated_at:    Optional[datetime] = None
    # Agregat turunan (dari property model) untuk konsol admin.
    total_orders:  int = 0
    total_spent:   float = 0.0
    last_order_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CustomerSummary(BaseModel):
    id:    int
    nama:  str
    email: Optional[str] = None
    phone: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)