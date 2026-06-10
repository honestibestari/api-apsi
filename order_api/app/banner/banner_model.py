from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class Banner(Base):
    """Banner promo yang tampil di home customer.

    Mendukung dua gaya tampilan:
      - berbasis gambar  → isi `image_url`
      - berbasis gradien → isi `bg` + `accent_color` (+ `badge`/`subtitle`)
    Frontend menampilkan gambar jika `image_url` ada, jika tidak pakai gradien.
    """

    __tablename__ = "banners"

    id           = Column(Integer, primary_key=True, index=True)
    title        = Column(String(150), nullable=False)
    subtitle     = Column(String(255), nullable=False, server_default="")
    badge        = Column(String(60), nullable=False, server_default="")
    image_url    = Column(String, nullable=False, server_default="")
    bg           = Column(String, nullable=False, server_default="")
    accent_color = Column(String(30), nullable=False, server_default="")
    sort_order   = Column(Integer, nullable=False, server_default="0")
    is_active    = Column(Boolean, nullable=False, server_default="true")
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
