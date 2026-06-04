from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id          = Column(Integer, primary_key=True, index=True)
    nama        = Column(String(100), nullable=False)
    email       = Column(String(150), unique=True, index=True, nullable=True)
    phone       = Column(String(30),  unique=True, index=True, nullable=True)
    no_wa       = Column(String(30),  nullable=True)
    session_id  = Column(String(200), nullable=True)
    expired_id  = Column(DateTime(timezone=True), nullable=True)
    minta_struk = Column(Boolean, nullable=False, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    # Relasi yang sudah ada
    orders = relationship("CustomerOrder", back_populates="customer")

    # ← TAMBAH: relasi ke Review (ULASAN → USER/Customer N:1)
    reviews = relationship("Review", back_populates="customer")

    # ← TAMBAH: relasi ke NotificationUser (NOTIFIKASI_USER → USER N:1)
    notifications = relationship("NotificationUser", back_populates="user")