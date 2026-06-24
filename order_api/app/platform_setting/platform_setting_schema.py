from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class PlatformSettingOut(BaseModel):
    """Bentuk lengkap untuk konsol admin."""
    id:         int
    fee_rate:   float
    fee_fixed:  float
    is_active:  bool
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PlatformSettingUpdate(BaseModel):
    """Field opsional — admin bisa mengubah sebagian saja."""
    fee_rate:  Optional[float] = None
    fee_fixed: Optional[float] = None
    is_active: Optional[bool]  = None

    @field_validator("fee_rate")
    @classmethod
    def rate_wajar(cls, v):
        if v is None:
            return v
        if v < 0 or v > 100:
            raise ValueError("fee_rate harus antara 0 dan 100 (persen)")
        return v

    @field_validator("fee_fixed")
    @classmethod
    def fixed_non_negatif(cls, v):
        if v is None:
            return v
        if v < 0:
            raise ValueError("fee_fixed tidak boleh negatif")
        return v


class PlatformFeePublic(BaseModel):
    """Info ringkas untuk FE customer menampilkan estimasi biaya layanan di cart.

    Tanpa auth — hanya parameter perhitungan, bukan data sensitif.
    """
    fee_rate:  float
    fee_fixed: float
    is_active: bool
