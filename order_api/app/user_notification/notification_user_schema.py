from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class NotificationUserOut(BaseModel):
    id:        int
    id_tenant: Optional[int] = None
    id_user:   int
    judul:     str
    isi:       str
    is_read:   bool
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)


class NotificationUserMarkRead(BaseModel):
    ids: List[int]