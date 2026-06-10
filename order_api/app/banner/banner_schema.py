from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class BannerCreate(BaseModel):
    title:        str
    subtitle:     str = ""
    badge:        str = ""
    image_url:    str = ""
    bg:           str = ""
    accent_color: str = ""
    sort_order:   int = 0
    is_active:    bool = True

    @field_validator("title")
    @classmethod
    def title_tidak_kosong(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Judul banner tidak boleh kosong")
        return v


class BannerUpdate(BaseModel):
    title:        Optional[str]  = None
    subtitle:     Optional[str]  = None
    badge:        Optional[str]  = None
    image_url:    Optional[str]  = None
    bg:           Optional[str]  = None
    accent_color: Optional[str]  = None
    sort_order:   Optional[int]  = None
    is_active:    Optional[bool] = None


class BannerOut(BaseModel):
    id:           int
    title:        str
    subtitle:     str
    badge:        str
    image_url:    str
    bg:           str
    accent_color: str
    sort_order:   int
    is_active:    bool
    created_at:   Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
