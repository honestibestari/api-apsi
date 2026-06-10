from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Category(Base):
    """Kategori produk — GLOBAL, dikelola admin (tidak menempel ke merchant)."""

    __tablename__ = "categories"

    id            = Column(Integer, primary_key=True, index=True)
    nama_kategori = Column(String(100), nullable=False, unique=True)

    products = relationship("Product", back_populates="category")