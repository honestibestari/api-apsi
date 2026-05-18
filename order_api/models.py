from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

class CategoryEnum(str, enum.Enum):
    makanan = "makanan"
    minuman = "minuman"

class StatusEnum(str, enum.Enum):
    pending = "pending"
    diproses = "diproses"
    selesai = "selesai"
    dibatalkan = "dibatalkan"

class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    nama = Column(String, index=True, nullable=False)
    kategori = Column(Enum(CategoryEnum), nullable=False)
    harga = Column(Float, nullable=False)
    deskripsi = Column(String)
    tersedia = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order_items = relationship("OrderItem", back_populates="menu_item")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    nama_pelanggan = Column(String, nullable=False)
    nomor_meja = Column(Integer, nullable=False)
    status = Column(Enum(StatusEnum), default=StatusEnum.pending)
    total_harga = Column(Float, default=0.0)
    catatan = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    jumlah = Column(Integer, nullable=False, default=1)
    harga_satuan = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem", back_populates="order_items")