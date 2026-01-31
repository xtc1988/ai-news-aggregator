"""Gemini APIを使用した記事要約（日本語翻訳対応）"""
import os
import re
import time
import random
from typing import Optional

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# レート制限対策
MAX_RETRIES = 3
BASE_DELAY = 30  # 秒

def configure_gemini():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Warning: GEMINI_API_KEY not set")
        return False
    if GEMINI_AVAILABLE:
        genai.configure(api_key=api_key)
        return True
    return False

def parse_gemini_response(response_text: str, expected_count: int) -> list[dict]:
    results = []
    # title_ja, summary, tagsを抽出するパターン
    pattern = r'(\d+)\.\s*title_ja:\s*(.+?)\s*summary:\s*(.+?)\s*tags:\s*(.+?)(?=\d+\.|$)'
    matches = re.findall(pattern, response_text, re.DOTALL | re.IGNORECASE)
    for match in matches:
        idx, title_ja, summary, tags = match
        title_ja = title_ja.strip()
        summary = summary.strip()
        tags = [t.strip() for t in tags.split(",") if t.strip()]
        results.append({
            "title_ja": title_ja if title_ja else None,
            "summary": summary if summary else None,
            "tags": tags[:5]
        })
    while len(results) < expected_count:
        results.append({"title_ja": None, "summary": None, "tags": []})
    return results[:expected_count]

def summarize_batch(articles: list[dict], model_name: str = "gemini-2.0-flash") -> list[dict]:
    if not GEMINI_AVAILABLE or not configure_gemini():
        return [{"title_ja": None, "summary": None, "tags": []} for _ in articles]
    prompt = """以下の記事を日本語で処理してください。
各記事について:
- title_ja: タイトルを自然な日本語に翻訳（技術用語は適切に残す）
- summary: 1-2文で内容を要約（日本語）
- tags: 関連する日本語タグを2-3個（カンマ区切り、例: 機械学習, 自然言語処理, オープンソース）

記事リスト:
"""
    for i, article in enumerate(articles, 1):
        prompt += f"\n{i}. タイトル: {article['title']}\n   URL: {article['url']}\n   ソース: {article['source']}\n"
    prompt += "\n回答形式:\n1. title_ja: [日本語タイトル]\n   summary: [要約]\n   tags: [タグ1], [タグ2], [タグ3]\n2. ..."
    for attempt in range(MAX_RETRIES):
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return parse_gemini_response(response.text, len(articles))
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                # レート制限エラー - 待機してリトライ
                delay = BASE_DELAY * (2 ** attempt) + random.uniform(0, 10)
                print(f"Rate limit hit, waiting {delay:.1f}s before retry {attempt + 1}/{MAX_RETRIES}...")
                time.sleep(delay)
                continue
            print(f"Gemini API error: {e}")
            break
    return [{"title_ja": None, "summary": None, "tags": []} for _ in articles]

def summarize_articles(articles: list[dict], batch_size: int = 5, max_articles: int = 30) -> list[dict]:
    """記事を日本語で要約・翻訳（レート制限対策済み）"""
    # summary または title_ja がない記事を対象
    to_summarize = [a for a in articles if not a.get("summary") or not a.get("title_ja")][:max_articles]
    if not to_summarize:
        return articles
    print(f"Summarizing {len(to_summarize)} articles (batch_size={batch_size})...")
    for i in range(0, len(to_summarize), batch_size):
        batch = to_summarize[i:i + batch_size]
        print(f"  Processing batch {i // batch_size + 1}/{(len(to_summarize) + batch_size - 1) // batch_size}...")
        results = summarize_batch(batch)
        for article, result in zip(batch, results):
            article["title_ja"] = result.get("title_ja") or article.get("title_ja")
            article["summary"] = result.get("summary") or article.get("summary")
            article["tags"] = result.get("tags") or article.get("tags", [])
        if i + batch_size < len(to_summarize):
            # バッチ間で十分な待機時間を設ける（レート制限対策）
            wait_time = 15 + random.uniform(0, 5)
            print(f"  Waiting {wait_time:.1f}s before next batch...")
            time.sleep(wait_time)
    return articles
