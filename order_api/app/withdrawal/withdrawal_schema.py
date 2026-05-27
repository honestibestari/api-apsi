from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.withdrawal.withdrawal_model import WithdrawalStatus


class WithdrawalCreate(BaseModel):
    merchant_id:    int
    amount:         float
    bank:           Optional[str] = None
    account_number: Optional[str] = None
    account_name:   Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_positif(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Jumlah penarikan harus lebih dari 0")
        return v


class WithdrawalProcess(BaseModel):
    """Approve / reject permintaan penarikan."""
    status: WithdrawalStatus
    note:   Optional[str] = None

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: WithdrawalStatus) -> WithdrawalStatus:
        if v not in (WithdrawalStatus.APPROVED, WithdrawalStatus.REJECTED):
            raise ValueError("Status hanya boleh approved atau rejected")
        return v


class WithdrawalOut(BaseModel):
    id:             int
    merchant_id:    int
    merchant_nama:  Optional[str] = None
    amount:         float
    status:         WithdrawalStatus
    bank:           Optional[str] = None
    account_number: Optional[str] = None
    account_name:   Optional[str] = None
    note:           Optional[str] = None
    requested_at:   datetime
    processed_at:   Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
