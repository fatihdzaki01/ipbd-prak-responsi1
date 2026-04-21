"""
flow.py — Prefect pipeline: Fetch → Transform → Load to PostgreSQL
Jalankan: python flow.py
"""

import re
from datetime import datetime

import psycopg2
import requests
from prefect import flow, task

# =========================
# CONFIG
# =========================
API_URL = "http://localhost:8000/articles"

DB_CONFIG = {
    "host": "localhost",
    "port": 5439,
    "dbname": "wired_db",
    "user": "wired_user",
    "password": "wired_pass",
}


# =========================
# TASK 1: FETCH
# =========================
@task(name="Fetch Articles from API", retries=2, retry_delay_seconds=5)
def fetch_articles() -> list[dict]:
    """Hit GET /articles ke FastAPI lokal."""
    response = requests.get(API_URL, timeout=15)
    response.raise_for_status()
    data = response.json()
    articles = data.get("articles", [])
    print(f"✅ Fetched {len(articles)} articles from API")
    return articles


# =========================
# TASK 2: TRANSFORM
# =========================
@task(name="Transform Articles")
def transform_articles(articles: list[dict]) -> list[dict]:
    """
    Bersihkan data:
    - Hapus kata 'By' dari author
    - Validasi / normalisasi scraped_at ke ISO format
    """
    cleaned = []
    for article in articles:
        # Bersihkan author: hapus 'By ', 'by ' di awal string
        author = article.get("author", "") or ""
        author = re.sub(r"^[Bb]y\s+", "", author).strip()

        # Normalisasi scraped_at
        raw_dt = article.get("scraped_at", "")
        try:
            # Sudah ISO format dari scraper, tapi kita parse ulang untuk validasi
            parsed_dt = datetime.fromisoformat(raw_dt)
            scraped_at = parsed_dt.isoformat()
        except (ValueError, TypeError):
            scraped_at = datetime.now().isoformat()

        cleaned.append(
            {
                "title": article.get("title", "").strip(),
                "url": article.get("url", "").strip(),
                "description": article.get("description", "").strip(),
                "author": author,
                "scraped_at": scraped_at,
                "source": article.get("source", "Wired.com").strip(),
            }
        )

    print(f"✅ Transformed {len(cleaned)} articles")
    return cleaned


# =========================
# TASK 3: LOAD TO DB
# =========================
@task(name="Load to PostgreSQL")
def load_to_db(articles: list[dict]) -> None:
    """
    Insert artikel ke tabel wired_articles.
    Buat tabel dulu kalau belum ada.
    ON CONFLICT (url) DO NOTHING → skip duplikat.
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Buat tabel jika belum ada
    cur.execute("""
        CREATE TABLE IF NOT EXISTS wired_articles (
            id          SERIAL PRIMARY KEY,
            title       TEXT,
            url         TEXT UNIQUE,
            description TEXT,
            author      TEXT,
            scraped_at  TIMESTAMP,
            source      TEXT,
            inserted_at TIMESTAMP DEFAULT NOW()
        );
    """)

    # Insert dengan skip duplikat
    insert_query = """
        INSERT INTO wired_articles (title, url, description, author, scraped_at, source)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (url) DO NOTHING;
    """

    inserted = 0
    skipped = 0
    for article in articles:
        cur.execute(
            insert_query,
            (
                article["title"],
                article["url"],
                article["description"],
                article["author"],
                article["scraped_at"],
                article["source"],
            ),
        )
        if cur.rowcount > 0:
            inserted += 1
        else:
            skipped += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"✅ Inserted: {inserted} | Skipped (duplikat): {skipped}")


# =========================
# FLOW UTAMA
# =========================
@flow(name="Wired Articles Pipeline")
def wired_pipeline():
    """
    Pipeline utama:
    fetch_articles → transform_articles → load_to_db
    Data dipass langsung lewat return value antar task.
    """
    raw = fetch_articles()
    cleaned = transform_articles(raw)
    load_to_db(cleaned)


# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    wired_pipeline()
