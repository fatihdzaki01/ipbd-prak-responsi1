# 📰 Wired Articles Scraper & ETL Pipeline

Pipeline lengkap untuk scraping artikel dari **Wired.com**, menyajikannya lewat REST API, dan memuatnya ke database PostgreSQL menggunakan orkestrasi Prefect.

---

## 📋 Daftar Isi

- [Penjelasan Program](#-penjelasan-program)
- [Alur Kerja](#-alur-kerja)
- [Cara Menjalankan Program](#-cara-menjalankan-program)
- [Manfaat dan Insight](#-manfaat-dan-insight)

---

## 🧩 Penjelasan Program

Proyek ini terdiri dari **4 file utama** dengan peran yang berbeda-beda:

### `scrapper.py` — Web Scraper Utama

| Library | Fungsi |
|---|---|
| `selenium` | Otomasi browser Chrome untuk membuka halaman web dan berinteraksi dengan DOM |
| `webdriver_manager` | Mengunduh dan mengelola ChromeDriver secara otomatis tanpa perlu instalasi manual |
| `selenium.webdriver.support.ui.WebDriverWait` | Menunggu elemen HTML muncul sebelum di-scrape (menghindari error timing) |
| `csv` | Menyimpan hasil scraping ke format CSV |
| `json` | Menyimpan hasil scraping ke format JSON terstruktur |
| `datetime` | Mencatat timestamp waktu scraping setiap artikel |
| `time` | Memberikan jeda (`sleep`) agar halaman selesai dimuat sebelum di-scrape |

**Yang dilakukan:**
- Membuka 5 kategori Wired.com (`security`, `science`, `business`, `culture`, `gear`) dalam mode headless (tanpa tampilan browser)
- Scroll halaman beberapa kali untuk memuat lebih banyak artikel
- Mengumpulkan link artikel unik yang mengandung `/story/`
- Mengunjungi setiap artikel dan mengambil: **title**, **description**, **author**, **URL**, **timestamp**, dan **source**
- Menggunakan strategi **multi-fallback** untuk description (meta tag → og:description → h2 → paragraf pertama) dan author (link `/author/` → rel="author" → byline "By ...")
- Menyimpan hasil ke `wired_articles.json` dan `wired_articles.csv`

**Output:**
```
wired_articles.json dan  wired_articles.csv
```

### `api.py` — REST API dengan FastAPI

> Menyajikan data hasil scraping sebagai REST API agar bisa dikonsumsi oleh pipeline ETL.

| Library | Fungsi |
|---|---|
| `fastapi` | Framework web untuk membangun REST API dengan performa tinggi |
| `uvicorn` | ASGI server untuk menjalankan aplikasi FastAPI |
| `pydantic` | Validasi dan serialisasi schema data (model `Article` & `ArticlesResponse`) |
| `json` | Membaca file `wired_articles.json` |
| `os` | Mengambil path file JSON secara dinamis |
| `datetime` | Timestamp pada health check endpoint |

**Endpoints yang tersedia:**

| Method | Endpoint | Fungsi |
|---|---|---|
| `GET` | `/` | Health check — mengecek apakah API berjalan |
| `GET` | `/articles` | Mengembalikan seluruh artikel hasil scraping dalam format JSON |
| `GET` | `/articles/count` | Mengembalikan jumlah artikel yang tersedia |

**Output contoh `/articles`:**
```json
{
  "session_id": "wired_session_20250421_091500",
  "timestamp": "2025-04-21T09:15:00",
  "articles_count": 75,
  "articles": [
    {
      "title": "...",
      "url": "https://www.wired.com/story/...",
      "description": "...",
      "author": "...",
      "scraped_at": "2025-04-21T09:10:00",
      "source": "Wired.com"
    }
  ]
}
```

---

### `flow.py` — ETL Pipeline dengan Prefect

> Orkestrasi pipeline data: ambil dari API → bersihkan → masukkan ke PostgreSQL.

| Library | Fungsi |
|---|---|
| `prefect` | Framework orkestrasi workflow; mendefinisikan `@task` dan `@flow` |
| `requests` | HTTP client untuk hit endpoint `GET /articles` ke FastAPI |
| `psycopg2` | Driver PostgreSQL untuk koneksi dan eksekusi query INSERT |
| `re` | Regex untuk membersihkan prefix "By " dari nama author |
| `datetime` | Validasi dan normalisasi format timestamp |

**Tiga task dalam pipeline:**

| Task | Fungsi |
|---|---|
| `fetch_articles()` | Hit `GET http://localhost:8000/articles`, ambil list artikel dari API (retry 2x jika gagal) |
| `transform_articles()` | Bersihkan data: hapus "By " dari author, validasi format timestamp ISO |
| `load_to_db()` | Insert artikel ke PostgreSQL; buat tabel otomatis jika belum ada; skip duplikat via `ON CONFLICT (url) DO NOTHING` |

**Schema tabel PostgreSQL `wired_articles`:**
```sql
CREATE TABLE wired_articles (
    id          SERIAL PRIMARY KEY,
    title       TEXT,
    url         TEXT UNIQUE,
    description TEXT,
    author      TEXT,
    scraped_at  TIMESTAMP,
    source      TEXT,
    inserted_at TIMESTAMP DEFAULT NOW()
);
```

### `docker-compose.yaml` — Infrastruktur Database

Menjalankan PostgreSQL versi 15 sebagai container Docker dengan konfigurasi:

| Parameter | Nilai |
|---|---|
| Database | `wired_db` |
| User | `wired_user` |
| Password | `wired_pass` |
| Port | `5439` (host) → `5432` (container) |

Data disimpan di volume persisten `postgres_data` sehingga tidak hilang saat container di-restart.

---

## 🔄 Alur Kerja

Program dijalankan secara berurutan lewat 4 file berikut:

| Urutan | File | Yang Dilakukan |
|:---:|---|---|
| 1 | `docker-compose.yaml` | Menyalakan database PostgreSQL sebagai tempat penyimpanan akhir |
| 2 | `scrapper.py` | Membuka browser secara otomatis, scraping artikel dari Wired.com, menyimpan hasilnya ke `wired_articles.json` dan `wired_articles.csv` |
| 3 | `api.py` | Membaca file JSON hasil scraping dan menyajikannya sebagai REST API di `localhost:8000` |
| 4 | `flow.py` | Mengambil data dari API, membersihkan data, lalu memasukkannya ke database PostgreSQL |

---

**Ringkasan alur:**

1. **PostgreSQL** dinyalakan lewat Docker sebagai tempat penyimpanan akhir data
2. **`scrapper.py`** membuka browser secara otomatis, mengunjungi Wired.com, dan mengumpulkan data artikel → disimpan ke file JSON dan CSV
3. **`api.py`** membaca file JSON tersebut dan menyajikannya sebagai REST API lokal
4. **`flow.py`** (Prefect) mengorkestrasi pipeline: fetch data dari API → transformasi/cleaning → load ke database

---

## 🚀 Cara Menjalankan Program

### Prasyarat

Pastikan sudah terinstal:
- Python 3.13+
- Docker & Docker Compose
- Google Chrome (untuk Selenium)
- `uv` (package manager) atau `pip`

### Langkah 1 — Clone dan Setup Environment

```bash
# Masuk ke direktori project
cd responsi-uts-infra

# Buat virtual environment dan install dependensi
uv sync

# Atau jika pakai pip:
pip install selenium webdriver-manager fastapi uvicorn prefect psycopg2-binary requests
```

### Langkah 2 — Jalankan Database PostgreSQL

```bash
docker compose up -d
```

Verifikasi database berjalan:
```bash
docker ps
# Harus ada container bernama: wired_postgres
```

### Langkah 3 — Jalankan Scraper

```bash
# Aktifkan virtual environment terlebih dahulu
source .venv/bin/activate   # Linux/Mac
# atau: .venv\Scripts\activate  # Windows

# Jalankan scraper utama (lebih lengkap, multi-kategori)
python scrapper.py
```

Proses ini membutuhkan waktu **5–15 menit** tergantung koneksi internet. Setelah selesai, akan muncul file:
- `wired_articles.json`
- `wired_articles.csv`

### Langkah 4 — Jalankan API Server

Buka **terminal baru** (jangan tutup yang sebelumnya):

```bash
source .venv/bin/activate

uvicorn api:app --reload --port 8000
```

Verifikasi API berjalan dengan membuka browser ke:
- `http://localhost:8000/` → harus muncul status `ok`
- `http://localhost:8000/docs` → Swagger UI interaktif
- `http://localhost:8000/articles` → data artikel JSON

### Langkah 5 — Jalankan ETL Pipeline

Buka **terminal baru** lagi:

```bash
source .venv/bin/activate

python flow.py
```

Pipeline akan berjalan dan menampilkan log:
```
✅ Fetched 75 articles from API
✅ Transformed 75 articles
✅ Inserted: 75 | Skipped (duplikat): 0
```

### Langkah 6 — Verifikasi Data di Database (Opsional)

```bash
# Masuk ke container PostgreSQL
docker exec -it wired_postgres psql -U wired_user -d wired_db

# Cek jumlah data
SELECT COUNT(*) FROM wired_articles;

# Lihat beberapa data
SELECT title, author, source, inserted_at FROM wired_articles LIMIT 5;

# Keluar dari psql
\q
```

### Menghentikan Semua Layanan

```bash
# Matikan API: Ctrl+C di terminal API

# Matikan Docker
docker compose down
```

---

## 💡 Manfaat dan Insight

### Output yang Dihasilkan

| Output | Format | Lokasi | Isi |
|---|---|---|---|
| File JSON | `.json` | `wired_articles.json` | Data artikel terstruktur dengan session metadata |
| File CSV | `.csv` | `wired_articles.csv` | Data tabular siap analisis di Excel/Pandas |
| Tabel Database | PostgreSQL | `wired_articles` | Data bersih, deduplikasi, siap query |
| REST API | HTTP JSON | `localhost:8000` | Endpoint data untuk integrasi sistem lain |

### Insight dari Data yang Bisa Digali

**1. Analisis Konten Artikel**
- Topik apa yang paling banyak ditulis di Wired.com per kategori?
- Berapa panjang rata-rata deskripsi artikel per kategori?

**2. Analisis Penulis (Author)**
- Siapa penulis paling produktif di Wired.com?
- Penulis mana yang paling sering menulis di kategori tertentu?

**3. Analisis Waktu**
- Pada jam berapa artikel biasanya dipublikasikan?
- Pola publikasi artikel per hari/minggu?

**4. Distribusi Kategori**
- Berapa banyak artikel per kategori (Security, Science, Business, Culture, Gear)?

### Contoh Query Analisis di PostgreSQL

```sql
-- Top 10 author paling produktif
SELECT author, COUNT(*) AS jumlah_artikel
FROM wired_articles
WHERE author != ''
GROUP BY author
ORDER BY jumlah_artikel DESC
LIMIT 10;

-- Jumlah artikel per hari
SELECT DATE(scraped_at) AS tanggal, COUNT(*) AS jumlah
FROM wired_articles
GROUP BY tanggal
ORDER BY tanggal DESC;

-- Artikel tanpa description (data quality check)
SELECT COUNT(*) AS artikel_tanpa_deskripsi
FROM wired_articles
WHERE description = '' OR description IS NULL;

---

## 📁 Struktur File

```
responsi-uts-infra/
├── scrapper.py          # Scraper utama (multi-kategori, multi-fallback)
├── main.py              # Scraper dasar (single kategori, versi awal)
├── api.py               # FastAPI server — sajikan data hasil scraping
├── flow.py              # Prefect ETL pipeline (Fetch → Transform → Load)
├── docker-compose.yaml  # Konfigurasi PostgreSQL via Docker
├── pyproject.toml       # Konfigurasi project dan dependensi Python
├── wired_articles.json  # Output scraping (format JSON)
└── wired_articles.csv   # Output scraping (format CSV)
```

