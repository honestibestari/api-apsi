from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AttachmentOut(BaseModel):
    id:           int
    url:          str
    filename:     str
    content_type: Optional[str] = None
    size:         Optional[int] = None
    entity_type:  str
    entity_id:    int
    uploaded_by:  Optional[int] = None
    created_at:   datetime
    model_config = ConfigDict(from_attributes=True)
