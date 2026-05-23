from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models
from app.core.config import settings
from app.core.database import engine
from app.db.seed import seed_data
from app.routers import merchants, products

# Buat tabel (jika belum ada) lalu isi data awal.
models.Base.metadata.create_all(bind=engine)
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

app.include_router(products.router)
app.include_router(merchants.router)


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
        },
    }
