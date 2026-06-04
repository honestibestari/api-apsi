from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
 
from app.core.database import Base
 
 
class Review(Base):
    __tablename__ = "reviews"
 
    id          = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    pelanggan   = Column(String(100), nullable=True)  # fallback untuk data lama
    rating      = Column(Integer, nullable=False)      # 1-5
    komentar    = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
 
    merchant = relationship("Merchant", back_populates="reviews")
    customer = relationship("Customer", back_populates="reviews")