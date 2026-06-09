from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from app.core.config import settings
from app.core.database import Base, engine, sync_columns, reset_schema
from app.db.seed import seed_data
from app.dining_table.dining_table_router import router as dining_table_router
from app.merchant.merchant_router import router as merchant_router
from app.product.product_router import router as product_router
from app.customer_order.customer_order_router import router as customer_order_router
from app.merchant_order.merchant_order_router import router as merchant_order_router
from app.withdrawal.withdrawal_router import router as withdrawal_router
from app.review.review_router import router as review_router
from app.customer.customer_router import router as customer_router
from app.auth.auth_router import router as auth_router
from app.user.user_model import User
from app.admin.admin_router import router as admin_router
from app.category.category_router           import router as category_router
from app.payment.payment_router             import router as payment_router
from app.payment_method.payment_method_router import router as payment_method_router
from app.refund.refund_router               import router as refund_router

# Model diregistrasi di app/__init__.py saat package load.
# 0) Jika RESET_DB=true: drop semua tabel + enum (sekali, untuk bereskan drift).
# 1) Buat tabel yang belum ada.
# 2) Tambahkan kolom baru ke tabel lama (create_all tidak meng-ALTER).
# 3) Isi data awal.
if settings.reset_db:
    reset_schema()
Base.metadata.create_all(bind=engine)
sync_columns()
seed_data()

app = FastAPI(
    title=settings.app_name,
    description="""
## API Product & Merchant

### Endpoint:
- **GET /products** — list product
- **GET /products/{id}** — detail product
- **GET /merchants** — list merchant
- **GET /merchants/{id}** — detail merchant (beserta daftar product)
    """,
    version=settings.app_version,
    contact={"name": settings.app_name, "email": "dev@example.id"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(product_router)
app.include_router(merchant_router)
app.include_router(dining_table_router)
app.include_router(customer_order_router)
app.include_router(merchant_order_router)
app.include_router(withdrawal_router)
app.include_router(review_router)
app.include_router(customer_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(category_router)
app.include_router(payment_router)
app.include_router(payment_method_router)
app.include_router(refund_router)


@app.get("/", tags=["Root"])
def root():
    """Landing endpoint: daftar semua endpoint API (di-generate otomatis dari router)."""
    grouped: dict[str, list[dict]] = {}
    for route in app.routes:
        # Lewati route non-API (mis. /openapi.json, /docs) dan root itu sendiri.
        if not isinstance(route, APIRoute) or route.path == "/":
            continue
        tag = (route.tags or ["Lainnya"])[0]
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            grouped.setdefault(tag, []).append(
                {
                    "method": method,
                    "path": route.path,
                    "summary": route.summary or route.name,
                }
            )
    for items in grouped.values():
        items.sort(key=lambda e: (e["path"], e["method"]))

    return {
        "message": f"Selamat datang di {settings.app_name}!",
        "version": settings.app_version,
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
        "total_endpoints": sum(len(v) for v in grouped.values()),
        "endpoints": grouped,
    }
