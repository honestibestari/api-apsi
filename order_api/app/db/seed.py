"""Seeder data awal (merchant & product dummy).

Dipanggil sekali saat startup. Jika data sudah ada, proses dilewati.
Bisa juga dijalankan manual: `python -m app.db.seed`
"""
from app.core.database import Base, SessionLocal, engine
from app.dining_table.dining_table_model import DiningTable
from app.merchant.merchant_model import Merchant
from app.product.product_model import Product


def seed_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    merchants_exist = db.query(Merchant).count() > 0
    dining_tables_exist = db.query(DiningTable).count() > 0

    if merchants_exist and dining_tables_exist:
        print("[OK] Data sudah ada, skip seeding.")
        db.close()
        return

    if not dining_tables_exist:
        print("Menanam dining table dummy...")
        dining_tables = [
            DiningTable(label="T-01", code="meja01demo"),
            DiningTable(label="T-02", code="meja02demo"),
            DiningTable(label="T-03", code="meja03demo"),
            DiningTable(label="T-04", code="meja04demo"),
            DiningTable(label="T-05", code="meja05demo"),
        ]
        db.add_all(dining_tables)
        db.commit()
        print(f"[OK] {len(dining_tables)} dining table ditambahkan")

    if merchants_exist:
        db.close()
        return

    print("Menanam data dummy...")

    # Setiap merchant beserta daftar product-nya.
    data = [
        {
            "merchant": Merchant(
                nama="Toko Berkah Jaya",
                deskripsi="Sembako dan kebutuhan harian",
                alamat="Jl. Merdeka No. 12, Surabaya",
            ),
            "products": [
                Product(nama="Beras Premium 5kg", harga=68000, stok=40,
                        deskripsi="Beras pulen kualitas premium"),
                Product(nama="Minyak Goreng 2L", harga=34000, stok=60,
                        deskripsi="Minyak goreng kemasan 2 liter"),
                Product(nama="Gula Pasir 1kg", harga=15000, stok=80,
                        deskripsi="Gula pasir putih bersih"),
            ],
        },
        {
            "merchant": Merchant(
                nama="Kedai Kopi Senja",
                deskripsi="Kopi dan minuman kekinian",
                alamat="Jl. Diponegoro No. 8, Malang",
            ),
            "products": [
                Product(nama="Kopi Susu Gula Aren", harga=18000, stok=100,
                        deskripsi="Kopi robusta dengan gula aren"),
                Product(nama="Americano", harga=15000, stok=100,
                        deskripsi="Espresso dengan air"),
                Product(nama="Matcha Latte", harga=22000, stok=50,
                        deskripsi="Matcha premium dengan susu"),
            ],
        },
        {
            "merchant": Merchant(
                nama="Gadget Corner",
                deskripsi="Aksesoris elektronik dan gadget",
                alamat="Jl. Pemuda No. 45, Jakarta",
            ),
            "products": [
                Product(nama="Kabel USB-C 1m", harga=25000, stok=120,
                        deskripsi="Kabel data & charging USB-C"),
                Product(nama="Powerbank 10000mAh", harga=150000, stok=30,
                        deskripsi="Powerbank fast charging"),
                Product(nama="Earbuds Bluetooth", harga=120000, stok=25,
                        deskripsi="TWS earbuds dengan noise reduction"),
                Product(nama="Mouse Wireless", harga=85000, stok=40,
                        deskripsi="Mouse nirkabel 2.4GHz"),
            ],
        },
        {
            "merchant": Merchant(
                nama="Fashion Outlet",
                deskripsi="Pakaian pria & wanita",
                alamat="Jl. Asia Afrika No. 21, Bandung",
            ),
            "products": [
                Product(nama="Kaos Polos Cotton", harga=55000, stok=70,
                        deskripsi="Kaos katun combed 30s"),
                Product(nama="Celana Chino", harga=145000, stok=35,
                        deskripsi="Celana chino bahan stretch"),
                Product(nama="Jaket Hoodie", harga=180000, stok=20,
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
