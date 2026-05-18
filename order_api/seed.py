from database import SessionLocal, engine
import models

def seed_data():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(models.MenuItem).count() > 0:
        print("✅ Data sudah ada, skip seeding.")
        db.close()
        return

    print("Menanam data dummy...")

    # ─── MENU MAKANAN ─────────────────────────────────────
    makanan = [
        models.MenuItem(nama="Nasi Goreng Spesial", kategori="makanan", harga=25000,
                        deskripsi="Nasi goreng dengan telur, ayam, dan sayuran segar"),
        models.MenuItem(nama="Mie Ayam Bakso", kategori="makanan", harga=20000,
                        deskripsi="Mie kenyal dengan ayam cincang dan bakso sapi"),
        models.MenuItem(nama="Ayam Geprek Sambal Bawang", kategori="makanan", harga=28000,
                        deskripsi="Ayam crispy digeprek dengan sambal bawang pedas"),
        models.MenuItem(nama="Gado-Gado Jakarta", kategori="makanan", harga=18000,
                        deskripsi="Sayuran segar dengan bumbu kacang spesial"),
        models.MenuItem(nama="Soto Ayam Lamongan", kategori="makanan", harga=22000,
                        deskripsi="Soto ayam kuah bening khas Lamongan"),
        models.MenuItem(nama="Rendang Daging Sapi", kategori="makanan", harga=35000,
                        deskripsi="Rendang daging sapi empuk dengan rempah pilihan"),
        models.MenuItem(nama="Bakso Kuah Spesial", kategori="makanan", harga=20000,
                        deskripsi="Bakso sapi dengan kuah kaldu gurih dan mie"),
        models.MenuItem(nama="Nasi Uduk Komplit", kategori="makanan", harga=23000,
                        deskripsi="Nasi uduk dengan ayam, tempe, dan lalapan"),
        models.MenuItem(nama="Pecel Lele + Nasi", kategori="makanan", harga=19000,
                        deskripsi="Lele goreng crispy dengan sambal dan lalapan"),
        models.MenuItem(nama="Sandwich Tuna Keju", kategori="makanan", harga=27000,
                        deskripsi="Sandwich roti tawar dengan isian tuna dan keju leleh", tersedia=False),
    ]

    # ─── MENU MINUMAN ─────────────────────────────────────
    minuman = [
        models.MenuItem(nama="Es Teh Manis", kategori="minuman", harga=5000,
                        deskripsi="Teh manis segar dengan es batu"),
        models.MenuItem(nama="Es Jeruk Peras", kategori="minuman", harga=8000,
                        deskripsi="Jeruk peras segar tanpa pengawet"),
        models.MenuItem(nama="Jus Alpukat", kategori="minuman", harga=15000,
                        deskripsi="Jus alpukat kental dengan susu dan madu"),
        models.MenuItem(nama="Kopi Susu Gula Aren", kategori="minuman", harga=18000,
                        deskripsi="Kopi robusta dengan susu segar dan gula aren"),
        models.MenuItem(nama="Es Campur Spesial", kategori="minuman", harga=14000,
                        deskripsi="Campuran cincau, kolang-kaling, dan sirup merah"),
        models.MenuItem(nama="Teh Tarik", kategori="minuman", harga=10000,
                        deskripsi="Teh susu khas Malaysia yang creamy"),
        models.MenuItem(nama="Jus Semangka Segar", kategori="minuman", harga=12000,
                        deskripsi="Semangka segar diblender dengan es"),
        models.MenuItem(nama="Air Mineral", kategori="minuman", harga=4000,
                        deskripsi="Air mineral kemasan 600ml"),
        models.MenuItem(nama="Es Lemon Tea", kategori="minuman", harga=9000,
                        deskripsi="Teh dengan perasan lemon dan es batu"),
        models.MenuItem(nama="Matcha Latte", kategori="minuman", harga=22000,
                        deskripsi="Matcha premium dengan susu oat"),
    ]

    db.add_all(makanan + minuman)
    db.commit()
    print(f"✅ {len(makanan)} menu makanan ditambahkan")
    print(f"✅ {len(minuman)} menu minuman ditambahkan")

    # ─── ORDERS DUMMY ─────────────────────────────────────
    menu = {m.nama: m for m in db.query(models.MenuItem).all()}

    orders_data = [
        {
            "order": models.Order(nama_pelanggan="Budi Santoso", nomor_meja=1,
                                  status="selesai", catatan="Tidak pakai pedas"),
            "items": [
                ("Nasi Goreng Spesial", 2),
                ("Es Teh Manis", 2),
            ]
        },
        {
            "order": models.Order(nama_pelanggan="Siti Rahayu", nomor_meja=3,
                                  status="diproses", catatan="Extra sambal"),
            "items": [
                ("Ayam Geprek Sambal Bawang", 1),
                ("Mie Ayam Bakso", 1),
                ("Jus Alpukat", 1),
                ("Es Jeruk Peras", 1),
            ]
        },
        {
            "order": models.Order(nama_pelanggan="Ahmad Fauzi", nomor_meja=5,
                                  status="pending"),
            "items": [
                ("Rendang Daging Sapi", 2),
                ("Nasi Uduk Komplit", 1),
                ("Kopi Susu Gula Aren", 2),
            ]
        },
        {
            "order": models.Order(nama_pelanggan="Dewi Lestari", nomor_meja=2,
                                  status="selesai", catatan="Minta sendok lebih"),
            "items": [
                ("Soto Ayam Lamongan", 3),
                ("Teh Tarik", 2),
                ("Air Mineral", 1),
            ]
        },
        {
            "order": models.Order(nama_pelanggan="Rizky Pratama", nomor_meja=7,
                                  status="diproses"),
            "items": [
                ("Gado-Gado Jakarta", 1),
                ("Pecel Lele + Nasi", 2),
                ("Matcha Latte", 1),
                ("Es Lemon Tea", 1),
            ]
        },
        {
            "order": models.Order(nama_pelanggan="Fitriani", nomor_meja=4,
                                  status="pending", catatan="Alergi kacang"),
            "items": [
                ("Bakso Kuah Spesial", 2),
                ("Jus Semangka Segar", 2),
            ]
        },
        {
            "order": models.Order(nama_pelanggan="Eko Wahyudi", nomor_meja=6,
                                  status="dibatalkan", catatan="Batalkan semua"),
            "items": [
                ("Nasi Goreng Spesial", 1),
                ("Kopi Susu Gula Aren", 1),
            ]
        },
    ]

    for data in orders_data:
        order = data["order"]
        db.add(order)
        db.flush()

        total = 0.0
        for nama_menu, jumlah in data["items"]:
            if nama_menu in menu:
                item = menu[nama_menu]
                subtotal = item.harga * jumlah
                total += subtotal
                order_item = models.OrderItem(
                    order_id=order.id,
                    menu_item_id=item.id,
                    jumlah=jumlah,
                    harga_satuan=item.harga,
                    subtotal=subtotal
                )
                db.add(order_item)

        order.total_harga = total

    db.commit()
    print(f"✅ {len(orders_data)} order dummy ditambahkan")
    print("Seeding selesai!")
    db.close()

if __name__ == "__main__":
    seed_data()