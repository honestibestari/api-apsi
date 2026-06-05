from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


class WithdrawalCreate(BaseModel):
    amount:         float
    bank:           str
    account_number: str
    account_name:   str

    @field_validator("amount")
    @classmethod
    def amount_positif(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Jumlah penarikan harus lebih dari 0")
        return v


class WithdrawalOut(BaseModel):
    id:             int
    merchant_id:    int
    amount:         float
    status:         str
    bank:           str
    account_number: str
    account_name:   str
    note:           Optional[str] = None
    processed_at:   Optional[datetime] = None
    requested_at:     datetime
    model_config = ConfigDict(from_attributes=True)