from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Attachment(Base):
    __tablename__ = "attachments"

    id          = Column(Integer, primary_key=True, index=True)
    url         = Column(String(500), nullable=False)       # URL dari Vercel Blob
    filename    = Column(String(200), nullable=False)       # nama file asli
    content_type = Column(String(100), nullable=True)       # image/jpeg, image/png, dll
    size        = Column(Integer, nullable=True)            # ukuran file dalam bytes
    uploaded_by = Column(Integer, ForeignKey("merchants.id"), nullable=True)  
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    uploader = relationship("Merchant")