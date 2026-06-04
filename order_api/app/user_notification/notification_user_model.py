 
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
 
from app.core.database import Base
 
 
class NotificationUser(Base):
    __tablename__ = "notification_user"
 
    id        = Column(Integer, primary_key=True, index=True)
    id_tenant = Column(Integer, ForeignKey("merchants.id"), nullable=True)
    id_user   = Column(Integer, ForeignKey("customers.id"), nullable=False)
    judul     = Column(String(200), nullable=False)
    isi       = Column(Text, nullable=False)
    is_read   = Column(Boolean, nullable=False, default=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
 
    tenant = relationship("Merchant")
    user = relationship("Customer", back_populates="notifications")