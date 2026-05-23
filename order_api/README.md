# Product & Merchant API

API sederhana untuk menampilkan **product** dan **merchant**, dibangun dengan
**FastAPI** + **SQLAlchemy** (SQLite). Disusun dengan arsitektur berlapis
(layered) supaya rapi dan mudah dikembangkan.

Relasi data: **satu Merchant memiliki banyak Product**.

## Endpoint

| Method | Path                | Deskripsi                                  |
| ------ | ------------------- | ------------------------------------------ |
| GET    | `/products`         | List semua product                         |
| GET    | `/products/{id}`    | Detail product (beserta merchant pemilik)  |
| GET    | `/merchants`        | List semua merchant                        |
| GET    | `/merchants/{id}`   | Detail merchant (beserta daftar product)   |

## Struktur Proyek

```
order_api/
├── app/
│   ├── main.py              # Entrypoint FastAPI: bikin app, daftar router
│   ├── core/
│   │   ├── config.py        # Konfigurasi via .env (pydantic-settings)
│   │   └── database.py      # Engine, SessionLocal, Base, get_db
│   ├── models/              # Model SQLAlchemy (tabel database)
│   │   ├── merchant.py      # Merchant
│   │   └── product.py       # Product
│   ├── schemas/             # Schema Pydantic (validasi request/response)
│   │   ├── merchant.py
│   │   └── product.py
│   ├── services/            # Logika bisnis (terpisah dari router)
│   │   ├── merchant_service.py
│   │   └── product_service.py
│   ├── routers/             # Endpoint HTTP (tipis, panggil service)
│   │   ├── merchants.py
│   │   └── products.py
│   └── db/
│       └── seed.py          # Seeder data awal (merchant & product dummy)
├── run.py                   # Shortcut menjalankan server
├── requirements.txt
├── .env.example             # Contoh konfigurasi (salin ke .env)
└── .gitignore
```

### Alur lapisan

```
Request → routers/ → services/ → models/ (database)
                 ↘ schemas/ (validasi & serialisasi) ↗
```

Router hanya menerima request dan memanggil **service**. Semua query database
ada di service, sehingga endpoint tetap tipis dan mudah diuji.

## Cara Menjalankan

> Semua perintah dijalankan dari dalam folder `order_api/`.

1. **Buat virtual environment & install dependency**

   ```powershell
   py -3.1 -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

   Jika `Activate.ps1` diblokir, jalankan dulu:
   `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

2. **Siapkan konfigurasi**

   ```powershell
   copy .env.example .env
   ```

   File `.env` sudah cukup untuk SQLite. Ubah `DATABASE_URL` bila ingin pakai
   database lain.

3. **Jalankan server**

   ```powershell
   python run.py
   ```

   atau:

   ```powershell
   uvicorn app.main:app --reload
   ```

   Database `store.db` otomatis dibuat dan diisi data dummy saat pertama kali
   start.

4. **Buka dokumentasi interaktif**

   - Swagger UI: <http://localhost:8000/docs>
   - ReDoc: <http://localhost:8000/redoc>

## Konfigurasi (.env)

| Variabel        | Default                       | Keterangan                   |
| --------------- | ----------------------------- | ---------------------------- |
| `APP_NAME`      | `Product & Merchant API`      | Judul aplikasi               |
| `APP_VERSION`   | `1.0.0`                       | Versi API                    |
| `DEBUG`         | `true`                        | Auto-reload server           |
| `DATABASE_URL`  | `sqlite:///./store.db`        | Koneksi database             |
| `CORS_ORIGINS`  | `*`                           | Daftar origin (dipisah koma) |
