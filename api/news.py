"""
api/news.py — STRIX News Module
Save as: E:\Strix\api\news.py

Gets top headlines using NewsAPI.
Free key at: https://newsapi.org
Add to .env:  NEWS_API_KEY=your_key_here

Falls back to BBC RSS feed if no API key.
"""

import os, time, requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))

API_KEY  = os.getenv("NEWS_API_KEY", "").strip()
BASE_URL = "https://newsapi.org/v2/top-headlines"

_cache = {}
CACHE_SECONDS = 300   # 5 minutes

CATEGORY_MAP = {
    "tech":          "technology",
    "technology":    "technology",
    "sport":         "sports",
    "sports":        "sports",
    "business":      "business",
    "finance":       "business",
    "health":        "health",
    "science":       "science",
    "entertainment": "entertainment",
    "general":       "general",
    "india":         "general",
    "world":         "general",
}


def _fetch_newsapi(category: str, count: int) -> list[dict]:
    """Fetch from NewsAPI."""
    cache_key = f"{category}_{count}"
    now = time.time()
    if cache_key in _cache and now - _cache[cache_key]["ts"] < CACHE_SECONDS:
        return _cache[cache_key]["data"]

    params = {
        "apiKey":   API_KEY,
        "country":  "in",          # India news by default
        "category": category,
        "pageSize": count,
    }
    try:
        r = requests.get(BASE_URL, params=params, timeout=8)
        r.raise_for_status()
        articles = r.json().get("articles", [])
        _cache[cache_key] = {"ts": now, "data": articles}
        return articles
    except Exception as e:
        print(f"[News] NewsAPI error: {e}")
        return []


def _fetch_rss_fallback(count: int) -> list[dict]:
    """Fallback: BBC World RSS — no API key needed."""
    try:
        import xml.etree.ElementTree as ET
        r = requests.get(
            "http://feeds.bbci.co.uk/news/rss.xml",
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        root = ET.fromstring(r.content)
        items = root.findall(".//item")[:count]
        articles = []
        for item in items:
            title = item.findtext("title", "").strip()
            desc  = item.findtext("description", "").strip()
            if title:
                articles.append({"title": title, "description": desc})
        return articles
    except Exception as e:
        print(f"[News] RSS fallback error: {e}")
        return []


def format_news(category: str = "general", count: int = 5) -> str:
    """
    Called by brain_router for get_news action.
    Returns formatted string STRIX reads aloud.
    """
    cat = CATEGORY_MAP.get(category.lower(), "general")

    # Try NewsAPI if key available
    if API_KEY:
        articles = _fetch_newsapi(cat, count)
    else:
        articles = []

    # Fallback to RSS if NewsAPI failed or no key
    if not articles:
        print("[News] Using RSS fallback")
        articles = _fetch_rss_fallback(count)

    if not articles:
        return "Sorry Boss, couldn't fetch news right now. Check your internet connection."

    lines = [f"Here are the top {len(articles)} {category} headlines, Boss:"]
    for i, art in enumerate(articles, 1):
        title = art.get("title", "").strip()
        # Remove source suffix like " - BBC News"
        if " - " in title:
            title = title.rsplit(" - ", 1)[0].strip()
        if title:
            lines.append(f"{i}. {title}")

    return "\n".join(lines)


if __name__ == "__main__":
    print(format_news("technology", 5))