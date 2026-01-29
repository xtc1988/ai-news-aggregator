"""Reddit JSON API からの投稿取得"""
import requests
import hashlib
import time
from datetime import datetime
from typing import Optional

REDDIT_BASE = "https://www.reddit.com"
USER_AGENT = "AI-News-Aggregator/1.0"

def generate_id(url: str) -> str:
    """URLからユニークIDを生成"""
    return hashlib.md5(url.encode()).hexdigest()[:12]

def parse_post(raw: dict, subreddit: str) -> Optional[dict]:
    """APIレスポンスを記事形式に変換"""
    data = raw.get("data", {})

    # セルフポストの場合はRedditのURLを使用
    url = data.get("url", "")
    if data.get("is_self", False):
        url = f"https://reddit.com{data.get('permalink', '')}"

    if not url:
        return None

    return {
        "id": generate_id(url),
        "title": data.get("title", ""),
        "url": url,
        "source": f"Reddit/{subreddit}",
        "source_score": data.get("score", 0),
        "comments_count": data.get("num_comments", 0),
        "comments_url": f"https://reddit.com{data.get('permalink', '')}",
        "summary": None,
        "tags": [],
        "interest_score": 0,
        "matched_keywords": [],
        "created_at": datetime.utcfromtimestamp(data.get("created_utc", 0)).isoformat() + "Z",
        "fetched_at": datetime.utcnow().isoformat() + "Z"
    }

def fetch_reddit_posts(subreddits: list[str], posts_per_sub: int = 25) -> list[dict]:
    """複数サブレディットから投稿を取得"""
    headers = {"User-Agent": USER_AGENT}
    articles = []

    for subreddit in subreddits:
        try:
            url = f"{REDDIT_BASE}/r/{subreddit}/hot.json?limit={posts_per_sub}"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            posts = data.get("data", {}).get("children", [])

            for post in posts:
                article = parse_post(post, subreddit)
                if article:
                    articles.append(article)

            # Rate limit: 1 request per second
            time.sleep(1)

        except Exception as e:
            print(f"Error fetching r/{subreddit}: {e}")
            continue

    return articles
