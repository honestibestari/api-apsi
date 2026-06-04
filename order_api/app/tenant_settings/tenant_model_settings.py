from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
 
from app.core.database import Base
 
 
class TenantSettings(Base):
    __tablename__ = "tenant_settings"
 
    id           = Column(Integer, primary_key=True, index=True)
    id_tenant    = Column(Integer, ForeignKey("merchants.id"), unique=True, nullable=False)
    bahasa       = Column(String(10), nullable=False, default="id")
    notif_order  = Column(Boolean, nullable=False, default=True)
    notif_ulasan = Column(Boolean, nullable=False, default=True)
    bisa_edit    = Column(Boolean, nullable=False, default=True)
 
    tenant = relationship("Merchant", back_populates="tenant_settings")