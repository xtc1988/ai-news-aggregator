"""Gemini APIを使用した記事要約"""
import os
import re
import time
from typing import Optional

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

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
    pattern = r'(\d+)\.\s*summary:\s*(.+?)\s*tags:\s*(.+?)(?=\d+\.|$)'
    matches = re.findall(pattern, response_text, re.DOTALL | re.IGNORECASE)
    for match in matches:
        idx, summary, tags = match
        summary = summary.strip()
        tags = [t.strip() for t in tags.split(",") if t.strip()]
        results.append({"summary": summary if summary else None, "tags": tags[:5]})
    while len(results) < expected_count:
        results.append({"summary": None, "tags": []})
    return results[:expected_count]

def summarize_batch(articles: list[dict], model_name: str = "gemini-1.5-flash") -> list[dict]:
    if not GEMINI_AVAILABLE or not configure_gemini():
        return [{"summary": None, "tags": []} for _ in articles]
    prompt = """以下の記事を日本語で要約してください。
各記事について:
- summary: 1-2文で内容を要約（日本語）
- tags: 関連するタグを2-3個（カンマ区切り）

記事リスト:
"""
    for i, article in enumerate(articles, 1):
        prompt += f"\n{i}. タイトル: {article['title']}\n   URL: {article['url']}\n   ソース: {article['source']}\n"
    prompt += "\n回答形式:\n1. summary: [要約]\n   tags: [タグ1], [タグ2], [タグ3]\n2. ..."
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return parse_gemini_response(response.text, len(articles))
    except Exception as e:
        print(f"Gemini API error: {e}")
        return [{"summary": None, "tags": []} for _ in articles]

def summarize_articles(articles: list[dict], batch_size: int = 10, max_articles: int = 50) -> list[dict]:
    to_summarize = [a for a in articles if not a.get("summary")][:max_articles]
    if not to_summarize:
        return articles
    print(f"Summarizing {len(to_summarize)} articles...")
    for i in range(0, len(to_summarize), batch_size):
        batch = to_summarize[i:i + batch_size]
        results = summarize_batch(batch)
        for article, result in zip(batch, results):
            article["summary"] = result["summary"]
            article["tags"] = result["tags"]
        if i + batch_size < len(to_summarize):
            time.sleep(2)
    return articles
