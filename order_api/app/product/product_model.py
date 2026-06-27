from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression, func

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id          = Column(Integer, primary_key=True, index=True)
    nama        = Column(String(100), nullable=False, index=True)
    deskripsi   = Column(String, nullable=True)
    foto        = Column(String, nullable=True)
    harga       = Column(Float, nullable=False)
    stok        = Column(Integer, nullable=False, default=0)
    # Ketersediaan jual yang diatur merchant (toggle "Tersedia/Habis"), terpisah
    # dari stok. Default tersedia. server_default agar baris lama ikut terisi saat
    # kolom ditambahkan via sync_columns().
    is_available = Column(Boolean, nullable=False, server_default=expression.true(),
                          default=True)
    # Blokir/ban produk oleh ADMIN (mis. melanggar aturan). Berbeda dari
    # is_available (diatur merchant): bila True, produk disembunyikan dari
    # pelanggan & tidak bisa dipesan, dan MERCHANT tidak bisa membatalkannya —
    # hanya admin yang bisa membuka blokir. Default tidak diblokir.
    is_banned   = Column(Boolean, nullable=False, server_default=expression.false(),
                         default=False)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    # Relasi
    merchant = relationship("Merchant", back_populates="products")
    category = relationship("Category", back_populates="products")
    additionals = relationship(
        "ProductAddon",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductAddon.id",
    )


class ProductAddon(Base):
    """Item tambahan (add-on) opsional untuk sebuah produk.

    Mis. "Extra Keju" +Rp5.000, "Telur" +Rp3.000. Dikelola merchant di menu,
    dipilih pelanggan saat memesan.
    """
    __tablename__ = "product_addons"

    id         = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    nama       = Column(String(100), nullable=False)
    harga      = Column(Float, nullable=False, default=0.0)
    is_active  = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="additionals")