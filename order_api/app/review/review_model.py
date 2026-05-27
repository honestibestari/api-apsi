from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Review(Base):
    """Ulasan & rating merchant (langkah 'Rating (Opsional)' di alur customer).

    Rating merchant diturunkan dari rata-rata seluruh review-nya.
    """
    __tablename__ = "reviews"

    id                = Column(Integer, primary_key=True, index=True)
    merchant_id       = Column(Integer, ForeignKey("merchants.id"), nullable=False, index=True)
    customer_order_id = Column(Integer, ForeignKey("customer_orders.id"), nullable=True)
    rating            = Column(Integer, nullable=False)  # 1..5
    komentar          = Column(Text, nullable=True)
    pelanggan         = Column(String(100), nullable=True)  # nama penulis bila tak terkait order
    created_at        = Column(DateTime(timezone=True), server_default=func.now())

    merchant       = relationship("Merchant", back_populates="reviews")
    customer_order = relationship("CustomerOrder")

    @property
    def pelanggan_nama(self):
        if self.customer_order and self.customer_order.customer:
            return self.customer_order.customer.nama
        return self.pelanggan
