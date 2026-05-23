"""Seeder data awal (merchant & product dummy).

Dipanggil sekali saat startup. Jika data sudah ada, proses dilewati.
Bisa juga dijalankan manual: `python -m app.db.seed`
"""
from app import models
from app.core.database import SessionLocal, engine


def seed_data():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(models.Merchant).count() > 0:
        print("[OK] Data sudah ada, skip seeding.")
        db.close()
        return

    print("Menanam data dummy...")

    # Setiap merchant beserta daftar product-nya.
    data = [
        {
            "merchant": models.Merchant(
                nama="Toko Berkah Jaya",
                deskripsi="Sembako dan kebutuhan harian",
                alamat="Jl. Merdeka No. 12, Surabaya",
            ),
            "products": [
                models.Product(nama="Beras Premium 5kg", harga=68000, stok=40,
                               deskripsi="Beras pulen kualitas premium"),
                models.Product(nama="Minyak Goreng 2L", harga=34000, stok=60,
                               deskripsi="Minyak goreng kemasan 2 liter"),
                models.Product(nama="Gula Pasir 1kg", harga=15000, stok=80,
                               deskripsi="Gula pasir putih bersih"),
            ],
        },
        {
            "merchant": models.Merchant(
                nama="Kedai Kopi Senja",
                deskripsi="Kopi dan minuman kekinian",
                alamat="Jl. Diponegoro No. 8, Malang",
            ),
            "products": [
                models.Product(nama="Kopi Susu Gula Aren", harga=18000, stok=100,
                               deskripsi="Kopi robusta dengan gula aren"),
                models.Product(nama="Americano", harga=15000, stok=100,
                               deskripsi="Espresso dengan air"),
                models.Product(nama="Matcha Latte", harga=22000, stok=50,
                               deskripsi="Matcha premium dengan susu"),
            ],
        },
        {
            "merchant": models.Merchant(
                nama="Gadget Corner",
                deskripsi="Aksesoris elektronik dan gadget",
                alamat="Jl. Pemuda No. 45, Jakarta",
            ),
            "products": [
                models.Product(nama="Kabel USB-C 1m", harga=25000, stok=120,
                               deskripsi="Kabel data & charging USB-C"),
                models.Product(nama="Powerbank 10000mAh", harga=150000, stok=30,
                               deskripsi="Powerbank fast charging"),
                models.Product(nama="Earbuds Bluetooth", harga=120000, stok=25,
                               deskripsi="TWS earbuds dengan noise reduction"),
                models.Product(nama="Mouse Wireless", harga=85000, stok=40,
                               deskripsi="Mouse nirkabel 2.4GHz"),
            ],
        },
        {
            "merchant": models.Merchant(
                nama="Fashion Outlet",
                deskripsi="Pakaian pria & wanita",
                alamat="Jl. Asia Afrika No. 21, Bandung",
            ),
            "products": [
                models.Product(nama="Kaos Polos Cotton", harga=55000, stok=70,
                               deskripsi="Kaos katun combed 30s"),
                models.Product(nama="Celana Chino", harga=145000, stok=35,
                               deskripsi="Celana chino bahan stretch"),
                models.Product(nama="Jaket Hoodie", harga=180000, stok=20,
                               deskripsi="Hoodie fleece tebal dan hangat"),
            ],
        },
    ]

    total_product = 0
    for entry in data:
        merchant = entry["merchant"]
        merchant.products = entry["products"]  # relasi mengisi merchant_id otomatis
        db.add(merchant)
        total_product += len(entry["products"])

    db.commit()
    print(f"[OK] {len(data)} merchant ditambahkan")
    print(f"[OK] {total_product} product ditambahkan")
    print("Seeding selesai!")
    db.close()


if __name__ == "__main__":
    seed_data()
