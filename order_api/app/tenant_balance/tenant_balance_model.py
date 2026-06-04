from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
 
from app.core.database import Base
 
 
class TenantBalance(Base):
    __tablename__ = "tenant_balance"
 
    id              = Column(Integer, primary_key=True, index=True)
    id_tenant       = Column(Integer, ForeignKey("merchants.id"), unique=True, nullable=False)
    total_saldo     = Column(Float, nullable=False, default=0.0)
    total_pending   = Column(Float, nullable=False, default=0.0)
    total_dicairkan = Column(Float, nullable=False, default=0.0)
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())
 
    tenant = relationship("Merchant", back_populates="tenant_balance")
 