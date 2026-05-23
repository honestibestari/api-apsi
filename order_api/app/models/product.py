from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    nama = Column(String, nullable=False, index=True)
    deskripsi = Column(String)
    harga = Column(Float, nullable=False)
    stok = Column(Integer, default=0)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Setiap product dimiliki oleh satu merchant.
    merchant = relationship("Merchant", back_populates="products")
