from typing import Optional
from pydantic import BaseModel, ConfigDict


class TenantSettingsUpdate(BaseModel):
    bahasa:       Optional[str]  = None
    notif_order:  Optional[bool] = None
    notif_ulasan: Optional[bool] = None
    bisa_edit:    Optional[bool] = None


class TenantSettingsOut(BaseModel):
    id:           int
    id_tenant:    int
    bahasa:       str
    notif_order:  bool
    notif_ulasan: bool
    bisa_edit:    bool
    model_config = ConfigDict(from_attributes=True)