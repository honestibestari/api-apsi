from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


class CategoryCreate(BaseModel):
    nama_kategori: str

    @field_validator("nama_kategori")
    @classmethod
    def tidak_kosong(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nama kategori tidak boleh kosong")
        return v


class CategoryUpdate(BaseModel):
    nama_kategori: Optional[str] = None


class CategoryOut(BaseModel):
    id:            int
    nama_kategori: str
    model_config = ConfigDict(from_attributes=True)