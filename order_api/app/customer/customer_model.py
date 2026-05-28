from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Customer(Base):
    """Pelanggan. Satu pelanggan bisa punya banyak CustomerOrder (struk global)."""

    __tablename__ = "customers"

    id         = Column(Integer, primary_key=True, index=True)
    nama       = Column(String(100), nullable=False)
    email      = Column(String(150), unique=True, index=True, nullable=True)
    phone      = Column(String(30), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    orders = relationship("CustomerOrder", back_populates="customer")