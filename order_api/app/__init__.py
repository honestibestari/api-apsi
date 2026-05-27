"""Food Order API — package aplikasi utama.

Saat package di-load, kita:
  1. Import seluruh SQLAlchemy model agar terdaftar di `Base.metadata`
     (dibutuhkan oleh `Base.metadata.create_all`).
  2. Resolve forward reference Pydantic antara product <-> merchant
     yang saling rujuk.
"""
# (1) Registrasi model — sengaja di-import meski tidak dipakai langsung.
from app.merchant.merchant_model import Merchant  # noqa: F401
from app.product.product_model import Product  # noqa: F401
from app.dining_table.dining_table_model import DiningTable  # noqa: F401
from app.customer.customer_model import Customer  # noqa: F401
from app.customer_order.customer_order_model import CustomerOrder  # noqa: F401
from app.merchant_order.merchant_order_model import (  # noqa: F401
    MerchantOrder, OrderItem, Notification,
)
from app.withdrawal.withdrawal_model import Withdrawal  # noqa: F401
from app.review.review_model import Review  # noqa: F401

# (2) Resolve forward reference: ProductDetail.merchant -> MerchantSummary.
from app.merchant.merchant_schema import MerchantSummary
from app.product import product_schema as _product_schema
from app.product.product_schema import ProductDetail

_product_schema.MerchantSummary = MerchantSummary
ProductDetail.model_rebuild()
