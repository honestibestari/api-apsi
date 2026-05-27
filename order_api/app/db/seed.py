"""Seeder data awal (merchant & product dummy).

Dipanggil sekali saat startup. Jika data sudah ada, proses dilewati.
Bisa juga dijalankan manual: `python -m app.db.seed`
"""
from app.core.database import Base, SessionLocal, engine
from app.dining_table.dining_table_model import DiningTable
from app.merchant.merchant_model import Merchant, MerchantStatus
from app.product.product_model import Product


def seed_orders(db):
    """Tanam beberapa customer order contoh, masing-masing dipecah ke merchant order.
    Mendemonstrasikan tiap status lifecycle + satu order mixed (ada tenant dibatalkan).
    """
    from app.customer.customer_model import Customer
    from app.customer_order.customer_order_model import (
        CustomerOrder, CustomerOrderStatus, MetodePembayaran, TipeOrder,
    )
    from app.merchant_order.merchant_order_model import (
        MerchantOrder, MerchantOrderStatus, Notification, NotifikasiTipe, OrderItem,
    )

    if db.query(CustomerOrder).count() > 0:
        return

    tables = db.query(DiningTable).all()
    if not tables:
        return

    def merchant_by_nama(nama):
        return db.query(Merchant).filter(Merchant.nama == nama).first()

    def build_order(code, cust, table, status, mo_specs):
        """mo_specs: list of (merchant_nama, MerchantOrderStatus, [(product_nama, qty)])."""
        customer = Customer(nama=cust["nama"], email=cust["email"], phone=cust["phone"])
        db.add(customer)
        db.flush()

        co = CustomerOrder(
            order_code=code,
            customer_id=customer.id,
            dining_table_id=table.id if table else None,
            tipe_order=TipeOrder.DINE_IN,
            metode_pembayaran=MetodePembayaran.QRIS,
            status=status,
        )
        db.add(co)
        db.flush()

        total = 0.0
        for merchant_nama, mo_status, lines in mo_specs:
            merchant = merchant_by_nama(merchant_nama)
            mo = MerchantOrder(
                order_code=f"{code}-T{merchant.id}",
                customer_order_id=co.id,
                merchant_id=merchant.id,
                status=mo_status,
            )
            db.add(mo)
            db.flush()
            subtotal = 0.0
            for product_nama, qty in lines:
                product = next((p for p in merchant.products if p.nama == product_nama), None)
                if not product:
                    continue
                line = product.harga * qty
                subtotal += line
                db.add(OrderItem(
                    merchant_order_id=mo.id, product_id=product.id,
                    jumlah=qty, harga_satuan=product.harga, subtotal=line,
                ))
            mo.subtotal = subtotal
            mo.total_harga = subtotal
            if mo_status != MerchantOrderStatus.DIBATALKAN:
                total += subtotal
            db.add(Notification(
                merchant_id=merchant.id, merchant_order_id=mo.id,
                tipe=NotifikasiTipe.ORDER_BARU,
                judul="Pesanan masuk", pesan=f"{mo.order_code} ({mo_status.value})",
            ))
        co.total_harga = total

    MS = MerchantOrderStatus
    print("Menanam customer order dummy...")

    specs = [
        ("ORD-700042", {"nama": "Andi Pratama", "email": "andi@mail.com", "phone": "0811-0001"}, CustomerOrderStatus.DONE, [
            ("Seblak Teh Rina", MS.SELESAI, [("Seblak Komplit", 1), ("Es Teh Manis", 1)]),
            ("Thai Tea Marina", MS.SELESAI, [("Thai Tea Original", 1), ("Thai Tea Green", 1)]),
        ]),
        ("ORD-700041", {"nama": "Budi Santoso", "email": "budi@mail.com", "phone": "0811-0002"}, CustomerOrderStatus.PROCESS, [
            ("Kantin Ea Ea", MS.DIPROSES, [("Nasi Goreng Spesial", 1), ("Ayam Geprek", 1)]),
            ("Gorengan Bu Ami", MS.DIPROSES, [("Bakwan Sayur", 3), ("Tahu Isi", 2)]),
        ]),
        ("ORD-700040", {"nama": "Citra Lestari", "email": "citra@mail.com", "phone": "0811-0003"}, CustomerOrderStatus.OPEN, [
            ("Es Teh Jumbo", MS.TERBUKA, [("Es Lemon Tea Jumbo", 1), ("Es Teh Tarik", 1)]),
        ]),
        ("ORD-700039", {"nama": "Dewi Anggraini", "email": "dewi@mail.com", "phone": "0811-0004"}, CustomerOrderStatus.WAITING_CONFIRMATION, [
            ("Mie Ayam Mantap", MS.SELESAI, [("Mie Ayam Komplit", 1), ("Mie Ayam Bakso", 1)]),
        ]),
        ("ORD-700038", {"nama": "Eka Putra", "email": "eka@mail.com", "phone": "0811-0005"}, CustomerOrderStatus.VERIFYING, [
            ("Siomay Asoy", MS.BARU, [("Siomay Bandung", 1), ("Siomay Telur", 1)]),
        ]),
        ("ORD-700037", {"nama": "Fajar Nugroho", "email": "fajar@mail.com", "phone": "0811-0006"}, CustomerOrderStatus.DONE, [
            ("Seblak Teh Rina", MS.SELESAI, [("Seblak Ayam", 1)]),
            ("Thai Tea Marina", MS.DIBATALKAN, [("Lychee Tea", 2)]),
        ]),
    ]
    for code, cust, status, mo_specs in specs:
        build_order(code, cust, tables[len(code) % len(tables)], status, mo_specs)

    db.commit()
    print(f"[OK] {len(specs)} customer order ditambahkan")

    # ── Ulasan (rating) ──
    from app.review.review_model import Review
    reviews = [
        ("Seblak Teh Rina", 5, "Pedasnya mantap, porsi banyak!", "Andi Pratama"),
        ("Seblak Teh Rina", 4, "Enak, langganan.", "Budi Santoso"),
        ("Seblak Teh Rina", 5, "Juara!", "Citra Lestari"),
        ("Thai Tea Marina", 4, "Segar dan manisnya pas.", "Dewi Anggraini"),
        ("Thai Tea Marina", 5, "Favorit.", "Eka Putra"),
        ("Kantin Ea Ea", 5, "Nasi gorengnya enak.", "Fajar Nugroho"),
        ("Kantin Ea Ea", 4, "Pelayanan cepat.", "Gita"),
        ("Gorengan Bu Ami", 5, "Renyah dan murah.", "Hadi"),
        ("Mie Ayam Mantap", 4, "Lumayan, kuah gurih.", "Indah"),
    ]
    for nama, rating, komentar, penulis in reviews:
        merchant = merchant_by_nama(nama)
        if merchant:
            db.add(Review(merchant_id=merchant.id, rating=rating, komentar=komentar, pelanggan=penulis))

    # ── Penarikan dana (withdrawal) ──
    from datetime import datetime
    from app.withdrawal.withdrawal_model import Withdrawal, WithdrawalStatus
    withdrawals = [
        ("Seblak Teh Rina", 20000, WithdrawalStatus.APPROVED, "BCA", "1234567890", "Rina Wati"),
        ("Seblak Teh Rina", 10000, WithdrawalStatus.PENDING, "BCA", "1234567890", "Rina Wati"),
        ("Thai Tea Marina", 15000, WithdrawalStatus.PENDING, "Mandiri", "9876543210", "Marina Sutopo"),
        ("Mie Ayam Mantap", 10000, WithdrawalStatus.APPROVED, "BNI", "5566778899", "Joko Susilo"),
        ("Gorengan Bu Ami", 8000, WithdrawalStatus.REJECTED, "BRI", "1122334455", "Ami Suryani"),
    ]
    for nama, amount, wstatus, bank, acc, accname in withdrawals:
        merchant = merchant_by_nama(nama)
        if not merchant:
            continue
        w = Withdrawal(
            merchant_id=merchant.id, amount=amount, status=wstatus,
            bank=bank, account_number=acc, account_name=accname,
            note=None if wstatus == WithdrawalStatus.PENDING else (
                "Disbursed successfully" if wstatus == WithdrawalStatus.APPROVED else "Saldo belum cukup"
            ),
        )
        if wstatus != WithdrawalStatus.PENDING:
            w.processed_at = datetime.now()
        db.add(w)

    db.commit()
    print(f"[OK] {len(reviews)} review & {len(withdrawals)} withdrawal ditambahkan")


def seed_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    merchants_exist = db.query(Merchant).count() > 0
    dining_tables_exist = db.query(DiningTable).count() > 0

    if merchants_exist and dining_tables_exist:
        print("[OK] Data merchant sudah ada, skip seeding merchant.")
        seed_orders(db)
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
        seed_orders(db)
        db.close()
        return

    print("Menanam data dummy...")

    # Tenant F&B di area Teras LA, selaras dengan konsol admin frontend.
    data = [
        {
            "merchant": Merchant(
                nama="Seblak Teh Rina", deskripsi="Seblak pedas aneka level",
                alamat="Blok B-001", owner="Rina Wati", email="rinaseblak@gmail.com",
                phone="0812-3456-7890", block="B-001", category="Makanan",
                status=MerchantStatus.ACTIVE,
            ),
            "products": [
                Product(nama="Seblak Komplit", harga=22000, stok=50, deskripsi="Seblak dengan topping lengkap"),
                Product(nama="Seblak Ayam", harga=18000, stok=50, deskripsi="Seblak dengan suwiran ayam"),
                Product(nama="Es Teh Manis", harga=5000, stok=100, deskripsi="Teh manis dingin"),
            ],
        },
        {
            "merchant": Merchant(
                nama="Thai Tea Marina", deskripsi="Minuman thai tea kekinian",
                alamat="Blok E-012", owner="Marina Sutopo", email="marina.thai@gmail.com",
                phone="0813-2222-4567", block="E-012", category="Minuman",
                status=MerchantStatus.ACTIVE,
            ),
            "products": [
                Product(nama="Thai Tea Original", harga=12000, stok=80, deskripsi="Thai tea klasik"),
                Product(nama="Thai Tea Green", harga=16000, stok=60, deskripsi="Thai green tea"),
                Product(nama="Lychee Tea", harga=4000, stok=80, deskripsi="Teh leci segar"),
            ],
        },
        {
            "merchant": Merchant(
                nama="Siomay Asoy", deskripsi="Siomay bandung bumbu kacang",
                alamat="Blok C-005", owner="Asep Solihin", email="asep.siomay@gmail.com",
                phone="0857-1111-2233", block="C-005", category="Camilan",
                status=MerchantStatus.ACTIVE,
            ),
            "products": [
                Product(nama="Siomay Bandung", harga=12000, stok=40, deskripsi="Siomay komplit bumbu kacang"),
                Product(nama="Siomay Telur", harga=6000, stok=40, deskripsi="Siomay telur"),
            ],
        },
        {
            "merchant": Merchant(
                nama="Kantin Ea Ea", deskripsi="Aneka nasi & lauk",
                alamat="Blok A-003", owner="Eko Wahyudi", email="ekokantin@gmail.com",
                phone="0812-9876-5432", block="A-003", category="Makanan",
                status=MerchantStatus.ACTIVE,
            ),
            "products": [
                Product(nama="Nasi Goreng Spesial", harga=20000, stok=40, deskripsi="Nasi goreng dengan telur & ayam"),
                Product(nama="Ayam Geprek", harga=12000, stok=40, deskripsi="Ayam geprek sambal"),
            ],
        },
        {
            "merchant": Merchant(
                nama="Gorengan Bu Ami", deskripsi="Gorengan hangat tiap hari",
                alamat="Blok D-007", owner="Ami Suryani", email="amigorengan@gmail.com",
                phone="0821-4567-8901", block="D-007", category="Camilan",
                status=MerchantStatus.ACTIVE,
            ),
            "products": [
                Product(nama="Bakwan Sayur", harga=2000, stok=200, deskripsi="Bakwan sayur renyah"),
                Product(nama="Tahu Isi", harga=2000, stok=200, deskripsi="Tahu isi sayur"),
                Product(nama="Pisang Goreng", harga=5000, stok=100, deskripsi="Pisang goreng crispy"),
            ],
        },
        {
            "merchant": Merchant(
                nama="Warung Pak Udin", deskripsi="Masakan rumahan",
                alamat="Blok E-002", owner="Udin Hidayat", email="udinwarung@gmail.com",
                phone="0856-7890-1234", block="E-002", category="Makanan",
                status=MerchantStatus.SUSPENDED,
            ),
            "products": [
                Product(nama="Nasi Goreng Pak Udin", harga=18000, stok=30, deskripsi="Nasi goreng spesial racikan Pak Udin"),
                Product(nama="Kerupuk", harga=3000, stok=100, deskripsi="Kerupuk renyah"),
            ],
        },
        {
            "merchant": Merchant(
                nama="Mie Ayam Mantap", deskripsi="Mie ayam & bakso",
                alamat="Blok C-010", owner="Joko Susilo", email="jokomie@gmail.com",
                phone="0813-5678-9012", block="C-010", category="Makanan",
                status=MerchantStatus.ACTIVE,
            ),
            "products": [
                Product(nama="Mie Ayam Komplit", harga=15000, stok=50, deskripsi="Mie ayam dengan topping lengkap"),
                Product(nama="Mie Ayam Bakso", harga=7000, stok=50, deskripsi="Mie ayam tambah bakso"),
            ],
        },
        {
            "merchant": Merchant(
                nama="Es Teh Jumbo", deskripsi="Es teh ukuran jumbo",
                alamat="Blok A-008", owner="Sari Indriani", email="sariesteh@gmail.com",
                phone="0857-2345-6789", block="A-008", category="Minuman",
                status=MerchantStatus.ACTIVE,
            ),
            "products": [
                Product(nama="Es Lemon Tea Jumbo", harga=8000, stok=100, deskripsi="Lemon tea ukuran jumbo"),
                Product(nama="Es Teh Tarik", harga=7000, stok=100, deskripsi="Teh tarik dingin"),
            ],
        },
        {
            "merchant": Merchant(
                nama="Bakso Pak Kumis", deskripsi="Bakso urat & telur",
                alamat="Blok B-004", owner="Mulyono Suryadi", email="kumisbakso@gmail.com",
                phone="0812-3344-5566", block="B-004", category="Makanan",
                status=MerchantStatus.PENDING,
            ),
            "products": [
                Product(nama="Bakso Urat", harga=15000, stok=40, deskripsi="Bakso urat sapi"),
                Product(nama="Bakso Telur", harga=17000, stok=40, deskripsi="Bakso isi telur"),
            ],
        },
        {
            "merchant": Merchant(
                nama="Roti Bakar Senja", deskripsi="Roti bakar aneka rasa",
                alamat="Blok D-011", owner="Senja Pramudya", email="senjaroti@gmail.com",
                phone="0821-7788-9900", block="D-011", category="Camilan",
                status=MerchantStatus.PENDING,
            ),
            "products": [
                Product(nama="Roti Bakar Coklat", harga=15000, stok=40, deskripsi="Roti bakar coklat keju"),
                Product(nama="Roti Bakar Keju", harga=17000, stok=40, deskripsi="Roti bakar keju spesial"),
            ],
        },
        {
            "merchant": Merchant(
                nama="Kopi Sore", deskripsi="Kopi dan minuman kekinian",
                alamat="Blok E-014", owner="Andika Wijaya", email="andikakopi@gmail.com",
                phone="0856-1122-3344", block="E-014", category="Minuman",
                status=MerchantStatus.PENDING,
            ),
            "products": [
                Product(nama="Kopi Susu Gula Aren", harga=18000, stok=80, deskripsi="Kopi susu gula aren"),
                Product(nama="Americano", harga=15000, stok=80, deskripsi="Americano dingin"),
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

    seed_orders(db)
    print("Seeding selesai!")
    db.close()


if __name__ == "__main__":
    seed_data()
