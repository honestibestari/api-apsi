from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
 
from app.core.database import Base
 
 
class Category(Base):
    __tablename__ = "categories"
 
    id            = Column(Integer, primary_key=True, index=True)
    nama_kategori = Column(String(100), nullable=False)
    id_tenant     = Column(Integer, ForeignKey("merchants.id"), nullable=False)
 
    tenant   = relationship("Merchant", back_populates="categories")
    products = relationship("Product", back_populates="category")