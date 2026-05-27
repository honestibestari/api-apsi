from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Customer(Base):
    """Pelanggan. Satu pelanggan memiliki banyak customer order (1 struk global per order).

    Catatan: sengaja tidak ada router/endpoint khusus customer — entitas ini hanya
    dipakai sebagai relasi dari CustomerOrder.
    """
    __tablename__ = "customers"

    id         = Column(Integer, primary_key=True, index=True)
    nama       = Column(String(100), nullable=False)
    email      = Column(String(150), index=True)
    phone      = Column(String(30))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    orders = relationship("CustomerOrder", back_populates="customer")
