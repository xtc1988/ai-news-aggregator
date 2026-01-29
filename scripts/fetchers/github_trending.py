"""GitHub Trending ページのスクレイピング"""
import requests
import hashlib
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup

GITHUB_TRENDING_URL = "https://github.com/trending"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def generate_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]

def parse_repo_row(row) -> Optional[dict]:
    try:
        h2 = row.select_one("h2 a")
        if not h2:
            return None
        repo_path = h2.get("href", "").strip()
        if not repo_path:
            return None
        url = f"https://github.com{repo_path}"
        repo_name = repo_path.strip("/")
        desc_elem = row.select_one("p")
        description = desc_elem.get_text(strip=True) if desc_elem else ""
        star_elem = row.select_one("a[href$='/stargazers']")
        stars = 0
        if star_elem:
            star_text = star_elem.get_text(strip=True).replace(",", "")
            try:
                stars = int(star_text)
            except ValueError:
                pass
        today_stars_elem = row.select_one("span.d-inline-block.float-sm-right")
        today_stars = 0
        if today_stars_elem:
            today_text = today_stars_elem.get_text(strip=True)
            try:
                today_stars = int(today_text.split()[0].replace(",", ""))
            except (ValueError, IndexError):
                pass
        return {
            "id": generate_id(url),
            "title": f"[GitHub] {repo_name}",
            "url": url,
            "source": "GitHub Trending",
            "source_score": stars,
            "comments_count": today_stars,
            "comments_url": f"{url}/issues",
            "summary": description if description else None,
            "tags": [],
            "interest_score": 0,
            "matched_keywords": [],
            "created_at": datetime.utcnow().isoformat() + "Z",
            "fetched_at": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        print(f"Error parsing repo row: {e}")
        return None

def fetch_github_trending() -> list[dict]:
    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(GITHUB_TRENDING_URL, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.select("article.Box-row")
        articles = []
        for row in rows:
            article = parse_repo_row(row)
            if article:
                articles.append(article)
        return articles
    except Exception as e:
        print(f"Error fetching GitHub Trending: {e}")
        return []
