"""Hacker News Firebase API からの記事取得"""
import requests
import hashlib
from datetime import datetime
from typing import Optional

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"

def generate_id(url: str) -> str:
    """URLからユニークIDを生成"""
    return hashlib.md5(url.encode()).hexdigest()[:12]

def parse_story(raw: dict) -> Optional[dict]:
    """APIレスポンスを記事形式に変換"""
    if "url" not in raw or not raw.get("url"):
        return None

    return {
        "id": generate_id(raw["url"]),
        "title": raw.get("title", ""),
        "url": raw["url"],
        "source": "Hacker News",
        "source_score": raw.get("score", 0),
        "comments_count": raw.get("descendants", 0),
        "comments_url": f"https://news.ycombinator.com/item?id={raw['id']}",
        "summary": None,
        "tags": [],
        "interest_score": 0,
        "matched_keywords": [],
        "created_at": datetime.utcfromtimestamp(raw.get("time", 0)).isoformat() + "Z",
        "fetched_at": datetime.utcnow().isoformat() + "Z"
    }

def fetch_hackernews_stories(limit: int = 100) -> list[dict]:
    """Hacker Newsのトップストーリーを取得"""
    # トップストーリーのID一覧を取得
    response = requests.get(f"{HN_API_BASE}/topstories.json", timeout=10)
    response.raise_for_status()
    story_ids = response.json()[:limit]

    articles = []
    for story_id in story_ids:
        try:
            resp = requests.get(f"{HN_API_BASE}/item/{story_id}.json", timeout=5)
            resp.raise_for_status()
            story = resp.json()
            if story:
                article = parse_story(story)
                if article:
                    articles.append(article)
        except Exception as e:
            print(f"Error fetching story {story_id}: {e}")
            continue

    return articles
