"""Schema Pydantic.

Re-export agar `from app import schemas` lalu `schemas.ProductDetail` bekerja.
Sekaligus me-resolve forward reference antara product <-> merchant.
"""
from app.schemas import product as _product
from app.schemas.merchant import MerchantBase, MerchantDetail, MerchantSummary
from app.schemas.product import ProductBase, ProductDetail, ProductSummary

# ProductDetail.merchant memakai forward reference "MerchantSummary".
# Suntikkan ke namespace modul product lalu rebuild agar ter-resolve.
_product.MerchantSummary = MerchantSummary
ProductDetail.model_rebuild()

__all__ = [
    "ProductBase",
    "ProductSummary",
    "ProductDetail",
    "MerchantBase",
    "MerchantSummary",
    "MerchantDetail",
]
