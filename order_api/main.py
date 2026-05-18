from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine
import models
from routers import menu, orders
from seed import seed_data

models.Base.metadata.create_all(bind=engine)

seed_data()

app = FastAPI(
    title="Food Order API",
    description="""
## API untuk Manajemen Order Makanan & Minuman

### Fitur:
- **Menu** - CRUD menu makanan dan minuman
- **Orders** - Buat, lihat, dan update status order
- **Summary** - Statistik order dan pendapatan

### Cara Pakai:
1. Lihat menu tersedia di `/menu`
2. Buat order baru di `POST /orders`
3. Update status di `PATCH /orders/{id}/status`
    """,
    version="1.0.0",
    contact={"name": "Food Order API", "email": "dev@foodorder.id"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(menu.router)
app.include_router(orders.router)

@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Selamat datang di Food Order API!",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "menu": "/menu",
            "menu_makanan": "/menu/makanan",
            "menu_minuman": "/menu/minuman",
            "orders": "/orders",
            "orders_aktif": "/orders/aktif",
            "order_summary": "/orders/summary",
        }
    }