from pydantic import BaseModel, ConfigDict, field_validator


class PaymentMethodCreate(BaseModel):
    nama_metode: str

    @field_validator("nama_metode")
    @classmethod
    def tidak_kosong(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nama metode tidak boleh kosong")
        return v


class PaymentMethodOut(BaseModel):
    id:          int
    nama_metode: str
    model_config = ConfigDict(from_attributes=True)