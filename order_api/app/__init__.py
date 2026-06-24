"""Food Order API — package aplikasi utama.

Saat package di-load, kita:
  1. Import seluruh SQLAlchemy model agar terdaftar di `Base.metadata`
     (dibutuhkan oleh `Base.metadata.create_all`).
  2. Resolve forward reference Pydantic antara product <-> merchant
     yang saling rujuk.
"""
# (1) Registrasi model — sengaja di-import meski tidak dipakai langsung.
from app.user.user_model import User
from app.merchant.merchant_model import Merchant  
from app.product.product_model import Product  
from app.dining_table.dining_table_model import DiningTable  
from app.customer.customer_model import Customer 
from app.customer_order.customer_order_model import CustomerOrder 
from app.merchant_order.merchant_order_model import (MerchantOrder, OrderItem, Notification)
from app.withdrawal.withdrawal_model import Withdrawal, MerchantBankAccount
from app.review.review_model import Review  
from app.admin.admin_model import Admin
from app.category.category_model import Category                             
from app.payment_method.payment_method_model import PaymentMethod             
from app.payment.payment_model import Payment
from app.refund.refund_model import Refund
from app.banner.banner_model import Banner
from app.attachment.attachment_model import Attachment
from app.platform_setting.platform_setting_model import PlatformSetting

# (2) Resolve forward reference: ProductDetail.merchant -> MerchantSummary.
from app.merchant.merchant_schema import MerchantSummary
from app.product import product_schema as _product_schema
from app.product.product_schema import ProductDetail

_product_schema.MerchantSummary = MerchantSummary
ProductDetail.model_rebuild()
