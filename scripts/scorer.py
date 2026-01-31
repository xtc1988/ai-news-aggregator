"""興味キーワードに基づくスコアリング"""
import re
from typing import Tuple

def calculate_interest_score(article: dict, interests: dict, weights: dict) -> Tuple[int, list[str]]:
    """記事の興味スコアを計算（日本語・英語両方のキーワードに対応）"""
    # None値を安全に処理
    title = article.get("title") or ""
    title_ja = article.get("title_ja") or ""
    summary = article.get("summary") or ""
    tags = article.get("tags") or []

    text = " ".join([
        title,
        title_ja,
        summary,
        " ".join(tags)
    ]).lower()
    score = 0
    matched = []
    for priority, keywords in interests.items():
        weight = weights.get(priority, 1)
        for keyword in keywords:
            pattern = re.compile(re.escape(keyword.lower()))
            if pattern.search(text):
                score += weight
                matched.append(keyword)
    return score, list(set(matched))

def score_articles(articles: list[dict], config: dict) -> list[dict]:
    interests = config.get("interests", {})
    weights = config.get("score_weights", {"high": 10, "medium": 5, "low": 2})
    for article in articles:
        score, keywords = calculate_interest_score(article, interests, weights)
        article["interest_score"] = score
        article["matched_keywords"] = keywords
    articles.sort(key=lambda x: x["interest_score"], reverse=True)
    return articles
