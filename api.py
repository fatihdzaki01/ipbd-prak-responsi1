# Jalankan dengan: uvicorn api:app --reload --port 8000

import json
import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# APP INIT
app = FastAPI(
    title="Wired Articles API",
    description="API untuk menyajikan data artikel hasil scraping dari Wired.com",
    version="1.0.0",
)

# Path ke file JSON hasil scraping
JSON_PATH = os.path.join(os.path.dirname(__file__), "wired_articles.json")


# SCHEMA
class Article(BaseModel):
    title: str
    url: str
    description: Optional[str] = ""
    author: Optional[str] = ""
    scraped_at: Optional[str] = ""
    source: Optional[str] = ""


class ArticlesResponse(BaseModel):
    session_id: str
    timestamp: str
    articles_count: int
    articles: List[Article]


# HELPER: LOAD JSON
def load_articles() -> dict:
    # Baca file JSON hasil scraping
    if not os.path.exists(JSON_PATH):
        raise HTTPException(
            status_code=500,
            detail=f"File data tidak ditemukan: {JSON_PATH}. Jalankan scraper.py terlebih dahulu.",
        )
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


# ENDPOINTS
@app.get("/", summary="Health Check")
def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "Wired Articles API is running",
        "timestamp": datetime.now().isoformat(),
    }


@app.get(
    "/articles",
    response_model=ArticlesResponse,
    summary="Get All Articles",
    description="Mengembalikan seluruh data artikel hasil scraping dari Wired.com dalam format JSON.",
)
def get_articles():
    ##— mengembalikan semua artikel dari file JSON hasil scraping.
    data = load_articles()

    return JSONResponse(
        content={
            "session_id": data.get("session_id", ""),
            "timestamp": data.get("timestamp", ""),
            "articles_count": data.get("articles_count", 0),
            "articles": data.get("articles", []),
        }
    )


@app.get(
    "/articles/count",
    summary="Get Article Count",
)
def get_articles_count():
    ##Mengembalikan jumlah artikel
    data = load_articles()
    return {
        "articles_count": data.get("articles_count", 0),
        "session_id": data.get("session_id", ""),
        "scraped_at": data.get("timestamp", ""),
    }
