from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, index=True)
    nama = Column(String, nullable=False, index=True)
    deskripsi = Column(String)
    alamat = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Satu merchant punya banyak product.
    products = relationship(
        "Product", back_populates="merchant", cascade="all, delete-orphan"
    )
