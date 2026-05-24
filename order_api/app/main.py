from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.db.seed import seed_data
from app.dining_table.dining_table_router import router as dining_table_router
from app.merchant.merchant_router import router as merchant_router
from app.product.product_router import router as product_router

# Buat tabel (jika belum ada) lalu isi data awal.
Base.metadata.create_all(bind=engine)
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


@app.get("/", tags=["Root"])
def root():
    return {
        "message": f"Selamat datang di {settings.app_name}!",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "products": "/products",
            "product_detail": "/products/{id}",
            "merchants": "/merchants",
            "merchant_detail": "/merchants/{id}",
            "dining_tables": "/dining-tables",
            "dining_table_scan": "/dining-tables/scan?code={code}",
        },
    }
