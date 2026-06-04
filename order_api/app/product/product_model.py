from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id          = Column(Integer, primary_key=True, index=True)
    nama        = Column(String(100), nullable=False, index=True)
    deskripsi   = Column(String, nullable=True)
    foto        = Column(String, nullable=True)
    harga       = Column(Float, nullable=False)
    stok        = Column(Integer, nullable=False, default=0)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    # Relasi
    merchant = relationship("Merchant", back_populates="products")
    category = relationship("Category", back_populates="products")