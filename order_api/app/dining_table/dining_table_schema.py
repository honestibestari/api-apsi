from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class DiningTableCreate(BaseModel):
    label:     str
    is_active: bool = True

    @field_validator("label")
    @classmethod
    def label_tidak_kosong(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Label meja tidak boleh kosong")
        return v


class DiningTableUpdate(BaseModel):
    """Field opsional — untuk rename label atau toggle aktif."""
    label:     Optional[str]  = None
    is_active: Optional[bool] = None


class DiningTableOut(BaseModel):
    id:         int
    code:       str
    label:      str
    is_active:  bool
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
