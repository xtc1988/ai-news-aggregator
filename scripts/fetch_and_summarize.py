#!/usr/bin/env python3
"""記事取得・要約・スコアリングのメインスクリプト"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from fetchers import fetch_hackernews_stories, fetch_reddit_posts, fetch_github_trending
from summarizer import summarize_articles
from scorer import score_articles

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_PATH = PROJECT_ROOT / "config.json"
ARTICLES_PATH = PROJECT_ROOT / "docs" / "data" / "articles.json"

def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_existing_articles() -> dict:
    if ARTICLES_PATH.exists():
        with open(ARTICLES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_updated": None, "articles": []}

def save_articles(data: dict):
    ARTICLES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ARTICLES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_all_articles(config: dict) -> list[dict]:
    articles = []
    sources = config.get("sources", {})
    if sources.get("hackernews", {}).get("enabled", False):
        print("Fetching Hacker News...")
        limit = sources["hackernews"].get("top_stories_count", 100)
        articles.extend(fetch_hackernews_stories(limit=limit))
    if sources.get("reddit", {}).get("enabled", False):
        print("Fetching Reddit...")
        subreddits = sources["reddit"].get("subreddits", [])
        posts_per = sources["reddit"].get("posts_per_subreddit", 25)
        articles.extend(fetch_reddit_posts(subreddits, posts_per))
    if sources.get("github_trending", {}).get("enabled", False):
        print("Fetching GitHub Trending...")
        articles.extend(fetch_github_trending())
    return articles

def deduplicate_articles(new_articles: list[dict], existing_articles: list[dict]) -> list[dict]:
    existing_ids = {a["id"] for a in existing_articles}
    return [a for a in new_articles if a["id"] not in existing_ids]

def cleanup_old_articles(articles: list[dict], retention_days: int) -> list[dict]:
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    cutoff_str = cutoff.isoformat() + "Z"
    return [a for a in articles if a.get("fetched_at", "") >= cutoff_str]

def main():
    print("=" * 50)
    print(f"AI News Aggregator - {datetime.utcnow().isoformat()}Z")
    print("=" * 50)
    config = load_config()
    existing_data = load_existing_articles()
    existing_articles = existing_data.get("articles", [])
    new_articles = fetch_all_articles(config)
    print(f"Fetched {len(new_articles)} articles total")
    unique_new = deduplicate_articles(new_articles, existing_articles)
    print(f"Found {len(unique_new)} new articles")
    all_articles = existing_articles + unique_new
    retention_days = config.get("retention_days", 7)
    all_articles = cleanup_old_articles(all_articles, retention_days)
    gemini_config = config.get("gemini", {})
    max_summarize = gemini_config.get("max_articles_per_run", 50)
    all_articles = summarize_articles(all_articles, max_articles=max_summarize)
    all_articles = score_articles(all_articles, config)
    output_data = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "articles": all_articles
    }
    save_articles(output_data)
    print(f"Saved {len(all_articles)} articles to {ARTICLES_PATH}")
    print("Done!")

if __name__ == "__main__":
    main()
