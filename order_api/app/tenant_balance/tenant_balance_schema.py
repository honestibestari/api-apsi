from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class TenantBalanceOut(BaseModel):
    id:              int
    id_tenant:       int
    total_saldo:     float
    total_pending:   float
    total_dicairkan: float
    updated_at:      Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)