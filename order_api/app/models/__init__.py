"""Model SQLAlchemy.

Re-export semua model agar `from app import models` lalu `models.Product`
tetap bekerja, dan agar Base.metadata mengenali seluruh tabel.
"""
from app.core.database import Base
from app.models.merchant import Merchant
from app.models.product import Product

__all__ = ["Base", "Merchant", "Product"]
