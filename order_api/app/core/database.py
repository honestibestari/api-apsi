"""Koneksi database & session SQLAlchemy.

URL database diambil dari konfigurasi (.env). Secara default memakai SQLite
lokal, tetapi bisa diganti ke Postgres/MySQL hanya dengan mengubah DATABASE_URL.
"""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.schema import CreateColumn

from app.core.config import settings

# check_same_thread hanya relevan untuk SQLite (FastAPI memakai banyak thread).
connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(settings.database_url, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency FastAPI: buka session per-request, lalu pastikan ditutup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_schema():
    """DROP semua tabel + tipe enum, lalu biarkan create_all() membangun ulang.

    Dipakai sekali untuk membereskan drift skema yang tidak bisa diperbaiki
    secara additive (mis. nilai tipe enum yang berbeda). DESTRUKTIF: semua data
    hilang. Hanya jalan jika settings.reset_db == True.
    """
    print("[reset_schema] DROP semua tabel & tipe enum (RESET_DB aktif)...")

    # Di Postgres, drop_all() hanya mengenal tabel yang terdaftar di model.
    # Tabel legacy (mis. tenant_balance/tenant_settings/notification_user) yang
    # tidak ada di model bisa punya FK ke tabel model → DROP TABLE-nya ditolak.
    # Cara paling bersih untuk reset total: buang seluruh schema `public` berikut
    # semua dependensinya (tabel legacy + tipe enum native), lalu buat ulang.
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
        print("[reset_schema] schema public di-drop & dibuat ulang (CASCADE)")
    else:
        Base.metadata.drop_all(bind=engine)


def apply_manual_migrations():
    """Migrasi non-additive yang tidak bisa ditangani sync_columns().

    sync_columns() hanya menambah kolom; ia tidak bisa mengubah nullability.
    Di sini kita jalankan ALTER eksplisit yang aman & idempotent.
    """
    if engine.dialect.name != "postgresql":
        return

    # ── Tambah nilai baru ke tipe ENUM native Postgres ──────────────────────────
    # create_all() TIDAK meng-ALTER tipe enum yang sudah ada. `ALTER TYPE ... ADD
    # VALUE` harus jalan di luar blok transaksi → pakai koneksi AUTOCOMMIT.
    # IF NOT EXISTS membuatnya idempotent (aman dijalankan tiap startup).
    _enum_additions = {
        "notifikasi_tipe": ["pengumuman", "penting"],
    }
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for enum_name, values in _enum_additions.items():
            for val in values:
                try:
                    conn.execute(text(
                        f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{val}'"
                    ))
                except Exception as exc:  # pragma: no cover - jangan gagal start app
                    print(f"[migrate] gagal ADD VALUE {enum_name}={val}: {exc}")

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    # ── categories.id_tenant → DROP (kategori kini global) ──────────────────────
    # DROP COLUMN otomatis membuang FK constraint-nya. IF EXISTS = idempotent.
    if "categories" in tables:
        cols = {c["name"] for c in inspector.get_columns("categories")}
        if "id_tenant" in cols:
            with engine.begin() as conn:
                conn.execute(text('ALTER TABLE categories DROP COLUMN IF EXISTS id_tenant'))
                print("[migrate] dropped categories.id_tenant (kategori global)")

    # ── customer_orders.metode_pembayaran enum → FK payment_methods ─────────────
    # Kolom FK (metode_pembayaran_id) sudah ditambahkan additive oleh sync_columns().
    # Di sini: backfill dari enum lama lalu buang kolom enum + tipenya.
    if "customer_orders" in tables and "payment_methods" in tables:
        cols = {c["name"] for c in inspector.get_columns("customer_orders")}
        if "metode_pembayaran" in cols:  # kolom enum lama masih ada → migrasikan
            with engine.begin() as conn:
                # Pastikan metode legacy ada agar backfill bisa mencocokkan.
                for nama in ("QRIS", "Tunai"):
                    conn.execute(text(
                        "INSERT INTO payment_methods (nama_metode, is_active, fee) "
                        "SELECT :nama, true, '' "
                        "WHERE NOT EXISTS (SELECT 1 FROM payment_methods "
                        "WHERE lower(nama_metode) = lower(:nama))"
                    ), {"nama": nama})
                # Backfill FK dari nilai enum lama (cocokkan via nama, case-insensitive).
                conn.execute(text(
                    "UPDATE customer_orders co SET metode_pembayaran_id = pm.id "
                    "FROM payment_methods pm "
                    "WHERE co.metode_pembayaran_id IS NULL "
                    "AND lower(pm.nama_metode) = lower(co.metode_pembayaran::text)"
                ))
                # Buang kolom enum lama + tipenya.
                conn.execute(text('ALTER TABLE customer_orders DROP COLUMN IF EXISTS metode_pembayaran'))
                conn.execute(text('DROP TYPE IF EXISTS metode_pembayaran'))
                print("[migrate] customer_orders.metode_pembayaran enum → FK payment_methods")

    # ── customers.phone: lepas UNIQUE (phone kini sekadar data, boleh berubah) ──
    if "customers" in tables:
        with engine.begin() as conn:
            conn.execute(text('ALTER TABLE customers DROP CONSTRAINT IF EXISTS customers_phone_key'))

    # ── payments: drop struk_dikirim + backfill public_token ────────────────────
    if "payments" in tables:
        cols = {c["name"] for c in inspector.get_columns("payments")}
        with engine.begin() as conn:
            if "struk_dikirim" in cols:
                conn.execute(text('ALTER TABLE payments DROP COLUMN IF EXISTS struk_dikirim'))
                print("[migrate] dropped payments.struk_dikirim (tak terpakai)")
            # Baris lama (sebelum kolom ada) bertoken NULL → isi token acak.
            if "public_token" in cols:
                conn.execute(text(
                    "UPDATE payments SET public_token = md5(random()::text || id::text) "
                    "WHERE public_token IS NULL"
                ))


def sync_columns():
    """Auto-migrasi ringan tanpa alembic.

    `Base.metadata.create_all()` hanya membuat tabel yang belum ada; ia TIDAK
    menambahkan kolom baru ke tabel yang sudah terlanjur dibuat di deploy
    sebelumnya. Fungsi ini membandingkan kolom pada model dengan kolom yang ada
    di database, lalu menjalankan `ALTER TABLE ... ADD COLUMN` untuk yang kurang.

    Aman dijalankan berulang kali: kolom yang sudah ada dilewati. Cukup untuk
    perubahan additive (menambah kolom). Untuk rename/drop/ubah tipe tetap perlu
    SQL manual.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            # Tabel yang benar-benar baru sudah ditangani create_all().
            if table.name not in existing_tables:
                continue

            existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_cols:
                    continue
                col_ddl = CreateColumn(column).compile(dialect=engine.dialect)
                ddl = f'ALTER TABLE "{table.name}" ADD COLUMN {col_ddl}'
                # Tabel yang sudah ada bisa berisi data. `ADD COLUMN ... NOT NULL`
                # tanpa default akan gagal (NotNullViolation) karena baris lama
                # belum punya nilai. Untuk kolom wajib tanpa server_default,
                # tambahkan dulu sebagai NULLABLE; enforcement NOT NULL (+ backfill)
                # diserahkan ke apply_manual_migrations() bila memang diperlukan.
                if not column.nullable and column.server_default is None:
                    ddl = ddl.replace(" NOT NULL", "")
                conn.execute(text(ddl))
                print(f"[sync_columns] added {table.name}.{column.name}")
